"""Tests for the processing pipeline and its single bounded retry.

All provider interaction is stubbed; no live network or API keys are used.
"""

import json

from app.services.pipeline import (
    RETRY_TRIGGER_INVALID_JSON,
    RETRY_TRIGGER_PROVIDER,
    RETRY_TRIGGER_SCHEMA,
    ProcessingPipeline,
)
from app.services.providers import ExtractionResult

# --- fixtures / helpers -----------------------------------------------------

NORMAL_NOTE = {
    "patient": {"name": "Anna Keller"},
    "vitals": {
        "blood_pressure": {"systolic": 138, "diastolic": 86, "unit": "mmHg"},
        "heart_rate": {"value": 78, "unit": "bpm"},
        "temperature": {"value": 36.8, "unit": "C"},
        "spo2": {"value": 97, "unit": "%"},
    },
    "medications": [{"name": "Metformin", "dose": "500mg", "route": "oral"}],
    "observations": [{"text": "resting comfortably"}],
}

HIGH_BP_NOTE = {
    "vitals": {"blood_pressure": {"systolic": 185, "diastolic": 105}},
    "observations": [{"text": "dizziness reported"}],
}


def _ok(content: str) -> ExtractionResult:
    return ExtractionResult(
        provider="openai",
        model="gpt-4o-mini",
        prompt_version="clinical-extraction-v1",
        raw_response_text=content,
        content=content,
        latency_ms=10,
        estimated_cost=0.0,
        retryable_error=False,
        error=None,
        prompt_tokens=10,
        completion_tokens=5,
    )


def _err(*, retryable: bool) -> ExtractionResult:
    return ExtractionResult(
        provider="openai",
        model="gpt-4o-mini",
        prompt_version="clinical-extraction-v1",
        raw_response_text=None,
        content=None,
        latency_ms=5,
        estimated_cost=0.0,
        retryable_error=retryable,
        error="provider failure",
        prompt_tokens=None,
        completion_tokens=None,
    )


class _StubProvider:
    """Returns queued ExtractionResults on successive extract() calls."""

    name = "openai"

    def __init__(self, results: list[ExtractionResult]) -> None:
        self._results = list(results)
        self.calls: list[str] = []

    def extract(self, transcript: str) -> ExtractionResult:
        self.calls.append(transcript)
        return self._results.pop(0)


def _pipeline(stub: _StubProvider) -> ProcessingPipeline:
    return ProcessingPipeline(provider_factory=lambda name, **kw: stub)


def _rule_ids(result) -> set[str]:
    return {i.rule_id for i in result.issues}


# --- 1. happy path: no retry ------------------------------------------------


def test_happy_path_no_retry():
    stub = _StubProvider([_ok(json.dumps(NORMAL_NOTE))])
    result = _pipeline(stub).run("transcript", "openai")

    assert result.retry_count == 0
    assert result.succeeded
    assert result.extracted_note is not None
    assert result.issues == []
    assert result.retry_trigger is None
    assert result.initial_response is None
    assert result.final_response is result.raw_response
    assert len(stub.calls) == 1


# --- 2. retry on retryable provider failure ---------------------------------


def test_retryable_provider_failure_retries_once_then_succeeds():
    stub = _StubProvider([_err(retryable=True), _ok(json.dumps(NORMAL_NOTE))])
    result = _pipeline(stub).run("the transcript", "openai")

    assert result.retry_count == 1
    assert result.succeeded
    assert result.retry_trigger == RETRY_TRIGGER_PROVIDER
    assert result.initial_response is not None
    assert result.initial_response.error == "provider failure"
    assert result.extracted_note is not None
    assert len(stub.calls) == 2
    # retry prompt carried the original transcript, no fabricated prior output
    assert "the transcript" in stub.calls[1]


# --- 3. no retry on permanent provider failure ------------------------------


def test_permanent_provider_failure_does_not_retry():
    stub = _StubProvider([_err(retryable=False)])
    result = _pipeline(stub).run("transcript", "openai")

    assert result.retry_count == 0
    assert not result.succeeded
    assert result.extracted_note is None
    assert result.retry_trigger is None
    assert result.raw_response.error == "provider failure"
    assert len(stub.calls) == 1


# --- 4. retry on invalid JSON / schema failure ------------------------------


def test_invalid_json_retries_and_corrects():
    stub = _StubProvider([_ok("this is not json"), _ok(json.dumps(NORMAL_NOTE))])
    result = _pipeline(stub).run("transcript", "openai")

    assert result.retry_count == 1
    assert result.succeeded
    assert result.retry_trigger == RETRY_TRIGGER_INVALID_JSON
    # first raw output preserved for later inspection
    assert result.initial_response is not None
    assert result.initial_response.raw_response_text == "this is not json"
    assert result.retry_context_summary == "previous output was not valid JSON"
    # correction prompt quoted the bad output
    assert "this is not json" in stub.calls[1]
    assert len(stub.calls) == 2


def test_schema_shape_failure_retries():
    # medication missing required 'name' -> schema-shape failure -> note is None
    bad = json.dumps({"medications": [{"dose": "500mg"}]})
    stub = _StubProvider([_ok(bad), _ok(json.dumps(NORMAL_NOTE))])
    result = _pipeline(stub).run("transcript", "openai")

    assert result.retry_count == 1
    assert result.succeeded
    assert result.retry_trigger == RETRY_TRIGGER_SCHEMA
    assert result.retry_context_summary.startswith("schema issue fields")


def test_markdown_fenced_json_is_parsed_without_retry():
    fenced = "```json\n" + json.dumps(NORMAL_NOTE) + "\n```"
    stub = _StubProvider([_ok(fenced)])
    result = _pipeline(stub).run("transcript", "openai")

    assert result.retry_count == 0
    assert result.succeeded
    assert result.extracted_note is not None


# --- 5. no retry for clinical issues only -----------------------------------


def test_clinical_issues_only_do_not_trigger_retry():
    stub = _StubProvider([_ok(json.dumps(HIGH_BP_NOTE))])
    result = _pipeline(stub).run("transcript", "openai")

    assert result.retry_count == 0
    assert result.succeeded  # valid note despite clinical issues
    assert result.extracted_note is not None
    assert "ERR_BP_SYSTOLIC_HIGH" in _rule_ids(result)
    assert result.retry_trigger is None
    assert len(stub.calls) == 1


# --- 6. retry remains bounded -----------------------------------------------


def test_second_attempt_failure_stops_at_one_retry():
    stub = _StubProvider([_ok("not json"), _ok("still not json")])
    result = _pipeline(stub).run("transcript", "openai")

    assert result.retry_count == 1
    assert not result.succeeded
    assert result.extracted_note is None
    assert result.retry_trigger == RETRY_TRIGGER_INVALID_JSON
    assert result.initial_response is not None
    assert "ERR_SCHEMA_INVALID_JSON" in _rule_ids(result)
    assert len(stub.calls) == 2  # never a third attempt


def test_retryable_then_permanent_failure_stops_cleanly():
    stub = _StubProvider([_err(retryable=True), _err(retryable=False)])
    result = _pipeline(stub).run("transcript", "openai")

    assert result.retry_count == 1
    assert not result.succeeded
    assert result.retry_trigger == RETRY_TRIGGER_PROVIDER
    assert result.raw_response.retryable_error is False
    assert result.final_response.error == "provider failure"
    assert len(stub.calls) == 2
