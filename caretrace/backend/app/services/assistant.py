"""AI Reviewer Assistant: advisory differential analysis for human reviewers.

This service simulates an LLM-backed clinical reviewer assistant using
deterministic, keyword- and diff-based heuristics so the demo is reproducible
and offline-safe. The analysis is *advisory only*: it never approves, rejects,
or mutates a run.

The single async entry point (``AssistantService.analyze_review``) is shaped so
the deterministic core can later be swapped for a real provider call — e.g.
``await client.chat.completions.create(...)`` — without changing callers. The
pure ``analyze_edit`` function holds the heuristics and is unit-tested directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.services.persistence import get_run

# Free-text findings that warrant a reviewer's explicit attention. The value is
# the phrasing surfaced in the advisory (kept clinically neutral: we flag for
# review, we never diagnose).
_HIGH_ALERT_TERMS: dict[str, str] = {
    "chest pain": "chest pain",
    "shortness of breath": "shortness of breath",
    "short of breath": "shortness of breath",
    "difficulty breathing": "difficulty breathing",
    "bleeding": "active bleeding",
    "anaphylaxis": "anaphylaxis",
    "allergic": "a possible allergic reaction",
    "unresponsive": "an unresponsive patient",
    "overdose": "a possible overdose",
    "sepsis": "possible sepsis",
    "suicidal": "an expressed self-harm risk",
}


@dataclass
class AssistantAnalysis:
    """Result of an advisory review analysis."""

    clinical_risks: list[str] = field(default_factory=list)
    suggestion: str = ""
    confidence_score: float = 0.0


class RunNotFoundError(LookupError):
    """Raised when analysis is requested for a run that does not exist."""


def _as_dicts(items: Any) -> list[dict[str, Any]]:
    return [item for item in items or [] if isinstance(item, dict)]


def _text_blob(note: dict[str, Any]) -> str:
    """Concatenate the free-text fields of a note for keyword scanning."""
    parts: list[str] = []
    summary = note.get("note_summary")
    if isinstance(summary, str):
        parts.append(summary)
    for key in ("observations", "symptoms"):
        for item in _as_dicts(note.get(key)):
            text = item.get("text")
            if isinstance(text, str):
                parts.append(text)
    return " ".join(parts).lower()


def _content_risks(note: dict[str, Any]) -> list[str]:
    """Deterministic keyword + vital-range risk detection on a single note."""
    risks: list[str] = []

    # High-alert free-text findings (deduplicated by surfaced phrasing).
    blob = _text_blob(note)
    seen: set[str] = set()
    for term, phrase in _HIGH_ALERT_TERMS.items():
        if term in blob and phrase not in seen:
            seen.add(phrase)
            risks.append(
                f"Documentation mentions {phrase} — a potentially high-acuity "
                "finding; confirm appropriate escalation is recorded."
            )

    # Medications missing a dose.
    for med in _as_dicts(note.get("medications")):
        name = med.get("name")
        if name and not med.get("dose"):
            risks.append(
                f"Medication '{name}' has no documented dose — confirm before "
                "administration."
            )

    # Out-of-range vitals (safe-range checks, not diagnoses).
    vitals = note.get("vitals")
    if isinstance(vitals, dict):
        risks.extend(_vital_risks(vitals))

    return risks


def _vital_value(vital: Any) -> float | None:
    if isinstance(vital, dict) and isinstance(vital.get("value"), (int, float)):
        return float(vital["value"])
    return None


def _vital_risks(vitals: dict[str, Any]) -> list[str]:
    """Out-of-range vitals, using the same thresholds as clinical validation.

    Kept in lockstep with ``app.services.validation`` (systolic >140/<90,
    diastolic >90/<60, HR >100/<60, temperature >38.0/<36.0, SpO₂ <95) so the
    assistant never contradicts the deterministic routing engine.
    """
    risks: list[str] = []

    spo2 = _vital_value(vitals.get("spo2"))
    if spo2 is not None and spo2 < 95:
        risks.append(
            f"Recorded SpO₂ ({spo2:g}%) is below the safe threshold (< 95%) — "
            "verify oxygenation status."
        )

    hr = _vital_value(vitals.get("heart_rate"))
    if hr is not None and (hr > 100 or hr < 60):
        risks.append(
            f"Heart rate ({hr:g} bpm) is outside the expected range (60–100) — "
            "confirm the reading."
        )

    temp = _vital_value(vitals.get("temperature"))
    if temp is not None and (temp > 38.0 or temp < 36.0):
        risks.append(
            f"Temperature ({temp:g}°C) is outside the expected range (36.0–38.0) — "
            "confirm and document any response."
        )

    bp = vitals.get("blood_pressure")
    if isinstance(bp, dict):
        systolic = bp.get("systolic")
        diastolic = bp.get("diastolic")
        if isinstance(systolic, (int, float)) and (systolic > 140 or systolic < 90):
            risks.append(
                f"Systolic blood pressure ({systolic:g} mmHg) is outside the "
                "expected range (90–140) — verify the reading."
            )
        if isinstance(diastolic, (int, float)) and (diastolic > 90 or diastolic < 60):
            risks.append(
                f"Diastolic blood pressure ({diastolic:g} mmHg) is outside the "
                "expected range (60–90) — verify the reading."
            )

    return risks


def _diff_risks(original: dict[str, Any], edited: dict[str, Any]) -> list[str]:
    """Risks arising from *changes* between the original extraction and the edit."""
    risks: list[str] = []

    def _meds(note: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {
            med["name"]: med
            for med in _as_dicts(note.get("medications"))
            if med.get("name")
        }

    orig_meds = _meds(original)
    edit_meds = _meds(edited)

    for name, med in edit_meds.items():
        if name in orig_meds and med.get("dose") != orig_meds[name].get("dose"):
            before = orig_meds[name].get("dose") or "unspecified"
            after = med.get("dose") or "unspecified"
            risks.append(
                f"Dose for '{name}' changed from '{before}' to '{after}' — verify "
                "against the medication chart."
            )

    for name in orig_meds:
        if name not in edit_meds:
            risks.append(
                f"Medication '{name}' was removed from the original extraction — "
                "confirm this is intended."
            )

    return risks


def _confidence(original: dict[str, Any], edited: dict[str, Any], risk_count: int) -> float:
    """Synthetic confidence from edit magnitude and flagged-risk count.

    A larger correction, or more flagged concerns, lowers the assistant's
    confidence that the output is ready — nudging the reviewer to scrutinize more.
    """
    changed = sum(
        1 for key in set(original) | set(edited) if original.get(key) != edited.get(key)
    )
    score = 0.95 - 0.07 * changed - 0.05 * risk_count
    return round(max(0.4, min(0.97, score)), 2)


def analyze_edit(*, original: dict[str, Any], edited: dict[str, Any]) -> AssistantAnalysis:
    """Deterministic advisory analysis of an edited output against the original.

    Combines content-based risk detection (keywords + vital ranges) with
    diff-based risks (dose changes, removed medications). Pure and side-effect
    free — this is the seam a real LLM call would replace.
    """
    risks = _content_risks(edited) + _diff_risks(original, edited)
    # Preserve order while removing exact duplicates.
    deduped = list(dict.fromkeys(risks))

    if deduped:
        suggestion = (
            "Review the flagged concern(s) and confirm them against the source "
            "documentation before approving. This assistant is advisory only and "
            "never approves or rejects on your behalf."
        )
    else:
        suggestion = (
            "No additional clinical concerns were detected in the current output. "
            "Apply your own clinical judgment before approving."
        )

    return AssistantAnalysis(
        clinical_risks=deduped,
        suggestion=suggestion,
        confidence_score=_confidence(original, edited, len(deduped)),
    )


class AssistantService:
    """Advisory analysis over a run's current output.

    Deterministic today; the ``analyze_review`` seam is async so it can later
    delegate to a real provider without touching the API or the frontend.
    """

    async def analyze_review(
        self, db: Session, run_id: UUID, edited_output: dict[str, Any]
    ) -> AssistantAnalysis:
        run = get_run(db, run_id)
        if run is None:
            raise RunNotFoundError(str(run_id))
        original = run.parsed_output or {}
        # Deterministic stand-in for an LLM reviewer call. In production this is
        # where an `await` provider request would go; the return contract is
        # unchanged.
        return analyze_edit(original=original, edited=edited_output)
