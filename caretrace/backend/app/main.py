"""FastAPI application entrypoint.

Run locally with:
    uv run uvicorn app.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import REQUEST_ID_HEADER, RequestContextMiddleware

settings = get_settings()

# Structured JSON logging + request correlation, installed before the app is
# built so startup logs are captured too. The level follows CARETRACE_LOG_LEVEL
# (default INFO), so a production deployment can dial verbosity from the
# environment without a code change.
configure_logging(level=settings.log_level)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """On startup, ensure tables exist when running on the SQLite demo default.

    This lets the app run from a clean checkout with no separate migration step.
    For Postgres, schema is managed by Alembic (`alembic upgrade head`), so we do
    not auto-create there. `create_all` is idempotent and only adds missing
    tables, so seeding or a prior run does no harm.

    When `CARETRACE_DEMO_SEED=1` (public demo instances), the deterministic demo
    dataset is loaded *only if the database is empty* — so a demo boots with data
    but an existing database (or a real production one) is never overwritten.
    """
    if settings.is_sqlite:
        import app.models  # noqa: F401  (register every table on Base.metadata)
        from app.db.base import Base
        from app.db.session import engine

        Base.metadata.create_all(engine)

    if settings.demo_seed_enabled:
        _seed_demo_if_empty()
    yield


def _seed_demo_if_empty() -> None:
    """Seed the demo dataset when the database has no runs yet (idempotent).

    Guarded so repeated boots (or a boot against a populated database) never
    reset or duplicate data. Failures are logged but do not block startup.
    """
    from app.core.logging import get_logger, log_event
    from app.db.session import SessionLocal
    from app.models import Run

    logger = get_logger("startup")
    db = SessionLocal()
    try:
        existing = db.query(Run).count()
    except Exception:
        existing = 0
    finally:
        db.close()

    if existing:
        log_event(logger, "demo_seed_skipped", reason="database_not_empty", runs=existing)
        return

    from app.seed_demo import seed

    # Harden for serverless cold starts: two instances could race to seed an
    # empty database. Seeding stays best-effort so a race (or any seed error)
    # is logged but never crashes application startup or corrupts a boot.
    try:
        counts = seed(reset=False)
        log_event(logger, "demo_seed_on_boot", total=sum(counts.values()))
    except Exception as exc:  # noqa: BLE001 - startup must not fail on seed
        log_event(logger, "demo_seed_failed", level=logging.ERROR, error=str(exc))


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    # Optional regex for additional origins (e.g. Vercel preview deployments).
    # None by default → identical behaviour to an explicit origin list only.
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Expose the correlation id so the browser can read it and tie a frontend
    # observation back to the backend logs that produced it.
    expose_headers=[REQUEST_ID_HEADER],
)

# Correlation id + request timing. Added last, so it is the outermost layer and
# stamps `X-Request-ID` on every response — including CORS preflights and error
# responses — while timing the full request.
app.add_middleware(RequestContextMiddleware)

app.include_router(api_router, prefix=settings.api_prefix)
