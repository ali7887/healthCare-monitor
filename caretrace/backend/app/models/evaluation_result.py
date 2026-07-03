"""EvaluationResult model: aggregated reliability metrics per provider."""

from __future__ import annotations

from sqlalchemy import Float
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import Provider, enum_column
from app.models.mixins import CreatedAtMixin, UUIDMixin


class EvaluationResult(UUIDMixin, CreatedAtMixin, Base):
    """A snapshot of aggregated evaluation metrics for a provider."""

    __tablename__ = "evaluation_results"

    provider: Mapped[Provider] = mapped_column(enum_column(Provider), nullable=False)
    schema_pass_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    retry_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    hallucination_rate: Mapped[float | None] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        return (
            f"EvaluationResult(id={self.id!r}, provider={self.provider!r}, "
            f"schema_pass_rate={self.schema_pass_rate!r})"
        )
