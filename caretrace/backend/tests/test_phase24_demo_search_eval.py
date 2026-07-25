"""Phase 24: demo/simulator mode, global search, and evaluation export."""

from __future__ import annotations

import csv
import io
import json

from app.core.config import Settings
from app.models import Run
from app.models.enums import Provider, ReviewStatus, RoutingDecision, RunStatus
from app.models.review_item import ReviewItem
from app.schemas.clinical_note import ClinicalNote
from app.services.providers import SimulatedProvider, get_provider
from app.services.providers import factory

GOOD_TRANSCRIPT = (
    "Patient Anna Keller reported mild dizziness in the morning. Blood pressure "
    "was 138/86 mmHg, heart rate 78 bpm, temperature 36.8°C, and SpO2 97%. "
    "Nurse administered prescribed Metformin 500mg orally after breakfast."
)


# --- simulated provider ------------------------------------------------------


def test_simulated_provider_extracts_schema_valid_note():
    result = SimulatedProvider(model="simulated").extract(GOOD_TRANSCRIPT)
    assert result.succeeded
    assert result.estimated_cost == 0.0

    note = ClinicalNote.model_validate(json.loads(result.content))
    assert note.patient and note.patient.name == "Anna Keller"
    assert note.vitals and note.vitals.blood_pressure.systolic == 138
    assert note.vitals.heart_rate.value == 78
    assert note.vitals.spo2.value == 97
    assert note.medications[0].name == "Metformin"
    assert note.medications[0].dose == "500mg"
    assert any("dizziness" in s.text for s in note.symptoms)


def test_simulated_provider_is_deterministic():
    first = SimulatedProvider(model="simulated").extract(GOOD_TRANSCRIPT)
    second = SimulatedProvider(model="simulated").extract(GOOD_TRANSCRIPT)
    assert first.content == second.content


# --- factory demo-safe fallbacks ---------------------------------------------


def test_factory_simulates_when_demo_mode_enabled(monkeypatch):
    monkeypatch.setattr(
        factory, "get_settings", lambda: Settings(demo_mode=True, _env_file=None)
    )
    assert isinstance(get_provider("openai"), SimulatedProvider)
    assert isinstance(get_provider("ollama"), SimulatedProvider)


def test_factory_simulates_when_openai_key_missing(monkeypatch):
    monkeypatch.setattr(
        factory, "get_settings", lambda: Settings(openai_api_key=None, _env_file=None)
    )
    assert isinstance(get_provider("openai"), SimulatedProvider)


def test_factory_simulates_when_ollama_unreachable(monkeypatch):
    monkeypatch.setattr(factory, "_ollama_available", lambda settings: False)
    assert isinstance(get_provider("ollama"), SimulatedProvider)


