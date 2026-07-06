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
from app.core.logging import configure_logging
from app.core.telemetry import log_seed_complete
from app.models.review_item import ReviewItem
from app.services.reasoning import build_reasoning_summary

# Import the models package so every table is registered before create_all.
import app.models  # noqa: F401,E402
from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402


def _breakdown(*, failure=0.0, retry=0.0, severity=0.0, type_=0.0) -> dict[str, float]:
    """Additive breakdown mirroring ``ConfidenceScorer``.

    The final score is *derived* from the penalties — never stated
    independently — so every seeded trace satisfies
    ``base - penalties == raw == final`` exactly as the live engine does.
    """
    raw = round(1.0 - failure - retry - severity - type_, 4)
    return {
        "base_score": 1.0,
        "failure_penalties": failure,
        "retry_penalties": retry,
        "severity_penalties": severity,
        "type_penalties": type_,
        "raw_score": raw,
        "final_score": round(max(0.0, min(1.0, raw)), 4),
    }


def _omit(note: dict[str, Any], *, spo2: bool = False, age: bool = False) -> dict[str, Any]:
    """A note variant with named fields absent, to pair with completeness warnings."""
    out = {**note, "patient": dict(note["patient"]), "vitals": dict(note.get("vitals", {}))}
    if spo2:
        out["vitals"].pop("spo2", None)
    if age:
        out["patient"].pop("age", None)
    return out


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
        "spo2": {"value": 96, "unit": "%"},
    },
    "symptoms": [{"text": "headache"}],
    "observations": [{"text": "Elevated blood pressure recorded this shift."}],
    "actions": [{"text": "Escalated to supervising nurse for blood pressure recheck."}],
    "note_summary": "Blood pressure above expected range; flagged for review.",
    "source_language": "en",
}

