"""ReviewItem model: a run routed for human review and its outcome."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ReviewStatus, enum_column
from app.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.run import Run


class ReviewItem(UUIDMixin, TimestampMixin, Base):
    """Human review record for a flagged run."""

    __tablename__ = "review_items"

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    edited_output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[ReviewStatus] = mapped_column(
        enum_column(ReviewStatus), nullable=False, default=ReviewStatus.pending
    )

    run: Mapped["Run"] = relationship(back_populates="review_items")

    def __repr__(self) -> str:
        return (
            f"ReviewItem(id={self.id!r}, run_id={self.run_id!r}, "
            f"status={self.status!r})"
        )
