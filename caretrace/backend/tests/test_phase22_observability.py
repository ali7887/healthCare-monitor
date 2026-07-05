"""Phase 22: observability — request correlation, timing, structured telemetry.

Covers the behavior operators rely on: a correlation id is minted (or preserved)
per request and echoed on the response, each request emits a timed
``http_request`` event, and the critical review/assistant/dashboard flows emit
safe, structured telemetry. Logs are captured by attaching a handler to the
application logger and formatting each record with the real JSON formatter, so
these tests exercise the actual log output (including the request-scoped id).
"""

from __future__ import annotations

import json
import logging
import uuid

import pytest

from app.core.logging import JsonLogFormatter, get_logger, log_event, set_request_id
from app.core.middleware import REQUEST_ID_HEADER
from app.models import Run
from app.models.enums import Provider, ReviewStatus, RoutingDecision, RunStatus
from app.models.review_item import ReviewItem


@pytest.fixture
def log_records():
    """Capture application logs as parsed JSON (formatted with the real formatter)."""
    logger = logging.getLogger("caretrace")
    formatter = JsonLogFormatter()
    captured: list[dict] = []

    class Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(json.loads(formatter.format(record)))

    handler = Capture()
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)
    prev_level = logger.level
    logger.setLevel(logging.INFO)
    try:
        yield captured
    finally:
        logger.removeHandler(handler)
        logger.setLevel(prev_level)


def _events(records: list[dict], event: str) -> list[dict]:
    return [r for r in records if r.get("event") == event]


# --- logging foundation ------------------------------------------------------


def test_log_event_emits_structured_json_with_context(log_records):
    set_request_id("ctx-abc")
    try:
        log_event(get_logger("unit"), "unit_event", foo="bar", count=3)
    finally:
        set_request_id(None)

    record = _events(log_records, "unit_event")[0]
    assert record["message"] == "unit_event"
    assert record["request_id"] == "ctx-abc"
    assert record["foo"] == "bar"
    assert record["count"] == 3
    assert record["level"] == "INFO"


# --- request id + timing middleware ------------------------------------------


def test_response_includes_generated_request_id(client):
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 200
    request_id = response.headers.get(REQUEST_ID_HEADER)
    assert request_id
    # A generated id is a uuid4 hex (32 hex chars).
    assert len(request_id) == 32


def test_incoming_request_id_is_preserved(client, log_records):
    supplied = "trace-me-123"
    response = client.get(
        "/api/dashboard/stats", headers={REQUEST_ID_HEADER: supplied}
    )
    assert response.headers.get(REQUEST_ID_HEADER) == supplied
    # The same id threads into the request-scoped logs.
    http = [r for r in _events(log_records, "http_request") if r.get("request_id") == supplied]
    assert http, "expected an http_request log carrying the supplied request id"


def test_http_request_event_records_method_path_status_and_timing(client, log_records):
    client.get("/api/dashboard/stats")
    http = [r for r in _events(log_records, "http_request") if r["path"] == "/api/dashboard/stats"]
    assert http
    event = http[-1]
    assert event["method"] == "GET"
    assert event["status_code"] == 200
    assert isinstance(event["duration_ms"], (int, float))
    assert event["duration_ms"] >= 0
    assert "request_id" in event


# --- domain telemetry --------------------------------------------------------


def _needs_review_run(db_session) -> Run:
    run = Run(
        transcript="t",
        provider=Provider.openai,
        status=RunStatus.needs_review,
        confidence=0.7,
        routing_decision=RoutingDecision.human_review,
        routing_reason="low confidence",
        parsed_output={"vitals": {"blood_pressure": {"systolic": 172, "diastolic": 101}}},
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run


def test_run_detail_fetch_is_logged(client, db_session, log_records):
    run = _needs_review_run(db_session)
    client.get(f"/api/runs/{run.id}")
    found = _events(log_records, "run_detail_fetch")
    assert any(r["run_id"] == str(run.id) and r["outcome"] == "found" for r in found)


def test_assistant_analysis_logs_request_and_risk_alert(client, db_session, log_records):
    run = _needs_review_run(db_session)
    response = client.post(
        f"/api/runs/{run.id}/analyze",
        json={"edited_output": {"vitals": {"blood_pressure": {"systolic": 172, "diastolic": 101}}}},
    )
    assert response.status_code == 200

    requested = _events(log_records, "assistant_analyze_request")
    assert any(r["run_id"] == str(run.id) for r in requested)

    success = _events(log_records, "assistant_analyze_success")
    hit = [r for r in success if r["run_id"] == str(run.id)]
    assert hit
    # A high-BP note produces risks → the outcome mirrors the UI "Risk alert".
    assert hit[-1]["risk_count"] >= 1
    assert hit[-1]["outcome"] == "risk_alert"


def test_assistant_unknown_run_logs_failure(client, log_records):
    unknown = uuid.uuid4()
    response = client.post(f"/api/runs/{unknown}/analyze", json={"edited_output": {}})
    assert response.status_code == 404
    failures = _events(log_records, "assistant_analyze_failure")
    assert any(r["run_id"] == str(unknown) and r["outcome"] == "failure" for r in failures)


def test_review_conflict_is_logged(client, db_session, log_records):
    # A decided review item: acting on it again must 409 and log a conflict.
    run = _needs_review_run(db_session)
    review = ReviewItem(run_id=run.id, status=ReviewStatus.approved)
    db_session.add(review)
    db_session.commit()
    db_session.refresh(review)

    response = client.post(
        f"/api/reviews/{review.id}/action", json={"action": "approve"}
    )
    assert response.status_code == 409
    conflicts = _events(log_records, "review_conflict")
    assert any(r["review_id"] == str(review.id) for r in conflicts)


def test_dashboard_stats_fetch_is_logged(client, log_records):
    client.get("/api/dashboard/stats")
    assert _events(log_records, "dashboard_stats_fetch")
