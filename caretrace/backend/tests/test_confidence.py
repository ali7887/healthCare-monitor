"""Tests for the deterministic confidence scoring engine.

All inputs are fixed/stubbed objects; no network or provider calls.
"""

import pytest

from app.schemas.clinical_note import ClinicalNote
from app.schemas.validation import ValidationIssue
from app.services.confidence import ConfidenceScorer
from app.services.pipeline import PipelineRunResult
from app.services.providers import ExtractionResult

_NOTE_SENTINEL = object()


def _extraction() -> ExtractionResult:
    return ExtractionResult(
        provider="openai",
        model="gpt-4o-mini",
        prompt_version="clinical-extraction-v1",
        raw_response_text="{}",
        content="{}",
        latency_ms=1,
        estimated_cost=0.0,
        retryable_error=False,
        error=None,
    )


def _run(
    *,
    succeeded: bool = True,
    note=_NOTE_SENTINEL,
    issues: list[ValidationIssue] | None = None,
    retry_count: int = 0,
    retry_trigger: str | None = None,
) -> PipelineRunResult:
    extraction = _extraction()
    extracted_note = ClinicalNote() if note is _NOTE_SENTINEL else note
    return PipelineRunResult(
        transcript="t",
        extracted_note=extracted_note,
        issues=issues or [],
        raw_response=extraction,
        final_response=extraction,
        succeeded=succeeded,
        retry_count=retry_count,
        initial_response=None,
        retry_trigger=retry_trigger,
    )


def _issue(severity: str, issue_type: str) -> ValidationIssue:
    return ValidationIssue(
        severity=severity, issue_type=issue_type, message="x", rule_id="R"
    )


def _score(**kwargs) -> float:
    return ConfidenceScorer().calculate(_run(**kwargs)).score


# --- 1. perfect execution ---------------------------------------------------


def test_perfect_execution():
    result = ConfidenceScorer().calculate(_run())
    assert result.score == 1.0
    assert result.breakdown.final_score == 1.0
    assert result.breakdown.raw_score == 1.0
    assert result.reasons == []


# --- 2. pipeline failure clamps to 0.0 --------------------------------------


def test_pipeline_failure_clamping():
    issues = [_issue("critical", "clinical") for _ in range(5)]
    result = ConfidenceScorer().calculate(
        _run(succeeded=False, note=None, issues=issues)
    )
    assert result.score == 0.0
    assert result.breakdown.final_score == 0.0
    # raw score dips below zero before clamping
    assert result.breakdown.raw_score < 0.0
    # failure penalties = 0.40 + 0.50
    assert result.breakdown.failure_penalties == pytest.approx(0.90)
    assert result.breakdown.severity_penalties == pytest.approx(0.48)  # capped
    assert any("did not succeed" in r for r in result.reasons)
    assert any("No clinical note" in r for r in result.reasons)


# --- 3. retry triggers ------------------------------------------------------


def test_retry_reduces_confidence_and_triggers_are_cumulative():
    no_retry = _score(retry_count=0)
    with_retry = _score(retry_count=1, retry_trigger="invalid_json")
    assert with_retry < no_retry

    # 0.15 (retry) + 0.15 (invalid_json)
    assert with_retry == pytest.approx(0.70)
    # provider_retryable_error add-on is smaller -> higher score
    assert _score(retry_count=1, retry_trigger="provider_retryable_error") == pytest.approx(0.77)
    assert _score(retry_count=1, retry_trigger="schema_validation_failed") == pytest.approx(0.73)
    # retry with no/unknown trigger applies only the base retry penalty
    assert _score(retry_count=1, retry_trigger=None) == pytest.approx(0.85)


# --- 4. severity caps -------------------------------------------------------


def test_severity_caps():
    issues = [_issue("critical", "clinical") for _ in range(5)]
    issues += [_issue("warning", "clinical") for _ in range(8)]
    breakdown = ConfidenceScorer().calculate(_run(issues=issues)).breakdown
    # 5*0.12=0.60 -> capped 0.48 ; 8*0.04=0.32 -> capped 0.24
    assert breakdown.severity_penalties == pytest.approx(0.72)


# --- 5. type caps -----------------------------------------------------------


def test_type_caps():
    issues = []
    for issue_type in ("schema", "format", "clinical", "completeness"):
        issues += [_issue("warning", issue_type) for _ in range(5)]
    breakdown = ConfidenceScorer().calculate(_run(issues=issues)).breakdown
    # 0.18 + 0.15 + 0.16 + 0.12
    assert breakdown.type_penalties == pytest.approx(0.61)


# --- extra reliability checks ----------------------------------------------


def test_warning_only_reduces_moderately_without_collapse():
    issues = [_issue("warning", "completeness") for _ in range(3)]
    score = ConfidenceScorer().calculate(_run(issues=issues)).score
    assert 0.5 < score < 1.0


def test_score_always_clamped_between_zero_and_one():
    high = ConfidenceScorer().calculate(_run()).score
    low = ConfidenceScorer().calculate(
        _run(succeeded=False, note=None, issues=[_issue("critical", "schema") for _ in range(10)])
    ).score
    assert 0.0 <= low <= 1.0
    assert 0.0 <= high <= 1.0


def test_deterministic_for_same_input():
    issues = [_issue("critical", "clinical"), _issue("warning", "completeness")]
    a = ConfidenceScorer().calculate(_run(issues=issues, retry_count=1, retry_trigger="invalid_json"))
    b = ConfidenceScorer().calculate(_run(issues=issues, retry_count=1, retry_trigger="invalid_json"))
    assert a.score == b.score
    assert a.reasons == b.reasons
    assert a.breakdown.model_dump() == b.breakdown.model_dump()


def test_breakdown_and_reasons_are_populated():
    issues = [_issue("critical", "clinical")]
    result = ConfidenceScorer().calculate(_run(issues=issues, retry_count=1, retry_trigger="invalid_json"))
    assert result.reasons  # non-empty audit trail
    assert result.breakdown.base_score == 1.0
    assert result.breakdown.retry_penalties == pytest.approx(0.30)
    assert result.score == pytest.approx(result.breakdown.final_score)
