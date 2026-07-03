"""Structured clinical note schemas.

Composition-first: the ``ClinicalNote`` aggregates small, explicit sub-models.
These schemas describe documentation structure only — they carry no diagnosis,
treatment, or decision fields, and they perform no range/clinical validation
(that is Phase 5). Clinical sub-models use ``extra="ignore"`` so that varied
model output parses leniently; strictness decisions belong to the validator.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Number

_CLINICAL_CONFIG = ConfigDict(extra="ignore")


class PatientInfo(BaseModel):
    """Patient reference details, as documented in the transcript."""

    model_config = _CLINICAL_CONFIG

    name: str | None = None
    age: int | None = None
    # `sex` is not defined in docs/API.md, so it is kept as a free string per
    # the Phase 4 spec's conditional guidance rather than a fixed Literal.
    sex: str | None = None
    patient_id: str | None = None


class BloodPressure(BaseModel):
    """Blood pressure reading."""

    model_config = _CLINICAL_CONFIG

    systolic: Number | None = None
    diastolic: Number | None = None
    unit: Literal["mmHg"] | None = None


class HeartRate(BaseModel):
    """Heart rate reading."""

    model_config = _CLINICAL_CONFIG

    value: Number | None = None
    unit: Literal["bpm"] | None = None


class Temperature(BaseModel):
    """Body temperature reading."""

    model_config = _CLINICAL_CONFIG

    value: Number | None = None
    unit: Literal["C"] | None = None


class Spo2(BaseModel):
    """Peripheral oxygen saturation reading."""

    model_config = _CLINICAL_CONFIG

    value: Number | None = None
    unit: Literal["%"] | None = None


class Vitals(BaseModel):
    """Collected vital signs. Any subset may be present."""

    model_config = _CLINICAL_CONFIG

    blood_pressure: BloodPressure | None = None
    heart_rate: HeartRate | None = None
    temperature: Temperature | None = None
    spo2: Spo2 | None = None


class Medication(BaseModel):
    """A documented medication. Missing dose is allowed (Phase 5 may flag)."""

    model_config = _CLINICAL_CONFIG

    name: str = Field(..., description="Medication name as documented.")
    dose: str | None = None
    route: str | None = None
    frequency: str | None = None


class Symptom(BaseModel):
    """A reported symptom, kept generic and non-diagnostic."""

    model_config = _CLINICAL_CONFIG

    text: str
    context: str | None = None


class Observation(BaseModel):
    """A documented observation."""

    model_config = _CLINICAL_CONFIG

    text: str
    context: str | None = None


class Action(BaseModel):
    """An action taken or advised, as documented (not a recommendation engine)."""

    model_config = _CLINICAL_CONFIG

    text: str
    context: str | None = None


class FollowUpNote(BaseModel):
    """A follow-up item documented in the transcript."""

    model_config = _CLINICAL_CONFIG

    text: str
    due: str | None = None


class ClinicalNote(BaseModel):
    """Normalized structured clinical note extracted from a transcript."""

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
                "patient": {"name": "Anna Keller"},
                "vitals": {
                    "blood_pressure": {
                        "systolic": 138,
                        "diastolic": 86,
                        "unit": "mmHg",
                    }
                },
                "medications": [
                    {"name": "Metformin", "dose": "500mg", "route": "oral"}
                ],
                "symptoms": [{"text": "mild dizziness"}],
                "observations": [{"text": "resting comfortably"}],
                "actions": [{"text": "advised hydration and routine monitoring"}],
                "follow_up": [],
                "source_language": "en",
            }
        },
    )

    patient: PatientInfo | None = None
    vitals: Vitals | None = None
    medications: list[Medication] = Field(default_factory=list)
    symptoms: list[Symptom] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)
    actions: list[Action] = Field(default_factory=list)
    follow_up: list[FollowUpNote] = Field(default_factory=list)
    source_language: str | None = None
    note_summary: str | None = None
    extracted_at: datetime | None = None
