"""Read-model DTOs for run listing, deep-trace detail, and dashboard stats.

Field names/values reflect the real ``Run`` ORM model (e.g. ``confidence`` and
routing values ``auto_save``/``human_review``/``reject``) rather than the
generic placeholders in the Phase 11 brief. The confidence breakdown mirrors the
value actually stored by the confidence engine; ``raw_score`` is intentionally
unconstrained because it may be negative before clamping.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.clinical_note import ClinicalNote
from app.schemas.common import ProviderLiteral, RunStatusLiteral
from app.schemas.process import RoutingDecisionLiteral
from app.schemas.validation import ValidationIssue


class ConfidenceBreakdownSchema(BaseModel):
    """Typed view of the stored confidence breakdown."""

    model_config = ConfigDict(from_attributes=True)

    base_score: float
    failure_penalties: float
    retry_penalties: float
    severity_penalties: float
    type_penalties: float
    raw_score: float
    final_score: float


class RunDetailResponse(BaseModel):
    """Full trace of a single run (deep tracing)."""

    id: UUID
    provider: ProviderLiteral
    status: RunStatusLiteral
    transcript: str
    parsed_output: ClinicalNote | None = None
    final_output: dict[str, Any] | None = None
    confidence_score: float | None = None
    confidence_breakdown: ConfidenceBreakdownSchema | None = None
    routing_decision: RoutingDecisionLiteral | None = None
    routing_reason: str | None = None
    retry_count: int = 0
    warnings_count: int = 0
    latency_ms: int | None = None
    cost: float | None = None
    raw_model_response: str | None = None
    issues: list[ValidationIssue] = Field(default_factory=list)
    created_at: datetime
    # Pending review item for this run (null unless status is needs_review).
    pending_review_id: UUID | None = None
    # Step-by-step account of the routing decision (Phase 20).
    reasoning_summary: str | None = None
    # Operator notes recorded on the review item — the read-only audit trail on
    # decided runs.
    reviewer_notes: str | None = None


class PaginatedRunResponse(BaseModel):
    """A page of runs with the total matching count."""

    items: list[RunDetailResponse] = Field(default_factory=list)
    total: int
    limit: int
    offset: int


class DashboardStatsResponse(BaseModel):
    """Aggregated run metrics for the dashboard."""

    total_runs: int
    accepted_runs: int
    routed_to_human_runs: int
    rejected_runs: int
    average_confidence: float


class TimeseriesPoint(BaseModel):
    """One time bucket of run counts, grouped by routing decision."""

    bucket: str  # ISO date, e.g. "2026-07-04"
    auto_save: int
    human_review: int
    reject: int
    total: int


class DashboardTimeseriesResponse(BaseModel):
    """Bucketed dashboard metrics for trend charts."""

    bucket: str  # granularity, currently always "day"
    points: list[TimeseriesPoint] = Field(default_factory=list)
