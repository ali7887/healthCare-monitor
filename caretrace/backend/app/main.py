"""FastAPI application entrypoint.

Run locally with:
    uv run uvicorn app.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import REQUEST_ID_HEADER, RequestContextMiddleware

settings = get_settings()

# Structured JSON logging + request correlation, installed before the app is
# built so startup logs are captured too.
configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """On startup, ensure tables exist when running on the SQLite demo default.

    This lets the app run from a clean checkout with no separate migration step.
    For Postgres, schema is managed by Alembic (`alembic upgrade head`), so we do
    not auto-create there. `create_all` is idempotent and only adds missing
    tables, so seeding or a prior run does no harm.
    """
    if settings.is_sqlite:
        import app.models  # noqa: F401  (register every table on Base.metadata)
        from app.db.base import Base
        from app.db.session import engine

        Base.metadata.create_all(engine)
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
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
