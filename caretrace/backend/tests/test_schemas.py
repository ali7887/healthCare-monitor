"""Tiny schema serialization tests (no runtime dependencies beyond imports)."""

from datetime import datetime, timezone
from uuid import uuid4

from app.schemas import (
    ClinicalNote,
    ProcessRequest,
    ProcessResponse,
    ValidationIssue,
)


def test_clinical_note_roundtrip_and_defaults():
    note = ClinicalNote.model_validate(
        {
            "patient": {"name": "Anna Keller"},
            "vitals": {
                "blood_pressure": {"systolic": 138, "diastolic": 86, "unit": "mmHg"}
            },
            "medications": [{"name": "Metformin", "dose": "500mg", "route": "oral"}],
            "symptoms": [{"text": "mild dizziness"}],
            "observations": [{"text": "resting comfortably"}],
            "actions": [{"text": "advised hydration and routine monitoring"}],
            "follow_up": [],
        }
    )
    dumped = note.model_dump(mode="json")

    # numeric values are preserved as integers (not coerced to float)
    assert dumped["vitals"]["blood_pressure"]["systolic"] == 138
    # missing collections default to empty lists; missing vitals default to None
    assert dumped["observations"][0]["text"] == "resting comfortably"
    assert dumped["vitals"]["heart_rate"] is None
    # round-trips back into an equal model
    assert ClinicalNote.model_validate(dumped) == note


def test_validation_issue_structure():
    issue = ValidationIssue(
        severity="critical",
        issue_type="clinical",
        field_path="vitals.blood_pressure.systolic",
        message="Systolic BP is outside the plausible range.",
        rule_id="vitals.bp.systolic.range",
    )
    assert issue.model_dump(mode="json")["rule_id"] == "vitals.bp.systolic.range"


def test_process_dtos_align_with_api_contract():
    req = ProcessRequest(transcript="text", provider="openai")
    assert req.model is None

    resp = ProcessResponse(
        run_id=uuid4(),
        status="auto_saved",
        provider="openai",
        prompt_version="clinical-extraction-v1",
        note=None,
        confidence=0.94,
        latency_ms=1820,
        estimated_cost_usd=0.0004,
        created_at=datetime.now(timezone.utc),
    )
    payload = resp.model_dump(mode="json")
    assert payload["retry_used"] is False
    assert payload["issues"] == []
    assert "estimated_cost_usd" in payload and "created_at" in payload
