"""Phase 21: AI Reviewer Assistant — service heuristics + /analyze endpoint.

Covers the advisory contract: deterministic risk detection (keywords, vital
ranges, medication diffs), the synthetic confidence, and the endpoint's 404/422
error handling. The assistant is advisory only — no test expects it to mutate a
run.
"""

from app.models import Run
from app.models.enums import Provider, RoutingDecision, RunStatus
from app.services.assistant import analyze_edit

# --- pure service heuristics -------------------------------------------------


def test_clean_note_is_stable_with_high_confidence():
    note = {"note_summary": "Routine check; patient comfortable.", "medications": []}
    result = analyze_edit(original=note, edited=note)
    assert result.clinical_risks == []
    assert "No additional clinical concerns" in result.suggestion
    # No edits, no risks → confidence stays at the ceiling.
    assert result.confidence_score == 0.95


def test_missing_medication_dose_is_flagged():
    note = {"medications": [{"name": "Amlodipine"}]}
    result = analyze_edit(original=note, edited=note)
    assert any("Amlodipine" in r and "dose" in r for r in result.clinical_risks)


def test_out_of_range_spo2_is_flagged():
    note = {"vitals": {"spo2": {"value": 90}}}
    result = analyze_edit(original=note, edited=note)
    assert any("SpO" in r for r in result.clinical_risks)


def test_high_alert_keyword_is_flagged_once():
    note = {"observations": [{"text": "Patient reports chest pain and chest pain again"}]}
    result = analyze_edit(original=note, edited=note)
    chest = [r for r in result.clinical_risks if "chest pain" in r]
    assert len(chest) == 1  # deduplicated


def test_dose_change_diff_is_flagged():
    original = {"medications": [{"name": "Amlodipine", "dose": "10mg"}]}
    edited = {"medications": [{"name": "Amlodipine", "dose": "5mg"}]}
    result = analyze_edit(original=original, edited=edited)
    assert any("10mg" in r and "5mg" in r for r in result.clinical_risks)


def test_removed_medication_diff_is_flagged():
    original = {"medications": [{"name": "Warfarin", "dose": "2mg"}]}
    edited = {"medications": []}
    result = analyze_edit(original=original, edited=edited)
    assert any("Warfarin" in r and "removed" in r for r in result.clinical_risks)


def test_confidence_drops_with_edit_magnitude_and_risks():
    original = {"note_summary": "a", "medications": [{"name": "X", "dose": "1mg"}]}
    edited = {"note_summary": "b", "medications": [{"name": "X"}]}  # changed + dose removed
    result = analyze_edit(original=original, edited=edited)
    assert result.clinical_risks  # a risk fired
    assert result.confidence_score < 0.95
    assert 0.4 <= result.confidence_score <= 0.97


# --- endpoint integration ----------------------------------------------------


def _needs_review_run(db_session) -> Run:
    run = Run(
        transcript="t",
        provider=Provider.openai,
        status=RunStatus.needs_review,
        confidence=0.7,
        routing_decision=RoutingDecision.human_review,
        routing_reason="low confidence",
        parsed_output={"medications": [{"name": "Amlodipine", "dose": "10mg"}]},
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run


def test_analyze_endpoint_returns_contract(client, db_session):
    run = _needs_review_run(db_session)
    body = {"edited_output": {"medications": [{"name": "Amlodipine", "dose": "5mg"}]}}
    response = client.post(f"/api/runs/{run.id}/analyze", json=body)
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"clinical_risks", "suggestion", "confidence_score"}
    assert isinstance(data["clinical_risks"], list)
    # The dose change is surfaced as a diff-based risk.
    assert any("5mg" in r for r in data["clinical_risks"])
    assert 0.0 <= data["confidence_score"] <= 1.0


def test_analyze_endpoint_does_not_mutate_run(client, db_session):
    run = _needs_review_run(db_session)
    client.post(
        f"/api/runs/{run.id}/analyze",
        json={"edited_output": {"medications": []}},
    )
    detail = client.get(f"/api/runs/{run.id}").json()
    # Advisory only: status and stored output are unchanged.
    assert detail["status"] == "needs_review"
    assert detail["final_output"] is None


def test_analyze_unknown_run_is_404(client):
    import uuid

    response = client.post(
        f"/api/runs/{uuid.uuid4()}/analyze",
        json={"edited_output": {}},
    )
    assert response.status_code == 404


def test_analyze_non_object_edited_output_is_422(client, db_session):
    run = _needs_review_run(db_session)
    response = client.post(
        f"/api/runs/{run.id}/analyze",
        json={"edited_output": [1, 2, 3]},
    )
    assert response.status_code == 422


def test_analyze_missing_edited_output_is_422(client, db_session):
    run = _needs_review_run(db_session)
    response = client.post(f"/api/runs/{run.id}/analyze", json={})
    assert response.status_code == 422