def test_process_endpoint_works_end_to_end_in_demo_mode(client, monkeypatch):
    """The full pipeline (validation, confidence, routing) runs on simulated
    extraction — a demo without credentials must still produce real traces."""
    monkeypatch.setattr(
        factory, "get_settings", lambda: Settings(demo_mode=True, _env_file=None)
    )
    response = client.post(
        "/api/process", json={"transcript": GOOD_TRANSCRIPT, "provider": "openai"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "auto_saved"
    assert body["confidence"] is not None
    assert body["note"]["patient"]["name"] == "Anna Keller"


def test_health_reports_demo_mode_flag(client):
    body = client.get("/api/health").json()
    assert isinstance(body["demo_mode"], bool)


# --- search -------------------------------------------------------------------


def _run(**kwargs) -> Run:
    defaults = dict(
        transcript="Routine note for Anna Keller; vitals stable.",
        provider=Provider.openai,
        status=RunStatus.auto_saved,
        confidence=0.95,
        routing_decision=RoutingDecision.auto_save,
        routing_reason="No validation issues; saved automatically.",
    )
    defaults.update(kwargs)
    return Run(**defaults)


def test_search_matches_transcript_and_flags_pending_review(client, db_session):
    match = _run(
        transcript="Evening note: patient Jonas Wolf, Amlodipine given, dose unclear.",
        status=RunStatus.needs_review,
        routing_decision=RoutingDecision.human_review,
        confidence=0.66,
    )
    match.review_items.append(ReviewItem(status=ReviewStatus.pending))
    other = _run()
    db_session.add_all([match, other])
    db_session.commit()

    body = client.get("/api/search", params={"q": "Amlodipine"}).json()
    assert body["query"] == "Amlodipine"
    assert len(body["results"]) == 1
    result = body["results"][0]
    assert result["run_id"] == str(match.id)
    assert result["pending_review"] is True
    assert "Amlodipine" in result["snippet"]


def test_search_matches_run_id_prefix(client, db_session):
    run = _run()
    db_session.add(run)
    db_session.commit()

    prefix = str(run.id)[:8]
    body = client.get("/api/search", params={"q": prefix}).json()
    assert any(r["run_id"] == str(run.id) for r in body["results"])


def test_search_rejects_too_short_query(client):
    assert client.get("/api/search", params={"q": "a"}).status_code == 422


# --- evaluation ---------------------------------------------------------------


def _seed_eval_runs(db_session) -> None:
    db_session.add_all(
        [
            _run(latency_ms=800, cost=0.0002),
            _run(latency_ms=900, cost=0.0002, retry_count=1),
            _run(
                provider=Provider.ollama,
                status=RunStatus.needs_review,
                routing_decision=RoutingDecision.human_review,
                confidence=0.7,
                latency_ms=1500,
                cost=0.0,
            ),
            _run(
                status=RunStatus.failed,
                routing_decision=None,
                confidence=None,
                latency_ms=None,
                cost=0.0,
            ),
        ]
    )
    db_session.commit()


def test_evaluation_summary_matches_contract(client, db_session):
    _seed_eval_runs(db_session)

    body = client.get("/api/evaluation").json()
    assert body["totals"]["runs"] == 4
    assert body["totals"]["auto_saved"] == 2
    assert body["totals"]["needs_review"] == 1
    assert body["totals"]["failed"] == 1

    by_provider = {row["provider"]: row for row in body["by_provider"]}
    openai = by_provider["openai"]
    assert openai["runs"] == 3
    assert openai["auto_save_rate"] == round(2 / 3, 4)
    assert openai["retry_rate"] == round(1 / 3, 4)
    assert by_provider["ollama"]["runs"] == 1


def test_evaluation_export_json_is_downloadable(client, db_session):
    _seed_eval_runs(db_session)

    response = client.get("/api/evaluation/export", params={"format": "json"})
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    payload = response.json()
    assert payload["summary"]["totals"]["runs"] == 4
    assert len(payload["runs"]) == 4
    # Metric rows only — no clinical text leaves via the export.
    assert "transcript" not in payload["runs"][0]


def test_evaluation_export_csv_has_one_row_per_run(client, db_session):
    _seed_eval_runs(db_session)

    response = client.get("/api/evaluation/export", params={"format": "csv"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 4
    assert set(rows[0].keys()) >= {"run_id", "provider", "status", "confidence"}


# --- reviewed_at on run detail -------------------------------------------------


def test_run_detail_exposes_reviewed_at_for_decided_runs(client, db_session):
    run = _run(status=RunStatus.reviewed, routing_decision=RoutingDecision.human_review)
    run.review_items.append(
        ReviewItem(status=ReviewStatus.approved, reviewer_notes="Verified.")
    )
    pending = _run(
        status=RunStatus.needs_review, routing_decision=RoutingDecision.human_review
    )
    pending.review_items.append(ReviewItem(status=ReviewStatus.pending))
    db_session.add_all([run, pending])
    db_session.commit()

    decided = client.get(f"/api/runs/{run.id}").json()
    assert decided["reviewed_at"] is not None

    undecided = client.get(f"/api/runs/{pending.id}").json()
    assert undecided["reviewed_at"] is None
