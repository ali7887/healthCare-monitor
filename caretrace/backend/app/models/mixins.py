"""Reusable declarative mixins for primary keys and timestamps.

Timestamps use Python-side defaults (application-generated, timezone-aware)
rather than server defaults, keeping migrations free of dialect-specific SQL.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UUIDMixin:
    """Adds a UUID primary key."""

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )


class CreatedAtMixin:
    """Adds an immutable creation timestamp."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )


class TimestampMixin(CreatedAtMixin):
    """Adds creation and last-updated timestamps."""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
