"""Tests for the deterministic routing engine and pipeline routing output.

Deterministic; no network, provider, or database access.
"""

import json

from app.schemas.clinical_note import ClinicalNote
from app.schemas.validation import ValidationIssue
from app.services.confidence import ConfidenceBreakdown, ConfidenceResult
from app.services.pipeline import PipelineRunResult, ProcessingPipeline
from app.services.providers import ExtractionResult
from app.services.routing import RoutingDecision, RoutingEngine

# --- helpers ----------------------------------------------------------------


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


def _run(*, issues: list[ValidationIssue] | None = None) -> PipelineRunResult:
    extraction = _extraction()
    return PipelineRunResult(
        transcript="t",
        extracted_note=ClinicalNote(),
        issues=issues or [],
        raw_response=extraction,
        final_response=extraction,
        succeeded=True,
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
    return ConfidenceResult(score=score, breakdown=breakdown, reasons=[])


def _critical() -> ValidationIssue:
    return ValidationIssue(
        severity="critical", issue_type="clinical", message="x", rule_id="ERR_SPO2_LOW"
    )


# --- routing decisions ------------------------------------------------------


def test_route_auto_save():
    result = RoutingEngine().route(_run(), _confidence(0.90))
    assert result.decision is RoutingDecision.AUTO_SAVE
    assert "AUTO_SAVE" in result.routing_reason


def test_route_human_review_due_to_score():
    result = RoutingEngine().route(_run(), _confidence(0.70))
    assert result.decision is RoutingDecision.HUMAN_REVIEW
    assert "review band" in result.routing_reason


def test_route_human_review_due_to_critical_issue():
    result = RoutingEngine().route(_run(issues=[_critical()]), _confidence(0.90))
    assert result.decision is RoutingDecision.HUMAN_REVIEW
    assert "critical" in result.routing_reason


def test_route_reject():
    result = RoutingEngine().route(_run(), _confidence(0.30))
    assert result.decision is RoutingDecision.REJECT
    assert "REJECT" in result.routing_reason


def test_routing_boundaries():
    assert RoutingEngine().route(_run(), _confidence(0.85)).decision is RoutingDecision.AUTO_SAVE
    assert RoutingEngine().route(_run(), _confidence(0.50)).decision is RoutingDecision.HUMAN_REVIEW
    assert RoutingEngine().route(_run(), _confidence(0.4999)).decision is RoutingDecision.REJECT


# --- pipeline attaches routing + confidence (pure, no side effects) ---------


class _StubProvider:
    name = "openai"

    def __init__(self, content: str) -> None:
        self._content = content

    def extract(self, transcript: str) -> ExtractionResult:
        return ExtractionResult(
            provider="openai",
            model="gpt-4o-mini",
            prompt_version="clinical-extraction-v1",
            raw_response_text=self._content,
            content=self._content,
            latency_ms=10,
            estimated_cost=0.0,
            retryable_error=False,
            error=None,
        )


def _pipeline_for(content: str) -> ProcessingPipeline:
    return ProcessingPipeline(provider_factory=lambda name, **kw: _StubProvider(content))


def test_pipeline_attaches_auto_save_for_clean_note():
    clean = {
        "vitals": {"blood_pressure": {"systolic": 120, "diastolic": 80}, "spo2": {"value": 98}},
        "observations": [{"text": "stable"}],
    }
    result = _pipeline_for(json.dumps(clean)).run("transcript", "openai")
    assert result.routing is not None
    assert result.routing.decision is RoutingDecision.AUTO_SAVE
    assert result.confidence is not None and result.confidence.score == 1.0


def test_pipeline_attaches_human_review_for_critical_note():
    critical_note = {"vitals": {"spo2": {"value": 90}}, "observations": [{"text": "x"}]}
    result = _pipeline_for(json.dumps(critical_note)).run("transcript", "openai")
    assert result.routing.decision is RoutingDecision.HUMAN_REVIEW
