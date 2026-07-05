"""Read endpoints for runs: list/filter/paginate and deep-trace detail."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Run
from app.models.enums import RoutingDecision
from app.models.validation_log import ValidationLog
from app.schemas.assistant import (
    AssistantAnalysisResponse,
    AssistantAnalyzeRequest,
)
from app.schemas.clinical_note import ClinicalNote
from app.schemas.run import (
    ConfidenceBreakdownSchema,
    PaginatedRunResponse,
    RunDetailResponse,
)
from app.schemas.validation import ValidationIssue
from app.services.assistant import AssistantService, RunNotFoundError
from app.services.persistence import (
    get_run,
    get_runs,
    pending_review_id,
    review_notes,
)

router = APIRouter(prefix="/runs", tags=["runs"])


def _issue_from_log(log: ValidationLog) -> ValidationIssue:
    return ValidationIssue(
        severity=log.severity.value if log.severity else "warning",
        issue_type=log.issue_type.value,
        field_path=log.field,
        message=log.message,
        rule_id=log.rule_id,
    )


def _to_detail(run: Run) -> RunDetailResponse:
    note = (
        ClinicalNote.model_validate(run.parsed_output) if run.parsed_output else None
    )
    breakdown = (
        ConfidenceBreakdownSchema.model_validate(run.confidence_breakdown)
        if run.confidence_breakdown
        else None
    )
    return RunDetailResponse(
        id=run.id,
        provider=run.provider.value,
        status=run.status.value,
        transcript=run.transcript,
        parsed_output=note,
        final_output=run.final_output,
        confidence_score=run.confidence,
        confidence_breakdown=breakdown,
        routing_decision=run.routing_decision.value if run.routing_decision else None,
        routing_reason=run.routing_reason,
        retry_count=run.retry_count,
        warnings_count=run.warnings_count,
        latency_ms=run.latency_ms,
        cost=run.cost,
        raw_model_response=run.raw_model_response,
        issues=[_issue_from_log(log) for log in run.validation_logs],
        created_at=run.created_at,
        pending_review_id=pending_review_id(run),
        reasoning_summary=run.reasoning_summary,
        reviewer_notes=review_notes(run),
    )


@router.get("", response_model=PaginatedRunResponse)
def list_runs(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    routing_decision: RoutingDecision | None = Query(default=None),
    min_confidence: float | None = Query(default=None, ge=0.0, le=1.0),
    max_confidence: float | None = Query(default=None, ge=0.0, le=1.0),
) -> PaginatedRunResponse:
    """List runs (newest first) with optional filters and pagination."""
    items, total = get_runs(
        db,
        offset=offset,
        limit=limit,
        routing_decision=routing_decision,
        min_confidence=min_confidence,
        max_confidence=max_confidence,
    )
    return PaginatedRunResponse(
        items=[_to_detail(run) for run in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{run_id}", response_model=RunDetailResponse)
def get_run_detail(
    run_id: UUID, db: Session = Depends(get_db)
) -> RunDetailResponse:
    """Return the full trace for a single run (404 if not found)."""
    run = get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return _to_detail(run)


@router.post("/{run_id}/analyze", response_model=AssistantAnalysisResponse)
async def analyze_run(
    run_id: UUID,
    payload: AssistantAnalyzeRequest,
    db: Session = Depends(get_db),
) -> AssistantAnalysisResponse:
    """Advisory AI-assistant analysis of the reviewer's current output.

    Returns potential clinical risks, an advisory suggestion, and a synthetic
    confidence. Advisory only — it never changes the run. 404 if the run does
    not exist; 422 if ``edited_output`` is not a JSON object.
    """
    try:
        analysis = await AssistantService().analyze_review(
            db, run_id, payload.edited_output
        )
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    return AssistantAnalysisResponse(
        clinical_risks=analysis.clinical_risks,
        suggestion=analysis.suggestion,
        confidence_score=analysis.confidence_score,
    )
