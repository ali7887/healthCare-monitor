"""Structured, request-scoped logging for the backend.

Emits one JSON object per log record — grep-friendly and machine-readable — and
carries a request-scoped correlation id through a ``contextvar`` so every log
written while handling a request is automatically tagged with its
``request_id`` without threading it through call signatures.

Intentionally dependency-free (stdlib ``logging`` only) and local-first: there
is no external log shipper, collector, or telemetry vendor. See
``docs/ENGINEERING_DECISIONS.md`` for why the observability layer is deliberately
thin. Callers must log **safe metadata only** — ids, statuses, counts — never
raw clinical text or full payloads.
"""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

# Request-scoped correlation id. Set by ``RequestContextMiddleware`` for the life
# of a request and reset afterwards; ``None`` outside a request (startup, seed).
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)

# LogRecord attribute names that already exist on a blank record. Anything a
# caller passes via ``extra=`` that is *not* in this set is treated as a
# structured field by the JSON formatter.
_RESERVED: set[str] = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}

# Root logger for the application. A dedicated tree (not the stdlib root) so the
# JSON handler never fights with uvicorn's own access/error logging.
_ROOT_NAME = "caretrace"


def set_request_id(request_id: str | None) -> None:
    """Bind (or clear) the correlation id for the current context."""
    _request_id.set(request_id)


def get_request_id() -> str | None:
    """Return the correlation id bound to the current context, if any."""
    return _request_id.get()


class JsonLogFormatter(logging.Formatter):
    """Render a ``LogRecord`` as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = _request_id.get()
        if request_id:
            payload["request_id"] = request_id

        # Fold structured extras (from ``log_event`` / ``logger.info(..., extra=)``)
        # into the top level so events are queryable, not buried in the message.
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, ensure_ascii=False)


_configured = False


def configure_logging(level: int = logging.INFO) -> None:
    """Install the JSON formatter on the application logger. Idempotent.

    Called once at app startup (and safe to call from scripts). Uses a private
    logger tree with ``propagate=False`` so records don't double-print through
    uvicorn's root handlers.
    """
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())

    logger = logging.getLogger(_ROOT_NAME)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    _configured = True


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a namespaced application logger (e.g. ``caretrace.http``)."""
    if not name:
        return logging.getLogger(_ROOT_NAME)
    if name == _ROOT_NAME or name.startswith(f"{_ROOT_NAME}."):
        return logging.getLogger(name)
    return logging.getLogger(f"{_ROOT_NAME}.{name}")


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    """Emit a structured event.

    ``event`` becomes both the log *message* (so plain-text grep works) and a
    first-class ``event`` field. Extra ``fields`` are attached as structured
    metadata; any that would collide with reserved ``LogRecord`` attributes are
    dropped defensively.
    """
    safe = {key: value for key, value in fields.items() if key not in _RESERVED}
    logger.log(level, event, extra={"event": event, **safe})
