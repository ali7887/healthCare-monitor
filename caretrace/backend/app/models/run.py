"""Run model: one transcript processing execution and its full trace."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Float, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Provider, RoutingDecision, RunStatus, enum_column
from app.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.review_item import ReviewItem
    from app.models.validation_log import ValidationLog


class Run(UUIDMixin, TimestampMixin, Base):
    """A single processing run, storing input, outputs, metrics, and decision."""

    __tablename__ = "runs"

    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[Provider] = mapped_column(enum_column(Provider), nullable=False)
    status: Mapped[RunStatus] = mapped_column(enum_column(RunStatus), nullable=False)

    warnings_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)

    raw_model_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    final_output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Routing + confidence trace (Phase 10)
    routing_decision: Mapped[RoutingDecision | None] = mapped_column(
        enum_column(RoutingDecision), nullable=True
    )
    routing_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_breakdown: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    # Human-readable, step-by-step account of how the routing decision was
    # reached (Phase 20). Newline-separated "Step N: ..." lines; rendered as an
    # ordered list in the trace viewer's reasoning panel.
    reasoning_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    validation_logs: Mapped[list["ValidationLog"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )
    review_items: Mapped[list["ReviewItem"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"Run(id={self.id!r}, provider={self.provider!r}, "
            f"status={self.status!r}, confidence={self.confidence!r})"
        )
