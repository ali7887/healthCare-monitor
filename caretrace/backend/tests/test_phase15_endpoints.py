"""Tests for Phase 15: pending_review_id on run detail + timeseries endpoint."""

from datetime import datetime, timezone

from app.models import Run
from app.models.enums import Provider, ReviewStatus, RoutingDecision, RunStatus
from app.models.review_item import ReviewItem


def _run(**kwargs) -> Run:
    defaults = dict(
        transcript="t",
        provider=Provider.openai,
        status=RunStatus.auto_saved,
        confidence=0.95,
        routing_decision=RoutingDecision.auto_save,
    )
    defaults.update(kwargs)
    return Run(**defaults)


def test_run_detail_exposes_pending_review_id(client, db_session):
    run = _run(status=RunStatus.needs_review, routing_decision=RoutingDecision.human_review, confidence=0.7)
    review = ReviewItem(run=run, status=ReviewStatus.pending)
    db_session.add(run)
    db_session.add(review)
    db_session.commit()

    body = client.get(f"/api/runs/{run.id}").json()
    assert body["pending_review_id"] == str(review.id)


def test_run_detail_pending_review_id_null_for_auto_saved(client, db_session):
    run = _run()
    db_session.add(run)
    db_session.commit()

    body = client.get(f"/api/runs/{run.id}").json()
    assert body["pending_review_id"] is None


def test_timeseries_returns_continuous_buckets(client, db_session):
    db_session.add_all(
        [
            _run(),  # auto_save (today)
            _run(),  # auto_save (today)
            _run(status=RunStatus.rejected, routing_decision=RoutingDecision.reject, confidence=0.3),
        ]
    )
    db_session.commit()

    body = client.get("/api/dashboard/stats/timeseries", params={"days": 7}).json()
    assert body["bucket"] == "day"
    assert len(body["points"]) == 7

    today = datetime.now(timezone.utc).date().isoformat()
    last = body["points"][-1]
    assert last["bucket"] == today
    assert last["auto_save"] == 2
    assert last["reject"] == 1
    assert last["total"] == 3


def test_timeseries_rejects_bad_bucket(client):
    assert client.get("/api/dashboard/stats/timeseries", params={"bucket": "week"}).status_code == 422
