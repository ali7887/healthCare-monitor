"""DTOs for the human-review queue endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.clinical_note import ClinicalNote
from app.schemas.validation import ValidationIssue

ReviewStatusLiteral = Literal["pending", "approved", "rejected"]


class ReviewItemResponse(BaseModel):
    """A review-queue item with the run context a reviewer needs."""

    id: UUID
    run_id: UUID
    status: ReviewStatusLiteral
    confidence_score: float | None = None
    routing_reason: str | None = None
    note: ClinicalNote | None = None
    issues: list[ValidationIssue] = Field(default_factory=list)
    created_at: datetime


class ReviewListResponse(BaseModel):
    """Paginated list of pending review items."""

    items: list[ReviewItemResponse] = Field(default_factory=list)
    total: int


class ReviewActionRequest(BaseModel):
    """A human decision on a review item."""

    model_config = ConfigDict(extra="forbid")

    action: Literal["approve", "reject"]
    reviewer_notes: str | None = None
    edited_output: ClinicalNote | None = Field(
        default=None,
        description="Optional corrected note applied on approval.",
    )


class ReviewActionResponse(BaseModel):
    """Outcome of a review action."""

    id: UUID
    run_id: UUID
    status: ReviewStatusLiteral
    run_status: str
