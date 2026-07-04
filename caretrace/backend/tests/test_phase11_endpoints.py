"""Integration tests for Phase 11 read endpoints: runs list/detail + dashboard."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models import Run
from app.models.enums import Provider, RoutingDecision, RunStatus

_BREAKDOWN = {
    "base_score": 1.0,
    "failure_penalties": 0.0,
    "retry_penalties": 0.0,
    "severity_penalties": 0.0,
    "type_penalties": 0.0,
    "raw_score": 0.95,
    "final_score": 0.95,
}


def _make_run(*, confidence, decision, status, created_at, breakdown=None, note=None):
    return Run(
        transcript="transcript text",
        provider=Provider.openai,
        status=status,
        confidence=confidence,
        routing_decision=decision,
        routing_reason=f"reason {decision.value}",
        confidence_breakdown=breakdown,
        parsed_output=note,
        warnings_count=0,
        retry_count=0,
        created_at=created_at,
    )


@pytest.fixture
def seeded(db_session):
    base = datetime(2026, 7, 1, tzinfo=timezone.utc)
    runs = [
        _make_run(
            confidence=0.95,
            decision=RoutingDecision.auto_save,
            status=RunStatus.auto_saved,
            created_at=base + timedelta(minutes=1),
            breakdown=_BREAKDOWN,
            note={"observations": [{"text": "stable"}]},
        ),
        _make_run(
            confidence=0.90,
            decision=RoutingDecision.auto_save,
            status=RunStatus.auto_saved,
            created_at=base + timedelta(minutes=2),
        ),
        _make_run(
            confidence=0.70,
            decision=RoutingDecision.human_review,
            status=RunStatus.needs_review,
            created_at=base + timedelta(minutes=3),
        ),
        _make_run(
            confidence=0.30,
            decision=RoutingDecision.reject,
            status=RunStatus.rejected,
            created_at=base + timedelta(minutes=4),
        ),
    ]
    db_session.add_all(runs)
    db_session.commit()
    return [r.id for r in runs]


# --- list / filter / paginate -----------------------------------------------


def test_list_runs_returns_all_newest_first(client, seeded):
    body = client.get("/api/runs").json()
    assert body["total"] == 4
    assert len(body["items"]) == 4
    assert body["limit"] == 50 and body["offset"] == 0
    # newest first: the reject run (minute 4) leads
    assert body["items"][0]["routing_decision"] == "reject"


def test_filter_by_routing_decision(client, seeded):
    body = client.get("/api/runs", params={"routing_decision": "auto_save"}).json()
    assert body["total"] == 2
    assert all(item["routing_decision"] == "auto_save" for item in body["items"])


def test_filter_by_min_confidence(client, seeded):
    body = client.get("/api/runs", params={"min_confidence": 0.85}).json()
    assert body["total"] == 2
    assert all(item["confidence_score"] >= 0.85 for item in body["items"])


def test_filter_by_max_confidence(client, seeded):
    body = client.get("/api/runs", params={"max_confidence": 0.5}).json()
    assert body["total"] == 1
    assert body["items"][0]["confidence_score"] == 0.30


def test_pagination_limit_and_offset(client, seeded):
    page1 = client.get("/api/runs", params={"limit": 2, "offset": 0}).json()
    page2 = client.get("/api/runs", params={"limit": 2, "offset": 2}).json()
    assert page1["total"] == 4 and page2["total"] == 4
    assert len(page1["items"]) == 2 and len(page2["items"]) == 2
    ids1 = {i["id"] for i in page1["items"]}
    ids2 = {i["id"] for i in page2["items"]}
    assert ids1.isdisjoint(ids2)


def test_invalid_routing_decision_is_rejected(client, seeded):
    response = client.get("/api/runs", params={"routing_decision": "ACCEPTED"})
    assert response.status_code == 422


# --- detail / deep trace ----------------------------------------------------


def test_run_detail_existing_includes_nested_breakdown(client, seeded):
    run_id = str(seeded[0])
    response = client.get(f"/api/runs/{run_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == run_id
    assert body["confidence_score"] == 0.95
    assert body["confidence_breakdown"]["final_score"] == 0.95
    assert body["confidence_breakdown"]["raw_score"] == 0.95
    assert body["parsed_output"]["observations"][0]["text"] == "stable"
    assert body["routing_decision"] == "auto_save"


def test_run_detail_not_found(client, seeded):
    response = client.get(f"/api/runs/{uuid.uuid4()}")
    assert response.status_code == 404


# --- dashboard stats --------------------------------------------------------


def test_dashboard_stats_aggregates(client, seeded):
    body = client.get("/api/dashboard/stats").json()
    assert body["total_runs"] == 4
    assert body["accepted_runs"] == 2
    assert body["routed_to_human_runs"] == 1
    assert body["rejected_runs"] == 1
    assert body["average_confidence"] == pytest.approx(0.7125)


def test_dashboard_stats_empty_db(client):
    body = client.get("/api/dashboard/stats").json()
    assert body["total_runs"] == 0
    assert body["average_confidence"] == 0.0
