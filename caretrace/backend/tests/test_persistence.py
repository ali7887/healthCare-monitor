"""Unit tests for the persistence layer using an in-memory SQLite session."""

from app.models import Run
from app.models.enums import ReviewStatus, RunStatus
from app.schemas.clinical_note import ClinicalNote
from app.schemas.validation import ValidationIssue
from app.services.confidence import ConfidenceBreakdown, ConfidenceResult
from app.services.pipeline import PipelineRunResult
from app.services.providers import ExtractionResult
from app.services.persistence import apply_review_action, persist_run
from app.services.routing import RoutingDecision, RoutingResult


def _extraction() -> ExtractionResult:
    return ExtractionResult(
        provider="openai",
        model="gpt-4o-mini",
        prompt_version="clinical-extraction-v1",
        raw_response_text='{"ok": true}',
        content='{"ok": true}',
        latency_ms=12,
        estimated_cost=0.0004,
        retryable_error=False,
        error=None,
    )


def _confidence(score: float) -> ConfidenceResult:
    breakdown = ConfidenceBreakdown(
        failure_penalties=0.0,
        retry_penalties=0.0,
        severity_penalties=0.0,
        type_penalties=0.0,
        raw_score=score,
        final_score=score,
    )
    return ConfidenceResult(score=score, breakdown=breakdown, reasons=["r"])


def _result(
    *,
    decision: RoutingDecision,
    score: float,
    succeeded: bool = True,
    issues: list[ValidationIssue] | None = None,
    note: ClinicalNote | None = None,
) -> PipelineRunResult:
    extraction = _extraction()
    routing = RoutingResult(
        decision=decision, confidence_score=score, routing_reason=f"reason {decision.value}"
    )
    return PipelineRunResult(
        transcript="t",
        extracted_note=note if note is not None else (ClinicalNote() if succeeded else None),
        issues=issues or [],
        raw_response=extraction,
        final_response=extraction,
        succeeded=succeeded,
        confidence=_confidence(score),
        routing=routing,
    )


def test_persist_auto_save(db_session):
    issues = [ValidationIssue(severity="warning", issue_type="completeness", message="m", rule_id="ERR_X")]
    result = _result(decision=RoutingDecision.AUTO_SAVE, score=0.95, issues=issues)
    run = persist_run(db_session, transcript="t", provider_name="openai", result=result)

    assert run.status == RunStatus.auto_saved
    assert run.routing_decision.value == "auto_save"
    assert run.routing_reason == "reason auto_save"
    assert run.confidence == 0.95
    assert run.confidence_breakdown is not None  # breakdown persisted for the UI
    assert run.warnings_count == 1
    assert len(run.validation_logs) == 1
    assert run.validation_logs[0].rule_id == "ERR_X"
    assert run.validation_logs[0].severity.value == "warning"
    assert run.final_output is not None  # auto-saved -> final == parsed
    assert run.review_items == []


def test_persist_human_review_creates_pending_review(db_session):
    issues = [ValidationIssue(severity="critical", issue_type="clinical", message="m", rule_id="ERR_SPO2_LOW")]
    result = _result(decision=RoutingDecision.HUMAN_REVIEW, score=0.84, issues=issues)
    run = persist_run(db_session, transcript="t", provider_name="openai", result=result)

    assert run.status == RunStatus.needs_review
    assert len(run.review_items) == 1
    assert run.review_items[0].status == ReviewStatus.pending
    assert run.final_output is None


def test_persist_reject(db_session):
    result = _result(decision=RoutingDecision.REJECT, score=0.30)
    run = persist_run(db_session, transcript="t", provider_name="openai", result=result)
    assert run.status == RunStatus.rejected
    assert run.review_items == []


def test_persist_failed_when_not_succeeded(db_session):
    result = _result(decision=RoutingDecision.REJECT, score=0.10, succeeded=False)
    run = persist_run(db_session, transcript="t", provider_name="openai", result=result)
    assert run.status == RunStatus.failed


def test_apply_review_action_approve_with_edit(db_session):
    result = _result(decision=RoutingDecision.HUMAN_REVIEW, score=0.80)
    run = persist_run(db_session, transcript="t", provider_name="openai", result=result)
    review = run.review_items[0]

    edited = {"note_summary": "corrected by reviewer"}
    updated = apply_review_action(
        db_session, review.id, action="approve", reviewer_notes="looks ok", edited_output=edited
    )

    assert updated is not None
    assert updated.status == ReviewStatus.approved
    assert updated.reviewer_notes == "looks ok"
    refreshed = db_session.get(Run, run.id)
    assert refreshed.status == RunStatus.reviewed
    assert refreshed.final_output == edited


def test_apply_review_action_reject(db_session):
    result = _result(decision=RoutingDecision.HUMAN_REVIEW, score=0.80)
    run = persist_run(db_session, transcript="t", provider_name="openai", result=result)
    review = run.review_items[0]

    updated = apply_review_action(db_session, review.id, action="reject")
    assert updated.status == ReviewStatus.rejected
    assert db_session.get(Run, run.id).status == RunStatus.rejected


def test_apply_review_action_missing_returns_none(db_session):
    import uuid

    assert apply_review_action(db_session, uuid.uuid4(), action="approve") is None
