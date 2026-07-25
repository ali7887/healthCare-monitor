"""Evaluation dashboard schemas (aggregated reliability metrics)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvaluationTotals(BaseModel):
    """Run counts by terminal status."""

    runs: int
    auto_saved: int
    needs_review: int
    reviewed: int
    rejected: int
    failed: int


class ProviderEvaluation(BaseModel):
    """Reliability metrics for one provider (model comparison row)."""

    provider: str
    runs: int
    auto_save_rate: float
    retry_rate: float
    avg_confidence: float | None = None
    avg_latency_ms: float | None = None
    estimated_cost_usd: float


class EvaluationResponse(BaseModel):
    """Aggregated evaluation metrics (docs/API.md → GET /api/evaluation)."""

    totals: EvaluationTotals
    by_provider: list[ProviderEvaluation] = Field(default_factory=list)
