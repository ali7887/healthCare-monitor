"""Seed the database with a realistic, honest demo dataset.

Run from the backend directory:

    uv run python -m app.seed_demo          # reset + seed
    uv run python -m app.seed_demo --keep    # seed without clearing existing rows

The dataset showcases every routing path so the dashboard, charts, runs table,
and review queue all have meaningful content out of the box:

    * auto-save        — high-confidence, clean extractions
    * needs-review     — flagged for a human, pending in the queue
    * reviewed         — a human approved a flagged run (incl. an *edited* approval)
    * rejected         — routed out automatically (critical issue / very low confidence)
    * failed           — extraction/parse failure (no structured note)

Counts are modest and plausible — this is a demo dataset, not synthetic
production traffic. Runs are spread across the last two weeks so the throughput
trend and routing donut render a natural distribution.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from app.db.session import SessionLocal, engine
from app.models import Run, ValidationLog
from app.models.enums import (
    IssueType,
    Provider,
    ReviewStatus,
    RoutingDecision,
    RunStatus,
    Severity,
)
from app.models.review_item import ReviewItem

# Import the models package so every table is registered before create_all.
import app.models  # noqa: F401,E402
from app.db.base import Base  # noqa: E402


def _breakdown(final: float, *, failure=0.0, retry=0.0, severity=0.0, type_=0.0) -> dict[str, float]:
    raw = round(1.0 - failure - retry - severity - type_, 4)
    return {
        "base_score": 1.0,
        "failure_penalties": failure,
        "retry_penalties": retry,
        "severity_penalties": severity,
        "type_penalties": type_,
        "raw_score": raw,
        "final_score": final,
    }


# --- realistic (non-diagnostic) documentation notes -------------------------

NOTE_STABLE: dict[str, Any] = {
    "patient": {"name": "Anna Keller", "age": 74},
    "vitals": {
        "blood_pressure": {"systolic": 128, "diastolic": 82, "unit": "mmHg"},
        "heart_rate": {"value": 76, "unit": "bpm"},
        "spo2": {"value": 98, "unit": "%"},
    },
    "medications": [{"name": "Metformin", "dose": "500mg", "route": "oral"}],
    "observations": [{"text": "Resting comfortably, no acute distress reported."}],
    "actions": [{"text": "Continued routine monitoring."}],
    "note_summary": "Stable vitals, medication administered as documented.",
    "source_language": "en",
}

NOTE_HYDRATION: dict[str, Any] = {
    "patient": {"name": "Thomas Berg", "age": 68},
    "vitals": {
        "blood_pressure": {"systolic": 134, "diastolic": 84, "unit": "mmHg"},
        "temperature": {"value": 36.8, "unit": "C"},
        "spo2": {"value": 97, "unit": "%"},
    },
    "symptoms": [{"text": "mild dizziness on standing"}],
    "observations": [{"text": "Reports adequate fluid intake."}],
    "actions": [{"text": "Advised hydration and routine monitoring."}],
    "note_summary": "Mild dizziness documented; hydration advised.",
    "source_language": "en",
}

NOTE_HIGH_BP: dict[str, Any] = {
    "patient": {"name": "Renate Fuchs", "age": 81},
    "vitals": {
        "blood_pressure": {"systolic": 172, "diastolic": 101, "unit": "mmHg"},
        "heart_rate": {"value": 92, "unit": "bpm"},
    },
    "symptoms": [{"text": "headache"}],
    "observations": [{"text": "Elevated blood pressure recorded this shift."}],
    "note_summary": "Blood pressure above expected range; flagged for review.",
    "source_language": "en",
}

NOTE_MISSING_DOSE: dict[str, Any] = {
    "patient": {"name": "Jonas Wolf", "age": 59},
    "medications": [{"name": "Amlodipine", "route": "oral"}],
    "observations": [{"text": "Medication administered; dose not documented."}],
    "note_summary": "Medication dose missing from documentation.",
    "source_language": "en",
}

NOTE_LOW_SPO2: dict[str, Any] = {
    "patient": {"name": "Ingrid Sommer", "age": 88},
    "vitals": {"spo2": {"value": 89, "unit": "%"}},
    "symptoms": [{"text": "shortness of breath"}],
    "observations": [{"text": "Oxygen saturation below expected threshold."}],
    "note_summary": "Low oxygen saturation documented; escalated out of auto-save.",
    "source_language": "en",
}

# Reviewer-corrected version of the missing-dose note (edited approval path).
NOTE_MISSING_DOSE_EDITED: dict[str, Any] = {
    **NOTE_MISSING_DOSE,
    "medications": [{"name": "Amlodipine", "dose": "5mg", "route": "oral"}],
    "note_summary": "Dose confirmed with chart and corrected by reviewer (5mg).",
}


# --- one row spec -----------------------------------------------------------


# A validation issue: (type, severity, field_path, message, rule_id).
Issue = tuple[IssueType, Severity, "str | None", str, "str | None"]


@dataclass
class Spec:
    """A single demo run to create. ``day`` is an offset back from today."""

    day: int
    provider: Provider
    status: RunStatus
    routing: RoutingDecision
    confidence: float | None
    note: dict[str, Any] | None
    reason: str
    latency_ms: int
    cost: float
    breakdown: dict[str, float] | None
    warnings: int = 0
    retries: int = 0
    issues: list[Issue] = field(default_factory=list)
    review: ReviewStatus | None = None
    reviewer_notes: str | None = None
    edited_output: dict[str, Any] | None = None


def _specs() -> list[Spec]:
    P_OAI, P_OLL = Provider.openai, Provider.ollama
    return [
        # --- auto-saved (clean, high confidence) ---------------------------
        Spec(day=13, provider=P_OAI, status=RunStatus.auto_saved, routing=RoutingDecision.auto_save,
             confidence=0.97, note=NOTE_STABLE, reason="High confidence; no validation issues.",
             latency_ms=880, cost=0.00021, breakdown=_breakdown(0.97)),
        Spec(day=12, provider=P_OAI, status=RunStatus.auto_saved, routing=RoutingDecision.auto_save,
             confidence=0.95, note=NOTE_HYDRATION, reason="High confidence; no validation issues.",
             latency_ms=910, cost=0.00023, breakdown=_breakdown(0.95)),
        Spec(day=11, provider=P_OLL, status=RunStatus.auto_saved, routing=RoutingDecision.auto_save,
             confidence=0.9, note=NOTE_STABLE, reason="Above auto-save threshold.",
             latency_ms=1420, cost=0.0, breakdown=_breakdown(0.9), warnings=1,
             issues=[(IssueType.completeness, Severity.warning, "patient.patient_id",
                      "Patient identifier not documented.", "WARN_MISSING_PATIENT_ID")]),
        Spec(day=10, provider=P_OAI, status=RunStatus.auto_saved, routing=RoutingDecision.auto_save,
             confidence=0.99, note=NOTE_STABLE, reason="High confidence; no validation issues.",
             latency_ms=790, cost=0.0002, breakdown=_breakdown(0.99)),
        Spec(day=9, provider=P_OAI, status=RunStatus.auto_saved, routing=RoutingDecision.auto_save,
             confidence=0.93, note=NOTE_HYDRATION, reason="High confidence; no validation issues.",
             latency_ms=845, cost=0.00022, breakdown=_breakdown(0.93)),
        Spec(day=7, provider=P_OLL, status=RunStatus.auto_saved, routing=RoutingDecision.auto_save,
             confidence=0.88, note=NOTE_STABLE, reason="Above auto-save threshold.",
             latency_ms=1610, cost=0.0, breakdown=_breakdown(0.88)),
        Spec(day=6, provider=P_OAI, status=RunStatus.auto_saved, routing=RoutingDecision.auto_save,
             confidence=0.96, note=NOTE_HYDRATION, reason="High confidence; no validation issues.",
             latency_ms=870, cost=0.00021, breakdown=_breakdown(0.96)),
        Spec(day=4, provider=P_OAI, status=RunStatus.auto_saved, routing=RoutingDecision.auto_save,
             confidence=0.94, note=NOTE_STABLE, reason="High confidence; no validation issues.",
             latency_ms=830, cost=0.0002, breakdown=_breakdown(0.94)),
        Spec(day=3, provider=P_OAI, status=RunStatus.auto_saved, routing=RoutingDecision.auto_save,
             confidence=0.91, note=NOTE_HYDRATION, reason="Above auto-save threshold.",
             latency_ms=905, cost=0.00023, breakdown=_breakdown(0.91)),
        Spec(day=1, provider=P_OAI, status=RunStatus.auto_saved, routing=RoutingDecision.auto_save,
             confidence=0.98, note=NOTE_STABLE, reason="High confidence; no validation issues.",
             latency_ms=810, cost=0.0002, breakdown=_breakdown(0.98)),
        Spec(day=0, provider=P_OAI, status=RunStatus.auto_saved, routing=RoutingDecision.auto_save,
             confidence=0.92, note=NOTE_HYDRATION, reason="Above auto-save threshold.",
             latency_ms=860, cost=0.00021, breakdown=_breakdown(0.92)),

        # --- needs review (pending in the queue) ---------------------------
        Spec(day=8, provider=P_OAI, status=RunStatus.needs_review, routing=RoutingDecision.human_review,
             confidence=0.72, note=NOTE_HIGH_BP, reason="Blood pressure outside expected range; flagged for review.",
             latency_ms=980, cost=0.00024, breakdown=_breakdown(0.72, severity=0.15, type_=0.13),
             warnings=1, review=ReviewStatus.pending,
             issues=[(IssueType.clinical, Severity.warning, "vitals.blood_pressure.systolic",
                      "Systolic blood pressure above expected range (>140 mmHg).", "WARN_BP_HIGH")]),
        Spec(day=5, provider=P_OLL, status=RunStatus.needs_review, routing=RoutingDecision.human_review,
             confidence=0.64, note=NOTE_MISSING_DOSE, reason="Missing medication dose; flagged for review.",
             latency_ms=1550, cost=0.0, breakdown=_breakdown(0.64, severity=0.16, type_=0.2),
             warnings=1, retries=1, review=ReviewStatus.pending,
             issues=[(IssueType.completeness, Severity.warning, "medications.0.dose",
                      "Medication dose not documented.", "WARN_MISSING_DOSE")]),
        Spec(day=2, provider=P_OAI, status=RunStatus.needs_review, routing=RoutingDecision.human_review,
             confidence=0.68, note=NOTE_HIGH_BP, reason="Elevated blood pressure; confidence below auto-save threshold.",
             latency_ms=940, cost=0.00023, breakdown=_breakdown(0.68, severity=0.15, type_=0.17),
             warnings=1, review=ReviewStatus.pending,
             issues=[(IssueType.clinical, Severity.warning, "vitals.blood_pressure.diastolic",
                      "Diastolic blood pressure above expected range (>90 mmHg).", "WARN_BP_HIGH")]),

        # --- reviewed (human approved a flagged run) -----------------------
        Spec(day=6, provider=P_OAI, status=RunStatus.reviewed, routing=RoutingDecision.human_review,
             confidence=0.7, note=NOTE_HIGH_BP, reason="Blood pressure outside expected range; flagged for review.",
             latency_ms=960, cost=0.00024, breakdown=_breakdown(0.7, severity=0.15, type_=0.15),
             warnings=1, review=ReviewStatus.approved,
             reviewer_notes="Confirmed elevated BP is known/managed for this patient. Documentation accepted.",
             issues=[(IssueType.clinical, Severity.warning, "vitals.blood_pressure.systolic",
                      "Systolic blood pressure above expected range (>140 mmHg).", "WARN_BP_HIGH")]),
        # edited approval: reviewer corrected the note before approving
        Spec(day=3, provider=P_OLL, status=RunStatus.reviewed, routing=RoutingDecision.human_review,
             confidence=0.66, note=NOTE_MISSING_DOSE, reason="Missing medication dose; flagged for review.",
             latency_ms=1580, cost=0.0, breakdown=_breakdown(0.66, severity=0.16, type_=0.18),
             warnings=1, retries=1, review=ReviewStatus.approved,
             reviewer_notes="Dose verified against medication chart; corrected to 5mg before approval.",
             edited_output=NOTE_MISSING_DOSE_EDITED,
             issues=[(IssueType.completeness, Severity.warning, "medications.0.dose",
                      "Medication dose not documented.", "WARN_MISSING_DOSE")]),

        # --- rejected (routed out automatically) ---------------------------
        Spec(day=9, provider=P_OAI, status=RunStatus.rejected, routing=RoutingDecision.reject,
             confidence=0.34, note=NOTE_LOW_SPO2, reason="Critical clinical issue detected; routed out of auto-save.",
             latency_ms=1010, cost=0.00025, breakdown=_breakdown(0.34, severity=0.5, type_=0.16),
             warnings=0,
             issues=[(IssueType.clinical, Severity.critical, "vitals.spo2.value",
                      "Oxygen saturation critically low (<90%).", "ERR_SPO2_LOW")]),
        Spec(day=2, provider=P_OLL, status=RunStatus.rejected, routing=RoutingDecision.reject,
             confidence=0.41, note=NOTE_LOW_SPO2, reason="Confidence below reject threshold.",
             latency_ms=1620, cost=0.0, breakdown=_breakdown(0.41, severity=0.4, type_=0.19),
             issues=[(IssueType.clinical, Severity.critical, "vitals.spo2.value",
                      "Oxygen saturation critically low (<90%).", "ERR_SPO2_LOW")]),

        # --- failed (extraction/parse failure, no structured note) ---------
        Spec(day=10, provider=P_OLL, status=RunStatus.failed, routing=RoutingDecision.reject,
             confidence=None, note=None, reason="Extraction failed to produce valid JSON after one retry.",
             latency_ms=1730, cost=0.0, breakdown=None, retries=1,
             issues=[(IssueType.format, Severity.critical, None,
                      "Model response was not valid JSON.", "ERR_INVALID_JSON")]),
    ]


_TRANSCRIPTS = {
    "en": "Nursing shift note dictated by caregiver; see structured extraction for details.",
}


def _make_run(spec: Spec, now: datetime) -> Run:
    created = now - timedelta(days=spec.day, hours=(spec.day % 5) + 1)
    note = spec.note
    final = None
    if spec.status == RunStatus.auto_saved:
        final = note
    elif spec.status == RunStatus.reviewed:
        final = spec.edited_output if spec.edited_output is not None else note

    raw = None if note is None else "{...model JSON...}"
    run = Run(
        transcript=_TRANSCRIPTS["en"],
        provider=spec.provider,
        status=spec.status,
        warnings_count=spec.warnings,
        retry_count=spec.retries,
        confidence=spec.confidence,
        latency_ms=spec.latency_ms,
        cost=spec.cost,
        raw_model_response=raw,
        parsed_output=note,
        final_output=final,
        routing_decision=spec.routing,
        routing_reason=spec.reason,
        confidence_breakdown=spec.breakdown,
        created_at=created,
        updated_at=created,
    )
    for issue_type, severity, field, message, rule_id in spec.issues or []:
        run.validation_logs.append(
            ValidationLog(
                issue_type=issue_type,
                severity=severity,
                field=field,
                message=message,
                rule_id=rule_id,
                created_at=created,
            )
        )
    if spec.review is not None:
        run.review_items.append(
            ReviewItem(
                status=spec.review,
                reviewer_notes=spec.reviewer_notes,
                edited_output=spec.edited_output,
                created_at=created,
            )
        )
    return run


def seed(*, reset: bool = True) -> dict[str, int]:
    """Populate the database with the demo dataset. Returns a status→count map."""
    import app.models  # noqa: F401  (ensure tables are registered)

    Base.metadata.create_all(engine)

    db = SessionLocal()
    try:
        if reset:
            # Delete children first for engines without cascade enforcement.
            db.query(ValidationLog).delete()
            db.query(ReviewItem).delete()
            db.query(Run).delete()
            db.commit()

        now = datetime.now(timezone.utc)
        runs = [_make_run(spec, now) for spec in _specs()]
        db.add_all(runs)
        db.commit()

        counts: dict[str, int] = {}
        for run in runs:
            counts[run.status.value] = counts.get(run.status.value, 0) + 1
        return counts
    finally:
        db.close()


def main() -> None:
    reset = "--keep" not in sys.argv
    counts = seed(reset=reset)
    total = sum(counts.values())
    print(f"Seeded {total} demo runs ({'reset' if reset else 'appended'}):")
    for status, count in sorted(counts.items()):
        print(f"  {status:<14} {count}")


if __name__ == "__main__":
    main()
