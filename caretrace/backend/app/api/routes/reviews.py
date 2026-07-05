"""Human-review queue endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core import telemetry
from app.models import Run
from app.models.review_item import ReviewItem
from app.models.validation_log import ValidationLog
from app.schemas.clinical_note import ClinicalNote
from app.schemas.review import (
    ReviewActionRequest,
    ReviewActionResponse,
    ReviewItemResponse,
    ReviewListResponse,
)
from app.schemas.validation import ValidationIssue
from app.services.persistence import (
    ReviewConflictError,
    apply_review_action,
    count_pending_reviews,
    list_pending_reviews,
)

router = APIRouter(prefix="/reviews", tags=["reviews"])


def _issue_from_log(log: ValidationLog) -> ValidationIssue:
    return ValidationIssue(
        severity=log.severity.value if log.severity else "warning",
        issue_type=log.issue_type.value,
        field_path=log.field,
        message=log.message,
        rule_id=log.rule_id,
    )


def _to_response(item: ReviewItem) -> ReviewItemResponse:
    run: Run = item.run
    note = (
        ClinicalNote.model_validate(run.parsed_output)
        if run.parsed_output
        else None
    )
    return ReviewItemResponse(
        id=item.id,
        run_id=item.run_id,
        status=item.status.value,
        confidence_score=run.confidence,
        routing_reason=run.routing_reason,
        note=note,
        issues=[_issue_from_log(log) for log in run.validation_logs],
        created_at=item.created_at,
    )


@router.get("", response_model=ReviewListResponse)
def list_reviews(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ReviewListResponse:
    """List pending review items (newest first)."""
    items = list_pending_reviews(db, limit=limit, offset=offset)
    return ReviewListResponse(
        items=[_to_response(item) for item in items],
        total=count_pending_reviews(db),
    )


@router.post("/{review_id}/action", response_model=ReviewActionResponse)
def review_action(
    review_id: UUID,
    payload: ReviewActionRequest,
    db: Session = Depends(get_db),
) -> ReviewActionResponse:
    """Approve or reject a review item, applying any manual corrections."""
    edited = (
        payload.edited_output.model_dump(mode="json")
        if payload.edited_output is not None
        else None
    )
    try:
        review = apply_review_action(
            db,
            review_id,
            action=payload.action,
            reviewer_notes=payload.reviewer_notes,
            edited_output=edited,
        )
    except ReviewConflictError as exc:
        telemetry.log_review_conflict(review_id=review_id)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if review is None:
        telemetry.log_review_not_found(review_id=review_id)
        raise HTTPException(status_code=404, detail="Review item not found")
    telemetry.log_review_decision(
        review_id=review.id,
        run_id=review.run_id,
        action=payload.action,
        run_status=review.run.status.value,
        edited=edited is not None,
    )
    return ReviewActionResponse(
        id=review.id,
        run_id=review.run_id,
        status=review.status.value,
        run_status=review.run.status.value,
    )
