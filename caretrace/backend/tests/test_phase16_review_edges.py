"""Phase 16: review-workflow edge cases + metric-alignment regressions.

Covers operator-correctness guarantees that the earlier phases left implicit:
  * a terminal review decision is immutable (409, not a silent re-apply),
  * malformed ``edited_output`` payloads are rejected at the contract boundary,
  * the time-series endpoint fills empty days with zeros, and
  * the donut (stats) and trend (timeseries) never drift out of alignment.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone

from app.api.deps import get_pipeline
from app.main import app
from app.models import Run
from app.models.enums import Provider, RoutingDecision, RunStatus
from app.services.pipeline import ProcessingPipeline
from app.services.providers import ExtractionResult

CRITICAL_NOTE = {
    "vitals": {"spo2": {"value": 90}},
    "observations": [{"text": "short of breath"}],
}


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
            estimated_cost=0.0002,
            retryable_error=False,
            error=None,
        )


def _use_provider(content: str) -> None:
    app.dependency_overrides[get_pipeline] = lambda: ProcessingPipeline(
        provider_factory=lambda name, **kw: _StubProvider(content)
    )


def _queue_one_review(client) -> str:
    """Process a critical transcript so exactly one pending review exists."""
    _use_provider(json.dumps(CRITICAL_NOTE))
    client.post("/api/process", json={"transcript": "t", "provider": "openai"})
    return client.get("/api/reviews").json()["items"][0]["id"]


# --- terminal decisions are immutable ---------------------------------------


def test_reject_after_approve_returns_409(client):
    review_id = _queue_one_review(client)
    assert (
        client.post(f"/api/reviews/{review_id}/action", json={"action": "approve"}).status_code
        == 200
    )

    conflict = client.post(f"/api/reviews/{review_id}/action", json={"action": "reject"})
    assert conflict.status_code == 409
    assert "already approved" in conflict.json()["detail"]

    # The already-recorded decision is unchanged (queue stays empty).
    assert client.get("/api/reviews").json()["total"] == 0


def test_approve_after_reject_returns_409(client):
    review_id = _queue_one_review(client)
    assert (
        client.post(f"/api/reviews/{review_id}/action", json={"action": "reject"}).status_code
        == 200
    )

    conflict = client.post(f"/api/reviews/{review_id}/action", json={"action": "approve"})
    assert conflict.status_code == 409
    assert "already rejected" in conflict.json()["detail"]


def test_action_on_unknown_review_still_404_not_409(client):
    # Absent review is distinct from a decided one: 404, not a conflict.
    response = client.post(
        f"/api/reviews/{uuid.uuid4()}/action", json={"action": "approve"}
    )
    assert response.status_code == 404


# --- invalid edited_output at the contract boundary --------------------------


def test_edited_output_wrong_type_is_422(client):
    review_id = _queue_one_review(client)
    # systolic must be an int; a string violates the ClinicalNote contract.
    bad = {
        "action": "approve",
        "edited_output": {"vitals": {"blood_pressure": {"systolic": "high", "diastolic": 80}}},
    }
    assert client.post(f"/api/reviews/{review_id}/action", json=bad).status_code == 422


def test_edited_output_non_object_is_422(client):
    review_id = _queue_one_review(client)
    bad = {"action": "approve", "edited_output": [1, 2, 3]}
    assert client.post(f"/api/reviews/{review_id}/action", json=bad).status_code == 422


def test_unknown_top_level_field_is_forbidden_422(client):
    review_id = _queue_one_review(client)
    bad = {"action": "approve", "unexpected": True}
    assert client.post(f"/api/reviews/{review_id}/action", json=bad).status_code == 422


def test_invalid_action_value_is_422(client):
    review_id = _queue_one_review(client)
    bad = {"action": "escalate"}
    assert client.post(f"/api/reviews/{review_id}/action", json=bad).status_code == 422


# --- timeseries continuity ---------------------------------------------------


def _seed(db_session, *, decision, status, created_at, confidence):
    db_session.add(
        Run(
            transcript="t",
            provider=Provider.openai,
            status=status,
            confidence=confidence,
            routing_decision=decision,
            routing_reason="r",
            created_at=created_at,
        )
    )
    db_session.commit()


def test_timeseries_fills_gaps_between_populated_days(client, db_session):
    today = datetime.now(timezone.utc)
    # Runs only today and 6 days ago; the 5 days in between must be present + zero.
    _seed(db_session, decision=RoutingDecision.auto_save, status=RunStatus.auto_saved,
          created_at=today, confidence=0.95)
    _seed(db_session, decision=RoutingDecision.reject, status=RunStatus.rejected,
          created_at=today - timedelta(days=6), confidence=0.30)

    points = client.get("/api/dashboard/stats/timeseries", params={"days": 7}).json()["points"]
    assert len(points) == 7
    # Buckets are contiguous, ascending, one calendar day apart.
    dates = [datetime.fromisoformat(p["bucket"]).date() for p in points]
    assert all((dates[i + 1] - dates[i]).days == 1 for i in range(len(dates) - 1))
    # Interior days have no runs but are still emitted with zeros.
    interior = points[1:-1]
    assert all(p["total"] == 0 for p in interior)
    assert all(p["auto_save"] == 0 and p["human_review"] == 0 and p["reject"] == 0 for p in interior)


def test_timeseries_empty_db_is_all_zero_but_continuous(client):
    points = client.get("/api/dashboard/stats/timeseries", params={"days": 14}).json()["points"]
    assert len(points) == 14
    assert sum(p["total"] for p in points) == 0


# --- donut/trend alignment regression ---------------------------------------


def test_stats_and_timeseries_agree_on_routing_grouping(client, db_session):
    """The donut reads /stats; the trend reads /timeseries. Both group runs by
    routing decision, so per-decision totals must match for runs inside the
    window. This guards against the two surfaces drifting apart."""
    today = datetime.now(timezone.utc)
    seeds = [
        (RoutingDecision.auto_save, RunStatus.auto_saved, 0.95),
        (RoutingDecision.auto_save, RunStatus.auto_saved, 0.90),
        (RoutingDecision.human_review, RunStatus.needs_review, 0.70),
        (RoutingDecision.reject, RunStatus.rejected, 0.30),
    ]
    for decision, status, confidence in seeds:
        _seed(db_session, decision=decision, status=status, created_at=today, confidence=confidence)

    stats = client.get("/api/dashboard/stats").json()
    points = client.get("/api/dashboard/stats/timeseries", params={"days": 14}).json()["points"]

    trend = {"auto_save": 0, "human_review": 0, "reject": 0}
    for point in points:
        for key in trend:
            trend[key] += point[key]

    assert trend["auto_save"] == stats["accepted_runs"] == 2
    assert trend["human_review"] == stats["routed_to_human_runs"] == 1
    assert trend["reject"] == stats["rejected_runs"] == 1
