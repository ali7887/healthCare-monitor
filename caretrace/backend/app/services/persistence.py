"""Transactional persistence for pipeline runs and human review.

Bridges the pure compute layer (``PipelineRunResult``) to the ORM. All writes
for a single run — the Run row, its ValidationLog rows, and (for HUMAN_REVIEW) a
ReviewItem — are committed within one transactional boundary. Review actions
(approve/reject) transition both the review item and its run.

Traceability: routing decision, routing reason, and the confidence breakdown are
stored on the Run exactly as computed so the UI can display them.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Run, ValidationLog
from app.models.enums import (
    IssueType,
    Provider,
    ReviewStatus,
    RoutingDecision,
    RunStatus,
    Severity,
)
from app.models.review_item import ReviewItem
from app.services.pipeline import PipelineRunResult
from app.services.reasoning import build_reasoning_summary
from app.services.routing import RoutingDecision as ServiceRoutingDecision

class ReviewConflictError(Exception):
    """Raised when a review action targets an already-decided (non-pending) item.

    A terminal decision (approved/rejected) is immutable; re-applying an action
    is a conflict rather than a silent no-op or a duplicate state transition.
    """


_DECISION_TO_STATUS: dict[str, RunStatus] = {
    ServiceRoutingDecision.AUTO_SAVE.value: RunStatus.auto_saved,
    ServiceRoutingDecision.HUMAN_REVIEW.value: RunStatus.needs_review,
    ServiceRoutingDecision.REJECT.value: RunStatus.rejected,
}


def _run_status(result: PipelineRunResult) -> RunStatus:
    if not result.succeeded:
        return RunStatus.failed
    return _DECISION_TO_STATUS[result.routing.decision.value]


def _note_dump(result: PipelineRunResult) -> dict[str, Any] | None:
    if result.extracted_note is None:
        return None
    return result.extracted_note.model_dump(mode="json")


def persist_run(
    db: Session,
    *,
    transcript: str,
    provider_name: str,
    result: PipelineRunResult,
) -> Run:
    """Persist a completed pipeline run and its issues in one transaction.

    Creates a ReviewItem when the routing decision is HUMAN_REVIEW.
    """
    confidence = result.confidence
    routing = result.routing
    note_dump = _note_dump(result)
    status = _run_status(result)

    warnings_count = sum(1 for issue in result.issues if issue.severity == "warning")

    reasoning_summary = build_reasoning_summary(
        succeeded=result.succeeded,
        decision=routing.decision.value if routing else None,
        confidence=confidence.score if confidence else None,
        issues=[(i.severity, i.message, i.rule_id) for i in result.issues],
    )

    run = Run(
        transcript=transcript,
        provider=Provider(provider_name),
        status=status,
        warnings_count=warnings_count,
        retry_count=result.retry_count,
        confidence=confidence.score if confidence else None,
        latency_ms=result.final_response.latency_ms,
        cost=result.final_response.estimated_cost,
        raw_model_response=result.final_response.raw_response_text,
        parsed_output=note_dump,
        final_output=note_dump if status == RunStatus.auto_saved else None,
        routing_decision=(
            RoutingDecision(routing.decision.value) if routing else None
        ),
        routing_reason=routing.routing_reason if routing else None,
        confidence_breakdown=(
            confidence.breakdown.model_dump(mode="json") if confidence else None
        ),
        reasoning_summary=reasoning_summary,
    )

    for issue in result.issues:
        run.validation_logs.append(
            ValidationLog(
                issue_type=IssueType(issue.issue_type),
                severity=Severity(issue.severity),
                field=issue.field_path,
                message=issue.message,
                rule_id=issue.rule_id,
            )
        )

    if routing and routing.decision == ServiceRoutingDecision.HUMAN_REVIEW:
        run.review_items.append(ReviewItem(status=ReviewStatus.pending))

    try:
        db.add(run)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(run)
    return run


def get_run(db: Session, run_id: UUID) -> Run | None:
    stmt = (
        select(Run)
        .where(Run.id == run_id)
        .options(
            selectinload(Run.validation_logs),
            selectinload(Run.review_items),
        )
    )
    return db.execute(stmt).scalar_one_or_none()


def pending_review_id(run: Run) -> UUID | None:
    """Return the id of the run's pending review item, if any."""
    for item in run.review_items:
        if item.status == ReviewStatus.pending:
            return item.id
    return None


def review_notes(run: Run) -> str | None:
    """Return the reviewer notes recorded on this run's review item, if any.

    A run has at most one review item; this surfaces the operator's notes for the
    read-only audit trail on decided runs (and any note saved on a pending item).
    """
    for item in run.review_items:
        if item.reviewer_notes:
            return item.reviewer_notes
    return None


