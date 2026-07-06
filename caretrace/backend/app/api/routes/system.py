"""System liveness and readiness endpoints.

These back the platform health checks used by hosts like Render/Railway and by
uptime monitors:

* ``GET /health``  — liveness + database connectivity. Cheap, no table access.
* ``GET /ready``   — readiness: the database is reachable *and* the core schema
  is present, so the service can actually serve traffic.

Both return **503** (not 500) when a probe fails, which is the conventional
signal for "not ready — don't route traffic here yet."
"""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Depends
from fastapi import status as http_status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.core.logging import get_logger, log_event
from app.models import Run
from app.schemas.health import HealthResponse, ReadinessResponse

router = APIRouter(tags=["system"])

_logger = get_logger("system")


# user:password@ in a URL embedded in an error message — never log credentials.
_URL_CREDENTIALS_RE = re.compile(r"://[^/@\s]+@")


def _sanitize_error(exc: Exception) -> str:
    """One-line, credential-free rendering of a database error."""
    message = str(exc).splitlines()[0] if str(exc) else ""
    return _URL_CREDENTIALS_RE.sub("://***@", message)


def _db_target(db: Session) -> tuple[str, str | None]:
    """The configured backend name and host (no credentials, no full URL)."""
    url = db.get_bind().url
    return url.get_backend_name(), url.host


def _probe_database(db: Session) -> str | None:
    """Round-trip ``SELECT 1``; return None on success, else the error class."""
    try:
        db.execute(text("SELECT 1"))
        return None
    except Exception as exc:
        _log_probe_failure(db, "database", exc)
        return type(exc).__name__


def _probe_schema(db: Session) -> str | None:
    """Query the core ``runs`` table; return None on success, else the error class."""
    try:
        db.query(Run).count()
        return None
    except Exception as exc:
        _log_probe_failure(db, "schema", exc)
        return type(exc).__name__


def _log_probe_failure(db: Session, check: str, exc: Exception) -> None:
    """Log a failed probe with enough sanitized detail to diagnose remotely."""
    backend, host = _db_target(db)
    log_event(
        _logger,
        "health_probe_failed",
        level=logging.ERROR,
        check=check,
        db_backend=backend,
        db_host=host,
        error=type(exc).__name__,
        detail=_sanitize_error(exc),
    )


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)):
    """Report service liveness and database connectivity.

    Returns the stable ``{status, service}`` contract on success; **503** if the
    database cannot be reached.
    """
    settings = get_settings()
    database_error = _probe_database(db)
    if database_error is not None:
        backend, host = _db_target(db)
        return JSONResponse(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unavailable",
                "service": settings.service_name,
                "env": settings.env,
                "diagnostics": {
                    "db_backend": backend,
                    "db_host": host,
                    "error": database_error,
                },
            },
        )
    return HealthResponse(status="ok", service=settings.service_name)


@router.get("/ready", response_model=ReadinessResponse)
def ready(db: Session = Depends(get_db)):
    """Report readiness to serve traffic: database reachable + schema present.

    Returns per-probe results in ``checks`` so an operator can see exactly which
    probe failed. Any failing probe yields **503**.
    """
    settings = get_settings()
    errors = {
        "database": _probe_database(db),
        "schema": _probe_schema(db),
    }
    checks = {name: error is None for name, error in errors.items()}
    if not all(checks.values()):
        failed = [name for name, ok in checks.items() if not ok]
        log_event(_logger, "readiness_check_failed", level=logging.ERROR, failed=failed)
        backend, host = _db_target(db)
        return JSONResponse(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "service": settings.service_name,
                "env": settings.env,
                "checks": checks,
                # Credential-free pointers for remote diagnosis: which engine the
                # deployment actually resolved (`sqlite` here in production means
                # DATABASE_URL never reached the app) and what failed, by class.
                "diagnostics": {
                    "db_backend": backend,
                    "db_host": host,
                    "errors": {name: err for name, err in errors.items() if err},
                },
            },
        )
    return ReadinessResponse(
        status="ready",
        service=settings.service_name,
        env=settings.env,
        checks=checks,
    )
