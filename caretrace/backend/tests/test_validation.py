"""Tests for the deterministic validation engine."""

from app.schemas.clinical_note import ClinicalNote
from app.schemas.validation import ValidationIssue
from app.services.validation import (
    RULE_CATALOG,
    parse_and_validate,
    validate_note,
)


def _rule_ids(issues: list[ValidationIssue]) -> set[str]:
    return {issue.rule_id for issue in issues}


# --- Normal / boundary cases ------------------------------------------------


def test_normal_note_produces_no_issues():
    note = ClinicalNote.model_validate(
        {
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
    )
    assert validate_note(note) == []


def test_thresholds_are_exclusive_at_boundary():
    # Exactly on the boundary is NOT flagged (strict > / <).
    note = ClinicalNote.model_validate(
        {
            "vitals": {
                "blood_pressure": {"systolic": 140, "diastolic": 90},
                "heart_rate": {"value": 100},
                "temperature": {"value": 38.0},
                "spo2": {"value": 95},
            },
            "observations": [{"text": "stable"}],
        }
    )
    assert validate_note(note) == []


# --- Out-of-range vitals ----------------------------------------------------


def test_high_bp_produces_clinical_issue_with_rule_id():
    note = ClinicalNote.model_validate(
        {
            "vitals": {"blood_pressure": {"systolic": 185, "diastolic": 105}},
            "observations": [{"text": "dizziness reported"}],
        }
    )
    issues = validate_note(note)
    ids = _rule_ids(issues)
    assert "ERR_BP_SYSTOLIC_HIGH" in ids
    assert "ERR_BP_DIASTOLIC_HIGH" in ids

    systolic_issue = next(i for i in issues if i.rule_id == "ERR_BP_SYSTOLIC_HIGH")
    assert systolic_issue.issue_type == "clinical"
    assert systolic_issue.severity == "warning"
    assert systolic_issue.field_path == "vitals.blood_pressure.systolic"


def test_low_vitals_are_flagged():
    note = ClinicalNote.model_validate(
        {
            "vitals": {
                "blood_pressure": {"systolic": 85, "diastolic": 55},
                "heart_rate": {"value": 45},
                "temperature": {"value": 35.2},
            },
            "observations": [{"text": "lethargic"}],
        }
    )
    ids = _rule_ids(validate_note(note))
    assert {"ERR_BP_SYSTOLIC_LOW", "ERR_BP_DIASTOLIC_LOW", "ERR_HR_LOW", "ERR_TEMP_LOW"} <= ids


def test_low_spo2_is_critical():
    note = ClinicalNote.model_validate(
        {"vitals": {"spo2": {"value": 92}}, "observations": [{"text": "short of breath"}]}
    )
    issues = validate_note(note)
    assert len(issues) == 1
    assert issues[0].rule_id == "ERR_SPO2_LOW"
    assert issues[0].severity == "critical"
    assert issues[0].issue_type == "clinical"


def test_high_temp_and_hr_flagged():
    note = ClinicalNote.model_validate(
        {
            "vitals": {"temperature": {"value": 39.1}, "heart_rate": {"value": 120}},
            "observations": [{"text": "febrile"}],
        }
    )
    ids = _rule_ids(validate_note(note))
    assert ids == {"ERR_TEMP_HIGH", "ERR_HR_HIGH"}


# --- Completeness -----------------------------------------------------------


def test_missing_medication_dose_produces_completeness_warning():
    note = ClinicalNote.model_validate(
        {
            "medications": [{"name": "Paracetamol"}, {"name": "Metformin", "dose": "500mg"}],
            "observations": [{"text": "nausea after lunch"}],
        }
    )
    issues = validate_note(note)
    dose_issues = [i for i in issues if i.rule_id == "ERR_MED_DOSE_MISSING"]
    assert len(dose_issues) == 1
    assert dose_issues[0].issue_type == "completeness"
    assert dose_issues[0].severity == "warning"
    assert dose_issues[0].field_path == "medications[0].dose"


def test_empty_dose_string_is_flagged():
    note = ClinicalNote.model_validate({"medications": [{"name": "Aspirin", "dose": "  "}]})
    ids = _rule_ids(validate_note(note))
    assert "ERR_MED_DOSE_MISSING" in ids


def test_completely_empty_note_is_flagged():
    note = ClinicalNote.model_validate({"patient": {"name": "John Meyer"}})
    ids = _rule_ids(validate_note(note))
    assert "ERR_NOTE_EMPTY" in ids


# --- Schema / structure safety ---------------------------------------------


def test_malformed_json_maps_to_schema_issue():
    note, issues = parse_and_validate("this is not json")
    assert note is None
    assert len(issues) == 1
    assert issues[0].rule_id == "ERR_SCHEMA_INVALID_JSON"
    assert issues[0].issue_type == "schema"
    assert issues[0].severity == "critical"


def test_non_object_json_maps_to_schema_issue():
    note, issues = parse_and_validate("[1, 2, 3]")
    assert note is None
    assert issues[0].rule_id == "ERR_SCHEMA_NOT_OBJECT"


def test_schema_violation_maps_to_schema_issue():
    # Medication without a required name is a schema error, not a completeness one.
    note, issues = parse_and_validate({"medications": [{"dose": "500mg"}]})
    assert note is None
    assert issues
    assert all(i.issue_type == "schema" for i in issues)
    assert any(i.rule_id == "ERR_SCHEMA_INVALID" for i in issues)


def test_parse_and_validate_success_runs_clinical_rules():
    note, issues = parse_and_validate(
        '{"vitals": {"spo2": {"value": 90}}, "observations": [{"text": "x"}]}'
    )
    assert isinstance(note, ClinicalNote)
    assert _rule_ids(issues) == {"ERR_SPO2_LOW"}


# --- Registry integrity -----------------------------------------------------


def test_every_rule_id_is_registered():
    # All rule ids referenced by the tests exist in the catalog.
    for rule_id in ("ERR_BP_SYSTOLIC_HIGH", "ERR_SPO2_LOW", "ERR_MED_DOSE_MISSING"):
        assert rule_id in RULE_CATALOG
