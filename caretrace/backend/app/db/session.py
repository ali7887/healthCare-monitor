"""Database engine and session scaffold.

The engine is created lazily by SQLAlchemy and does not open a connection at
import time, so this module is import-safe even without a running database.
`get_db` is the FastAPI session dependency used by the API routes.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# SQLite (the local/demo default) needs check_same_thread disabled because
# FastAPI serves sync handlers from a thread pool. Postgres uses pool_pre_ping
# to transparently recover stale pooled connections.
if settings.is_sqlite:
    _engine_kwargs: dict = {"connect_args": {"check_same_thread": False}}
else:
    _engine_kwargs = {"pool_pre_ping": True}

engine = create_engine(settings.database_url, future=True, **_engine_kwargs)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and ensure it is closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
