"""Process endpoint DTOs (structure only; no routes in this phase).

Field names follow docs/API.md, which is the source of truth for the API
contract, while the nested payload uses the canonical schema types
(``ClinicalNote``, ``ValidationIssue``). The DTOs can represent every pipeline
outcome: ``auto_saved``, ``needs_review``, and ``failed`` (note/confidence may
be null on failure).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.clinical_note import ClinicalNote
from app.schemas.common import ProviderLiteral, RunStatusLiteral
from app.schemas.validation import ValidationIssue


class ProcessRequest(BaseModel):
    """Request body for processing a transcript."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "transcript": "Patient Anna Keller reported mild dizziness...",
                "provider": "openai",
            }
        },
    )

    transcript: str = Field(..., description="Raw nursing/caregiver transcript text.")
    provider: ProviderLiteral
    model: str | None = Field(
        default=None,
        description="Optional model override; defaults to the provider's configured model.",
    )


class ProcessResponse(BaseModel):
    """Response body describing the outcome of a processing run.

    Envelope fields align with docs/API.md. ``retry_used`` is a boolean (the
    persisted ``Run.retry_count`` maps to ``retry_used = retry_count > 0``);
    ``estimated_cost_usd`` mirrors the API contract's cost field.
    """

    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    status: RunStatusLiteral
    provider: ProviderLiteral
    prompt_version: str
    note: ClinicalNote | None = None
    issues: list[ValidationIssue] = Field(default_factory=list)
    retry_used: bool = False
    confidence: float | None = None
    latency_ms: int | None = None
    estimated_cost_usd: float | None = None
    created_at: datetime