NOTE_MISSING_DOSE: dict[str, Any] = {
    "patient": {"name": "Jonas Wolf", "age": 59},
    "vitals": {"spo2": {"value": 97, "unit": "%"}},
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

# Incomplete-documentation variants. Each omission pairs with a completeness
# warning below, so identical notes always carry identical issue lists.
NOTE_STABLE_PARTIAL = _omit(NOTE_STABLE, spo2=True)
NOTE_STABLE_MINIMAL = _omit(NOTE_STABLE, spo2=True, age=True)
NOTE_HYDRATION_PARTIAL = _omit(NOTE_HYDRATION, spo2=True)
NOTE_HYDRATION_MINIMAL = _omit(NOTE_HYDRATION, spo2=True, age=True)


# --- one row spec -----------------------------------------------------------


# A validation issue: (type, severity, field_path, message, rule_id).
Issue = tuple[IssueType, Severity, "str | None", str, "str | None"]

# Deterministic validation produces identical issues for identical notes, so
# shared issue tuples are reused wherever a note (or variant) recurs.
WARN_SPO2_NOT_DOCUMENTED: Issue = (
    IssueType.completeness, Severity.warning, "vitals.spo2",
    "Oxygen saturation not documented.", "WARN_MISSING_SPO2")
WARN_AGE_NOT_DOCUMENTED: Issue = (
    IssueType.completeness, Severity.warning, "patient.age",
    "Patient age not documented.", "WARN_MISSING_AGE")
WARN_BP_SYSTOLIC: Issue = (
    IssueType.clinical, Severity.warning, "vitals.blood_pressure.systolic",
    "Systolic blood pressure above expected range (>140 mmHg).", "WARN_BP_HIGH")
WARN_BP_DIASTOLIC: Issue = (
    IssueType.clinical, Severity.warning, "vitals.blood_pressure.diastolic",
    "Diastolic blood pressure above expected range (>90 mmHg).", "WARN_BP_HIGH")
WARN_DOSE_MISSING: Issue = (
    IssueType.completeness, Severity.warning, "medications.0.dose",
    "Medication dose not documented.", "WARN_MISSING_DOSE")
WARN_ACTION_MISSING: Issue = (
    IssueType.completeness, Severity.warning, "actions",
    "No follow-up action documented for the abnormal finding.", "WARN_MISSING_ACTION")
CRIT_SPO2_LOW: Issue = (
    IssueType.clinical, Severity.critical, "vitals.spo2.value",
    "Oxygen saturation critically low (<90%).", "ERR_SPO2_LOW")
CRIT_INVALID_JSON: Issue = (
    IssueType.format, Severity.critical, None,
    "Model response was not valid JSON.", "ERR_INVALID_JSON")


@dataclass
class Spec:
    """A single demo run to create. ``day`` is an offset back from today.

    There is deliberately no ``confidence`` field: the run's confidence is
    always the breakdown's derived ``final_score`` (or ``None`` for failures),
    so seeded scores can never drift from their own penalty arithmetic.
    """

    day: int
    provider: Provider
    status: RunStatus
    routing: RoutingDecision
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
    """Demo runs whose penalties, issues, retries, and routing all agree.

    Penalty magnitudes mirror the ``ConfidenceScorer`` weight tables — warning
    severity 0.04/issue, critical severity 0.12/issue, type penalties 0.03
    (completeness) / 0.04 (clinical) per issue, retries 0.15 plus a trigger
    addon (provider 0.08, schema 0.12, invalid JSON 0.15) — and every derived
    final score lands in the routing band its spec claims (auto-save >= 0.85,
    review band [0.50, 0.85), reject < 0.50).
    """
    P_OAI, P_OLL = Provider.openai, Provider.ollama
    return [
        # --- auto-saved: clean notes score exactly 1.0; incomplete variants
        # carry completeness warnings and land at 0.93 / 0.86 ----------------
        Spec(day=13, provider=P_OAI, status=RunStatus.auto_saved, routing=RoutingDecision.auto_save,
             note=NOTE_STABLE, reason="No validation issues; saved automatically.",
             latency_ms=880, cost=0.00021, breakdown=_breakdown()),
        Spec(day=12, provider=P_OAI, status=RunStatus.auto_saved, routing=RoutingDecision.auto_save,
             note=NOTE_HYDRATION, reason="No validation issues; saved automatically.",
             latency_ms=910, cost=0.00023, breakdown=_breakdown()),
        Spec(day=11, provider=P_OLL, status=RunStatus.auto_saved, routing=RoutingDecision.auto_save,
             note=NOTE_STABLE_PARTIAL, reason="Minor completeness warning; above auto-save threshold.",
             latency_ms=1420, cost=0.0, breakdown=_breakdown(severity=0.04, type_=0.03),
             warnings=1, issues=[WARN_SPO2_NOT_DOCUMENTED]),
        Spec(day=10, provider=P_OAI, status=RunStatus.auto_saved, routing=RoutingDecision.auto_save,
             note=NOTE_STABLE, reason="No validation issues; saved automatically.",
             latency_ms=790, cost=0.0002, breakdown=_breakdown()),
        Spec(day=9, provider=P_OAI, status=RunStatus.auto_saved, routing=RoutingDecision.auto_save,
             note=NOTE_HYDRATION_PARTIAL, reason="Minor completeness warning; above auto-save threshold.",
             latency_ms=845, cost=0.00022, breakdown=_breakdown(severity=0.04, type_=0.03),
             warnings=1, issues=[WARN_SPO2_NOT_DOCUMENTED]),
        Spec(day=7, provider=P_OLL, status=RunStatus.auto_saved, routing=RoutingDecision.auto_save,
             note=NOTE_STABLE_MINIMAL, reason="Two completeness warnings; above auto-save threshold.",
             latency_ms=1610, cost=0.0, breakdown=_breakdown(severity=0.08, type_=0.06),
             warnings=2, issues=[WARN_SPO2_NOT_DOCUMENTED, WARN_AGE_NOT_DOCUMENTED]),
        Spec(day=6, provider=P_OAI, status=RunStatus.auto_saved, routing=RoutingDecision.auto_save,
             note=NOTE_HYDRATION, reason="No validation issues; saved automatically.",
             latency_ms=870, cost=0.00021, breakdown=_breakdown()),
        Spec(day=4, provider=P_OAI, status=RunStatus.auto_saved, routing=RoutingDecision.auto_save,
             note=NOTE_STABLE_PARTIAL, reason="Minor completeness warning; above auto-save threshold.",
             latency_ms=830, cost=0.0002, breakdown=_breakdown(severity=0.04, type_=0.03),
             warnings=1, issues=[WARN_SPO2_NOT_DOCUMENTED]),
        Spec(day=3, provider=P_OAI, status=RunStatus.auto_saved, routing=RoutingDecision.auto_save,
             note=NOTE_HYDRATION_MINIMAL, reason="Two completeness warnings; above auto-save threshold.",
             latency_ms=905, cost=0.00023, breakdown=_breakdown(severity=0.08, type_=0.06),
             warnings=2, issues=[WARN_SPO2_NOT_DOCUMENTED, WARN_AGE_NOT_DOCUMENTED]),
        Spec(day=1, provider=P_OAI, status=RunStatus.auto_saved, routing=RoutingDecision.auto_save,
             note=NOTE_STABLE, reason="No validation issues; saved automatically.",
             latency_ms=810, cost=0.0002, breakdown=_breakdown()),
        Spec(day=0, provider=P_OAI, status=RunStatus.auto_saved, routing=RoutingDecision.auto_save,
             note=NOTE_HYDRATION_PARTIAL, reason="Minor completeness warning; above auto-save threshold.",
             latency_ms=860, cost=0.00021, breakdown=_breakdown(severity=0.04, type_=0.03),
             warnings=1, issues=[WARN_SPO2_NOT_DOCUMENTED]),

        # --- needs review (pending in the queue) ---------------------------
        # NOTE_HIGH_BP always yields the same two clinical warnings; runs
        # differ only by retry penalties.
        Spec(day=8, provider=P_OAI, status=RunStatus.needs_review, routing=RoutingDecision.human_review,
             note=NOTE_HIGH_BP, reason="Blood pressure outside expected range; confidence below auto-save threshold.",
             latency_ms=980, cost=0.00024, breakdown=_breakdown(severity=0.08, type_=0.08),
             warnings=2, review=ReviewStatus.pending,
             issues=[WARN_BP_SYSTOLIC, WARN_BP_DIASTOLIC]),
        Spec(day=5, provider=P_OLL, status=RunStatus.needs_review, routing=RoutingDecision.human_review,
             note=NOTE_MISSING_DOSE, reason="Missing medication dose; retry used; flagged for review.",
             latency_ms=1550, cost=0.0, breakdown=_breakdown(severity=0.04, type_=0.03, retry=0.27),
             warnings=1, retries=1, review=ReviewStatus.pending,
             issues=[WARN_DOSE_MISSING]),
        Spec(day=2, provider=P_OAI, status=RunStatus.needs_review, routing=RoutingDecision.human_review,
             note=NOTE_HIGH_BP, reason="Elevated blood pressure; retry used; confidence below auto-save threshold.",
             latency_ms=940, cost=0.00023, breakdown=_breakdown(severity=0.08, type_=0.08, retry=0.23),
             warnings=2, retries=1, review=ReviewStatus.pending,
             issues=[WARN_BP_SYSTOLIC, WARN_BP_DIASTOLIC]),

        # --- reviewed (human approved a flagged run) -----------------------
        Spec(day=6, provider=P_OAI, status=RunStatus.reviewed, routing=RoutingDecision.human_review,
             note=NOTE_HIGH_BP, reason="Blood pressure outside expected range; confidence below auto-save threshold.",
             latency_ms=960, cost=0.00024, breakdown=_breakdown(severity=0.08, type_=0.08),
             warnings=2, review=ReviewStatus.approved,
             reviewer_notes="Confirmed elevated BP is known/managed for this patient. Documentation accepted.",
             issues=[WARN_BP_SYSTOLIC, WARN_BP_DIASTOLIC]),
        # edited approval: reviewer corrected the note before approving
        Spec(day=3, provider=P_OLL, status=RunStatus.reviewed, routing=RoutingDecision.human_review,
             note=NOTE_MISSING_DOSE, reason="Missing medication dose; retry used; flagged for review.",
             latency_ms=1580, cost=0.0, breakdown=_breakdown(severity=0.04, type_=0.03, retry=0.30),
             warnings=1, retries=1, review=ReviewStatus.approved,
             reviewer_notes="Dose verified against medication chart; corrected to 5mg before approval.",
             edited_output=NOTE_MISSING_DOSE_EDITED,
             issues=[WARN_DOSE_MISSING]),

        # --- rejected (routed out automatically; score must be < 0.50) -----
        # NOTE_LOW_SPO2 always yields the same critical + completeness pair.
        Spec(day=9, provider=P_OAI, status=RunStatus.rejected, routing=RoutingDecision.reject,
             note=NOTE_LOW_SPO2, reason="Critical clinical issue; confidence below reject threshold.",
             latency_ms=1010, cost=0.00025, breakdown=_breakdown(severity=0.16, type_=0.07, retry=0.30),
             warnings=1, retries=1,
             issues=[CRIT_SPO2_LOW, WARN_ACTION_MISSING]),
        Spec(day=2, provider=P_OLL, status=RunStatus.rejected, routing=RoutingDecision.reject,
             note=NOTE_LOW_SPO2, reason="Critical clinical issue; confidence below reject threshold.",
             latency_ms=1620, cost=0.0, breakdown=_breakdown(severity=0.16, type_=0.07, retry=0.30),
             warnings=1, retries=1,
             issues=[CRIT_SPO2_LOW, WARN_ACTION_MISSING]),

        # --- failed (extraction/parse failure, no structured note) ---------
        Spec(day=10, provider=P_OLL, status=RunStatus.failed, routing=RoutingDecision.reject,
             note=None, reason="Extraction failed to produce valid JSON after one retry.",
             latency_ms=1730, cost=0.0, breakdown=None, retries=1,
             issues=[CRIT_INVALID_JSON]),
    ]


# --- verbatim caregiver dictations --------------------------------------------
# One transcript per note constant, keyed by object identity (the notes are
# module-level constants, so identity is stable). Each transcript mentions
# exactly what its note extracts — and *omits* what the completeness warnings
# flag — so transcript, extraction, and validation always tell the same story.

_TRANSCRIPT_STABLE = (
    "Shift note for Anna Keller, 74 years old. Blood pressure this morning 128 over 82, "
    "heart rate 76, oxygen saturation 98 percent. Metformin 500 milligrams given by mouth "
    "as scheduled. She is resting comfortably and reports no acute distress. "
    "Continuing routine monitoring."
)
_TRANSCRIPT_STABLE_PARTIAL = (
    "Shift note for Anna Keller, 74 years old. Blood pressure this morning 128 over 82, "
    "heart rate 76. Metformin 500 milligrams given by mouth as scheduled. She is resting "
    "comfortably and reports no acute distress. Continuing routine monitoring."
)
_TRANSCRIPT_STABLE_MINIMAL = (
    "Quick note for Anna Keller. Blood pressure 128 over 82, heart rate 76. Metformin "
    "500 milligrams given by mouth as scheduled. Resting comfortably, no acute distress. "
    "Continuing routine monitoring."
)
_TRANSCRIPT_HYDRATION = (
    "Note for Thomas Berg, 68 years old. Blood pressure 134 over 84, temperature 36.8, "
    "oxygen saturation 97 percent. He mentions mild dizziness when standing up. Fluid "
    "intake looks adequate today. I advised him to keep drinking regularly and we will "
    "continue routine monitoring."
)
_TRANSCRIPT_HYDRATION_PARTIAL = (
    "Note for Thomas Berg, 68 years old. Blood pressure 134 over 84, temperature 36.8. "
    "He mentions mild dizziness when standing up. Fluid intake looks adequate today. "
    "I advised him to keep drinking regularly and we will continue routine monitoring."
)
_TRANSCRIPT_HYDRATION_MINIMAL = (
    "Note for Thomas Berg. Blood pressure 134 over 84, temperature 36.8. He mentions "
    "mild dizziness when standing up. Fluid intake looks adequate. Advised him to keep "
    "drinking regularly, continuing routine monitoring."
)
_TRANSCRIPT_HIGH_BP = (
    "Renate Fuchs, 81 years old. Blood pressure this shift 172 over 101, pulse 92, "
    "oxygen saturation 96 percent. She complains of a headache. That blood pressure is "
    "well above her usual range, so I escalated to the supervising nurse for a recheck."
)
_TRANSCRIPT_MISSING_DOSE = (
    "Jonas Wolf, 59 years old. Oxygen saturation 97 percent. I gave him his Amlodipine "
    "by mouth this morning — I don't have the dose in front of me right now, it should "
    "be on the chart. Otherwise nothing new to report."
)
_TRANSCRIPT_LOW_SPO2 = (
    "Ingrid Sommer, 88 years old. Oxygen saturation is reading 89 percent and she says "
    "she is short of breath. That saturation is below where we expect her to be."
)
# The failed run's input: a dictation the recorder mangled, so extraction never
# produced valid JSON.
_TRANSCRIPT_GARBLED = (
    "Evening note for — [audio cuts out] — vitals were — [inaudible] — sorry, the "
    "recorder keeps dropping. I will redo this note at the end of the round."
)

_TRANSCRIPTS: dict[int, str] = {
    id(NOTE_STABLE): _TRANSCRIPT_STABLE,
    id(NOTE_STABLE_PARTIAL): _TRANSCRIPT_STABLE_PARTIAL,
    id(NOTE_STABLE_MINIMAL): _TRANSCRIPT_STABLE_MINIMAL,
    id(NOTE_HYDRATION): _TRANSCRIPT_HYDRATION,
    id(NOTE_HYDRATION_PARTIAL): _TRANSCRIPT_HYDRATION_PARTIAL,
    id(NOTE_HYDRATION_MINIMAL): _TRANSCRIPT_HYDRATION_MINIMAL,
    id(NOTE_HIGH_BP): _TRANSCRIPT_HIGH_BP,
    id(NOTE_MISSING_DOSE): _TRANSCRIPT_MISSING_DOSE,
    id(NOTE_LOW_SPO2): _TRANSCRIPT_LOW_SPO2,
}


def _make_run(spec: Spec, now: datetime) -> Run:
    created = now - timedelta(days=spec.day, hours=(spec.day % 5) + 1)
    confidence = spec.breakdown["final_score"] if spec.breakdown is not None else None

    # Guard: seeded scores must obey the real routing thresholds (routing.py),
    # so the demo can never show a score/routing pair the engine would not produce.
    if confidence is not None:
        has_critical = any(sev is Severity.critical for _, sev, _, _, _ in spec.issues)
        if spec.routing is RoutingDecision.auto_save:
            assert confidence >= 0.85 and not has_critical, spec
        elif spec.routing is RoutingDecision.reject:
            assert confidence < 0.50, spec
        else:
            assert 0.50 <= confidence < 0.85 or has_critical, spec

    note = spec.note
    final = None
    if spec.status == RunStatus.auto_saved:
        final = note
    elif spec.status == RunStatus.reviewed:
        final = spec.edited_output if spec.edited_output is not None else note

    raw = None if note is None else "{...model JSON...}"
    reasoning = build_reasoning_summary(
        succeeded=spec.status != RunStatus.failed,
        decision=spec.routing.value,
        confidence=confidence,
        issues=[(sev.value, message, rule_id) for _, sev, _, message, rule_id in spec.issues],
    )
    run = Run(
        transcript=_TRANSCRIPTS[id(note)] if note is not None else _TRANSCRIPT_GARBLED,
        provider=spec.provider,
        status=spec.status,
        warnings_count=spec.warnings,
        retry_count=spec.retries,
        confidence=confidence,
        latency_ms=spec.latency_ms,
        cost=spec.cost,
        raw_model_response=raw,
        parsed_output=note,
        final_output=final,
        routing_decision=spec.routing,
        routing_reason=spec.reason,
        confidence_breakdown=spec.breakdown,
        reasoning_summary=reasoning,
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
    """Populate the database with the demo dataset. Returns a status→count map.

    On SQLite (the local/demo default) a reset does a full drop+create so schema
    changes (new columns) are picked up automatically without a migration step.
    On Postgres, where Alembic owns the schema, a reset only clears rows.
    """
    import app.models  # noqa: F401  (ensure tables are registered)

    if reset and get_settings().is_sqlite:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    db = SessionLocal()
    try:
        if reset and not get_settings().is_sqlite:
            # Postgres: schema is Alembic-managed, so clear rows only. Delete
            # children first for engines without cascade enforcement.
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
    configure_logging()
    reset = "--keep" not in sys.argv
    counts = seed(reset=reset)
    total = sum(counts.values())
    log_seed_complete(total=total, reset=reset)
    print(f"Seeded {total} demo runs ({'reset' if reset else 'appended'}):")
    for status, count in sorted(counts.items()):
        print(f"  {status:<14} {count}")


if __name__ == "__main__":
    main()