def get_dashboard_timeseries(db: Session, *, days: int = 14) -> dict[str, object]:
    """Daily run counts grouped by routing decision, over the last ``days``.

    Buckets are computed in Python for dialect portability (SQLite in tests,
    Postgres in prod) and to fill empty days with zeros. Only two columns are
    read; at larger scale this can move to a SQL date_trunc + GROUP BY with a
    windowed WHERE clause.
    """
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=days - 1)

    rows = db.execute(select(Run.created_at, Run.routing_decision)).all()

    counts: dict[str, dict[str, int]] = {}
    for created_at, routing in rows:
        if created_at is None:
            continue
        day = created_at.date()
        if day < start or day > today:
            continue
        bucket = counts.setdefault(
            day.isoformat(), {"auto_save": 0, "human_review": 0, "reject": 0}
        )
        if routing is not None and routing.value in bucket:
            bucket[routing.value] += 1

    points: list[dict[str, object]] = []
    for offset in range(days):
        key = (start + timedelta(days=offset)).isoformat()
        bucket = counts.get(key, {"auto_save": 0, "human_review": 0, "reject": 0})
        total = bucket["auto_save"] + bucket["human_review"] + bucket["reject"]
        points.append({"bucket": key, **bucket, "total": total})

    return {"bucket": "day", "points": points}


def get_runs(
    db: Session,
    *,
    offset: int = 0,
    limit: int = 50,
    routing_decision: RoutingDecision | None = None,
    min_confidence: float | None = None,
    max_confidence: float | None = None,
) -> tuple[list[Run], int]:
    """Return filtered runs (newest first) and the total matching count.

    Uses server-side pagination and a separate COUNT query so the full table is
    never loaded into memory.
    """
    conditions = []
    if routing_decision is not None:
        conditions.append(Run.routing_decision == routing_decision)
    if min_confidence is not None:
        conditions.append(Run.confidence >= min_confidence)
    if max_confidence is not None:
        conditions.append(Run.confidence <= max_confidence)

    count_stmt = select(func.count()).select_from(Run)
    items_stmt = (
        select(Run)
        .options(
            selectinload(Run.validation_logs),
            selectinload(Run.review_items),
        )
        .order_by(Run.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if conditions:
        count_stmt = count_stmt.where(*conditions)
        items_stmt = items_stmt.where(*conditions)

    total = int(db.execute(count_stmt).scalar_one())
    items = list(db.execute(items_stmt).scalars().all())
    return items, total


def get_dashboard_stats(db: Session) -> dict[str, object]:
    """Compute dashboard metrics via SQL aggregation (no in-memory scans)."""

    def _count(decision: RoutingDecision | None = None) -> int:
        stmt = select(func.count()).select_from(Run)
        if decision is not None:
            stmt = stmt.where(Run.routing_decision == decision)
        return int(db.execute(stmt).scalar_one())

    avg_confidence = db.execute(select(func.avg(Run.confidence))).scalar()

    return {
        "total_runs": _count(),
        "accepted_runs": _count(RoutingDecision.auto_save),
        "routed_to_human_runs": _count(RoutingDecision.human_review),
        "rejected_runs": _count(RoutingDecision.reject),
        "average_confidence": round(float(avg_confidence or 0.0), 4),
    }


def list_pending_reviews(
    db: Session, *, limit: int = 50, offset: int = 0
) -> list[ReviewItem]:
    """Return pending review items (newest first) with their runs loaded."""
    stmt = (
        select(ReviewItem)
        .where(ReviewItem.status == ReviewStatus.pending)
        .order_by(ReviewItem.created_at.desc())
        .offset(offset)
        .limit(limit)
        .options(selectinload(ReviewItem.run).selectinload(Run.validation_logs))
    )
    return list(db.execute(stmt).scalars().all())


def count_pending_reviews(db: Session) -> int:
    stmt = (
        select(func.count())
        .select_from(ReviewItem)
        .where(ReviewItem.status == ReviewStatus.pending)
    )
    return int(db.execute(stmt).scalar_one())


def get_review(db: Session, review_id: UUID) -> ReviewItem | None:
    stmt = (
        select(ReviewItem)
        .where(ReviewItem.id == review_id)
        .options(selectinload(ReviewItem.run).selectinload(Run.validation_logs))
    )
    return db.execute(stmt).scalar_one_or_none()


def apply_review_action(
    db: Session,
    review_id: UUID,
    *,
    action: Literal["approve", "reject"],
    reviewer_notes: str | None = None,
    edited_output: dict[str, Any] | None = None,
) -> ReviewItem | None:
    """Apply a human decision to a pending review item and its run.

    Returns None if the review item does not exist.
    """
    review = get_review(db, review_id)
    if review is None:
        return None
    if review.status != ReviewStatus.pending:
        # Terminal decisions are immutable — surface a conflict, don't re-apply.
        raise ReviewConflictError(
            f"Review item is already {review.status.value}; no further action allowed."
        )

    run = review.run
    if reviewer_notes is not None:
        review.reviewer_notes = reviewer_notes

    if action == "approve":
        review.status = ReviewStatus.approved
        run.status = RunStatus.reviewed
        if edited_output is not None:
            review.edited_output = edited_output
            run.final_output = edited_output
        elif run.final_output is None:
            run.final_output = run.parsed_output
    else:  # reject
        review.status = ReviewStatus.rejected
        run.status = RunStatus.rejected

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(review)
    return review
