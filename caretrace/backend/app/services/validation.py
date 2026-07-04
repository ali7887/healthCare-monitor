"""Deterministic clinical validation engine.

Pure Python, no LLM calls, no I/O. Takes a parsed ``ClinicalNote`` and returns
a list of ``ValidationIssue`` objects describing schema, clinical, and
completeness problems. A stable ``RULE_CATALOG`` maps each ``rule_id`` to its
issue type, severity, and message template so findings are auditable and the
evaluation dashboard can key metrics off rule ids.

Thresholds implement the Phase 5 (clinically-abnormal) bounds. Note this is
intentionally narrower than the implausible-value bounds in docs/AI_PIPELINE.md;
that document is flagged for reconciliation (it is outside this phase's allowed
files).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from pydantic import ValidationError

from app.schemas.clinical_note import ClinicalNote, Vitals
from app.schemas.validation import IssueTypeLiteral, SeverityLiteral, ValidationIssue


@dataclass(frozen=True)
class RuleSpec:
    """Static metadata for a single validation rule."""

    issue_type: IssueTypeLiteral
    severity: SeverityLiteral
    message: str  # str.format template


# Stable registry: rule_id -> metadata. Message templates use named fields
# filled in at issue-construction time.
RULE_CATALOG: dict[str, RuleSpec] = {
    # --- Blood pressure ---
    "ERR_BP_SYSTOLIC_HIGH": RuleSpec(
        "clinical", "warning",
        "Systolic blood pressure {value} mmHg is above the expected range (> 140).",
    ),
    "ERR_BP_SYSTOLIC_LOW": RuleSpec(
        "clinical", "warning",
        "Systolic blood pressure {value} mmHg is below the expected range (< 90).",
    ),
    "ERR_BP_DIASTOLIC_HIGH": RuleSpec(
        "clinical", "warning",
        "Diastolic blood pressure {value} mmHg is above the expected range (> 90).",
    ),
    "ERR_BP_DIASTOLIC_LOW": RuleSpec(
        "clinical", "warning",
        "Diastolic blood pressure {value} mmHg is below the expected range (< 60).",
    ),
    # --- Heart rate ---
    "ERR_HR_HIGH": RuleSpec(
        "clinical", "warning",
        "Heart rate {value} bpm is above the expected range (> 100).",
    ),
    "ERR_HR_LOW": RuleSpec(
        "clinical", "warning",
        "Heart rate {value} bpm is below the expected range (< 60).",
    ),
    # --- Temperature ---
    "ERR_TEMP_HIGH": RuleSpec(
        "clinical", "warning",
        "Temperature {value}°C is above the expected range (> 38.0).",
    ),
    "ERR_TEMP_LOW": RuleSpec(
        "clinical", "warning",
        "Temperature {value}°C is below the expected range (< 36.0).",
    ),
    # --- SpO2 ---
    "ERR_SPO2_LOW": RuleSpec(
        "clinical", "critical",
        "Oxygen saturation {value}% is below the safe threshold (< 95).",
    ),
    # --- Completeness ---
    "ERR_MED_DOSE_MISSING": RuleSpec(
        "completeness", "warning",
        "Medication '{name}' is documented without a dose.",
    ),
    "ERR_NOTE_EMPTY": RuleSpec(
        "completeness", "warning",
        "The clinical note contains no documented clinical content.",
    ),
    # --- Schema / structure ---
    "ERR_SCHEMA_INVALID_JSON": RuleSpec(
        "schema", "critical",
        "Extracted output is not valid JSON: {detail}",
    ),
    "ERR_SCHEMA_NOT_OBJECT": RuleSpec(
        "schema", "critical",
        "Extracted output is not a JSON object.",
    ),
    "ERR_SCHEMA_INVALID": RuleSpec(
        "schema", "critical",
        "Schema validation failed: {detail}",
    ),
}


def _issue(rule_id: str, *, field_path: str | None = None, **fmt: object) -> ValidationIssue:
    """Build a ValidationIssue from the registry, formatting its message."""
    spec = RULE_CATALOG[rule_id]
    message = spec.message.format(**fmt) if fmt else spec.message
    return ValidationIssue(
        severity=spec.severity,
        issue_type=spec.issue_type,
        field_path=field_path,
        message=message,
        rule_id=rule_id,
    )


# --- Vital sign rules -------------------------------------------------------


def _validate_vitals(vitals: Vitals | None) -> list[ValidationIssue]:
    if vitals is None:
        return []

    issues: list[ValidationIssue] = []

    bp = vitals.blood_pressure
    if bp is not None:
        if bp.systolic is not None:
            if bp.systolic > 140:
                issues.append(_issue("ERR_BP_SYSTOLIC_HIGH", field_path="vitals.blood_pressure.systolic", value=bp.systolic))
            elif bp.systolic < 90:
                issues.append(_issue("ERR_BP_SYSTOLIC_LOW", field_path="vitals.blood_pressure.systolic", value=bp.systolic))
        if bp.diastolic is not None:
            if bp.diastolic > 90:
                issues.append(_issue("ERR_BP_DIASTOLIC_HIGH", field_path="vitals.blood_pressure.diastolic", value=bp.diastolic))
            elif bp.diastolic < 60:
                issues.append(_issue("ERR_BP_DIASTOLIC_LOW", field_path="vitals.blood_pressure.diastolic", value=bp.diastolic))

    hr = vitals.heart_rate
    if hr is not None and hr.value is not None:
        if hr.value > 100:
            issues.append(_issue("ERR_HR_HIGH", field_path="vitals.heart_rate.value", value=hr.value))
        elif hr.value < 60:
            issues.append(_issue("ERR_HR_LOW", field_path="vitals.heart_rate.value", value=hr.value))

    temp = vitals.temperature
    if temp is not None and temp.value is not None:
        if temp.value > 38.0:
            issues.append(_issue("ERR_TEMP_HIGH", field_path="vitals.temperature.value", value=temp.value))
        elif temp.value < 36.0:
            issues.append(_issue("ERR_TEMP_LOW", field_path="vitals.temperature.value", value=temp.value))

    spo2 = vitals.spo2
    if spo2 is not None and spo2.value is not None and spo2.value < 95:
        issues.append(_issue("ERR_SPO2_LOW", field_path="vitals.spo2.value", value=spo2.value))

    return issues


# --- Completeness / integrity rules -----------------------------------------


def _validate_medications(note: ClinicalNote) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for index, med in enumerate(note.medications):
        if med.dose is None or not med.dose.strip():
            issues.append(
                _issue(
                    "ERR_MED_DOSE_MISSING",
                    field_path=f"medications[{index}].dose",
                    name=med.name,
                )
            )
    return issues


def _vitals_has_value(vitals: Vitals | None) -> bool:
    if vitals is None:
        return False
    bp = vitals.blood_pressure
    if bp is not None and (bp.systolic is not None or bp.diastolic is not None):
        return True
    for reading in (vitals.heart_rate, vitals.temperature, vitals.spo2):
        if reading is not None and reading.value is not None:
            return True
    return False


def _note_is_empty(note: ClinicalNote) -> bool:
    has_content = any(
        [
            note.medications,
            note.symptoms,
            note.observations,
            note.actions,
            note.follow_up,
            _vitals_has_value(note.vitals),
            bool(note.note_summary and note.note_summary.strip()),
        ]
    )
    return not has_content


def _validate_completeness(note: ClinicalNote) -> list[ValidationIssue]:
    issues = _validate_medications(note)
    if _note_is_empty(note):
        issues.append(_issue("ERR_NOTE_EMPTY", field_path=None))
    return issues


# --- Public API -------------------------------------------------------------


def validate_note(note: ClinicalNote) -> list[ValidationIssue]:
    """Run all clinical and completeness rules against a parsed note."""
    issues: list[ValidationIssue] = []
    issues.extend(_validate_vitals(note.vitals))
    issues.extend(_validate_completeness(note))
    return issues


def _issues_from_validation_error(error: ValidationError) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for err in error.errors():
        field_path = ".".join(str(part) for part in err.get("loc", ())) or None
        issues.append(
            _issue("ERR_SCHEMA_INVALID", field_path=field_path, detail=err.get("msg", "invalid"))
        )
    return issues


def parse_and_validate(
    content: str | dict[str, object],
) -> tuple[ClinicalNote | None, list[ValidationIssue]]:
    """Parse extracted content and validate it without ever raising.

    Malformed JSON or schema violations are captured as ``schema`` issues and
    returned with ``note=None`` so the pipeline can route to review instead of
    crashing. On success, returns the parsed note and its clinical/completeness
    issues.
    """
    if isinstance(content, str):
        try:
            data: object = json.loads(content)
        except json.JSONDecodeError as exc:
            return None, [_issue("ERR_SCHEMA_INVALID_JSON", detail=str(exc))]
    else:
        data = content

    if not isinstance(data, dict):
        return None, [_issue("ERR_SCHEMA_NOT_OBJECT")]

    try:
        note = ClinicalNote.model_validate(data)
    except ValidationError as exc:
        return None, _issues_from_validation_error(exc)

    return note, validate_note(note)
