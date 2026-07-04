"""Integration tests for the /process and /reviews endpoints.

Uses the in-memory SQLite ``client`` fixture and a stubbed provider (via the
``get_pipeline`` dependency override) so no network or API keys are needed.
"""

import json
import uuid

from app.api.deps import get_pipeline
from app.main import app
from app.services.pipeline import ProcessingPipeline
from app.services.providers import ExtractionResult

CLEAN_NOTE = {
    "vitals": {"blood_pressure": {"systolic": 120, "diastolic": 80}, "spo2": {"value": 98}},
    "observations": [{"text": "stable"}],
}
CRITICAL_NOTE = {"vitals": {"spo2": {"value": 90}}, "observations": [{"text": "short of breath"}]}


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


def test_process_auto_save_persists_run(client):
    _use_provider(json.dumps(CLEAN_NOTE))
    response = client.post("/api/process", json={"transcript": "t", "provider": "openai"})
    assert response.status_code == 200
    body = response.json()
    assert body["routing_decision"] == "auto_save"
    assert body["status"] == "auto_saved"
    assert body["confidence"] == 1.0
    assert body["confidence_breakdown"] is not None
    assert body["routing_reason"]
    # nothing queued for review
    assert client.get("/api/reviews").json()["total"] == 0


def test_process_critical_routes_to_review_then_approve(client):
    _use_provider(json.dumps(CRITICAL_NOTE))
    response = client.post("/api/process", json={"transcript": "t", "provider": "openai"})
    assert response.status_code == 200
    body = response.json()
    assert body["routing_decision"] == "human_review"
    assert body["status"] == "needs_review"

    listing = client.get("/api/reviews").json()
    assert listing["total"] == 1
    assert len(listing["items"]) == 1
    item = listing["items"][0]
    assert item["issues"]  # the critical SpO2 issue is present
    assert item["issues"][0]["rule_id"] == "ERR_SPO2_LOW"

    action = client.post(
        f"/api/reviews/{item['id']}/action", json={"action": "approve"}
    )
    assert action.status_code == 200
    assert action.json()["status"] == "approved"
    assert action.json()["run_status"] == "reviewed"

    # queue is now empty
    assert client.get("/api/reviews").json()["total"] == 0


def test_process_invalid_json_is_rejected_and_logged(client):
    _use_provider("this is not valid json")
    response = client.post("/api/process", json={"transcript": "t", "provider": "openai"})
    assert response.status_code == 200
    body = response.json()
    assert body["routing_decision"] == "reject"
    assert body["status"] == "failed"  # extraction/parsing failed
    assert body["note"] is None
    # not routed to review
    assert client.get("/api/reviews").json()["total"] == 0


def test_review_action_reject_transitions_state(client):
    _use_provider(json.dumps(CRITICAL_NOTE))
    client.post("/api/process", json={"transcript": "t", "provider": "openai"})
    item = client.get("/api/reviews").json()["items"][0]

    action = client.post(f"/api/reviews/{item['id']}/action", json={"action": "reject"})
    assert action.status_code == 200
    assert action.json()["status"] == "rejected"
    assert action.json()["run_status"] == "rejected"


def test_review_action_unknown_id_returns_404(client):
    response = client.post(
        f"/api/reviews/{uuid.uuid4()}/action", json={"action": "approve"}
    )
    assert response.status_code == 404
