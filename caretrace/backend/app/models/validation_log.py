"""ValidationLog model: one validation issue associated with a run."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import IssueType, Severity, enum_column
from app.models.mixins import CreatedAtMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.run import Run


class ValidationLog(UUIDMixin, CreatedAtMixin, Base):
    """A single schema or clinical validation issue for a run."""

    __tablename__ = "validation_logs"

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    issue_type: Mapped[IssueType] = mapped_column(
        enum_column(IssueType), nullable=False
    )
    # severity and rule_id complete the unified validation taxonomy (Phase 10).
    severity: Mapped[Severity | None] = mapped_column(
        enum_column(Severity), nullable=True
    )
    field: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    rule_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    run: Mapped["Run"] = relationship(back_populates="validation_logs")

    def __repr__(self) -> str:
        return (
            f"ValidationLog(id={self.id!r}, run_id={self.run_id!r}, "
            f"issue_type={self.issue_type!r}, field={self.field!r})"
        )
