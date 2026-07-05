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


def _db_reachable(db: Session) -> bool:
    """Return True if a trivial round-trip to the database succeeds."""
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception:  # pragma: no cover - defensive; exercised via readiness
        return False


def _schema_present(db: Session) -> bool:
    """Return True if the core ``runs`` table exists and is queryable."""
    try:
        db.query(Run).count()
        return True
    except Exception:
        return False


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)):
    """Report service liveness and database connectivity.

    Returns the stable ``{status, service}`` contract on success; **503** if the
    database cannot be reached.
    """
    settings = get_settings()
    if not _db_reachable(db):
        log_event(_logger, "health_check_failed", level=logging.ERROR, check="database")
        return JSONResponse(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unavailable", "service": settings.service_name},
        )
    return HealthResponse(status="ok", service=settings.service_name)


@router.get("/ready", response_model=ReadinessResponse)
def ready(db: Session = Depends(get_db)):
    """Report readiness to serve traffic: database reachable + schema present.

    Returns per-probe results in ``checks`` so an operator can see exactly which
    probe failed. Any failing probe yields **503**.
    """
    settings = get_settings()
    checks = {
        "database": _db_reachable(db),
        "schema": _schema_present(db),
    }
    ready_now = all(checks.values())
    if not ready_now:
        failed = [name for name, ok in checks.items() if not ok]
        log_event(_logger, "readiness_check_failed", level=logging.ERROR, failed=failed)
        return JSONResponse(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "service": settings.service_name,
                "env": settings.env,
                "checks": checks,
            },
        )
    return ReadinessResponse(
        status="ready",
        service=settings.service_name,
        env=settings.env,
        checks=checks,
    )
