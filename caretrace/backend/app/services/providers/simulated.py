"""Simulated extraction provider — demo / dry-run mode.

Produces a deterministic, schema-shaped clinical note from the transcript
using a handful of local regexes: no network, no credentials, zero cost. The
output flows through the exact same downstream machinery as a real model call
(schema validation, clinical rules, derived confidence, routing), so demo mode
still demonstrates the reliability pipeline honestly — including flagged and
rejected outcomes for out-of-range vitals.

Selected by the provider factory when ``DEMO_MODE=true``, when the OpenAI key
is missing, or when the local Ollama server is unreachable (see ``factory``).
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.services.providers.base import ExtractionProvider, RawCompletion

# Extraction patterns are deliberately simple and case-insensitive. They cover
# the bundled examples/ transcripts and typical dictation phrasing; anything
# they miss simply becomes a completeness warning downstream — which is the
# honest behavior for an extractor.
# Keyword is case-insensitive, but the captured name must stay capitalized —
# a fully IGNORECASE pattern would capture ordinary lowercase words.
_NAME_RE = re.compile(
    r"(?:[Pp]atient|[Nn]ote for|for)\s+([A-Z][a-zA-Z]+ [A-Z][a-zA-Z]+)"
)
_AGE_RE = re.compile(r"(\d{1,3})\s*(?:years?\s*old|y/?o)", re.IGNORECASE)
_BP_RE = re.compile(
    r"(?:blood pressure|bp)\D{0,20}?(\d{2,3})\s*(?:/|over)\s*(\d{2,3})", re.IGNORECASE
)
_HR_RE = re.compile(r"(?:heart rate|pulse)\D{0,15}?(\d{1,3})", re.IGNORECASE)
_TEMP_RE = re.compile(r"temp(?:erature)?\D{0,15}?(\d{2}(?:\.\d)?)", re.IGNORECASE)
_SPO2_RE = re.compile(
    r"(?:spo2|oxygen saturation|sats?)\D{0,15}?(\d{2,3})", re.IGNORECASE
)
_MED_WITH_DOSE_RE = re.compile(
    r"\b([A-Z][a-z]{3,})\s+(\d+(?:\.\d+)?\s?(?:mg|mcg|g|ml)\b)"
)
_MED_NAMED_RE = re.compile(
    r"(?:administered|prescribed|given|gave(?: him| her)?(?: his| her)?)\s+"
    r"(?:prescribed\s+)?([A-Z][a-z]{3,})"
)
_ORAL_RE = re.compile(r"\borally\b|\bby mouth\b|\boral\b", re.IGNORECASE)
_SYMPTOM_KEYWORDS = (
    "dizziness",
    "headache",
    "nausea",
    "shortness of breath",
    "short of breath",
    "vomiting",
    "pain",
    "weak",
)


def _first_sentence(text: str, limit: int = 140) -> str:
    sentence = text.strip().split(".")[0].strip()
    return sentence[:limit] if sentence else text.strip()[:limit]


def simulate_note(transcript: str) -> dict[str, Any]:
    """Deterministically derive a ClinicalNote-shaped dict from a transcript."""
    note: dict[str, Any] = {"source_language": "en"}

    patient: dict[str, Any] = {}
    if name := _NAME_RE.search(transcript):
        patient["name"] = name.group(1)
    if age := _AGE_RE.search(transcript):
        patient["age"] = int(age.group(1))
    if patient:
        note["patient"] = patient

    vitals: dict[str, Any] = {}
    if bp := _BP_RE.search(transcript):
        vitals["blood_pressure"] = {
            "systolic": int(bp.group(1)),
            "diastolic": int(bp.group(2)),
            "unit": "mmHg",
        }
    if hr := _HR_RE.search(transcript):
        vitals["heart_rate"] = {"value": int(hr.group(1)), "unit": "bpm"}
    if temp := _TEMP_RE.search(transcript):
        vitals["temperature"] = {"value": float(temp.group(1)), "unit": "C"}
    if spo2 := _SPO2_RE.search(transcript):
        vitals["spo2"] = {"value": int(spo2.group(1)), "unit": "%"}
    if vitals:
        note["vitals"] = vitals

    route = "oral" if _ORAL_RE.search(transcript) else None
    medications: list[dict[str, Any]] = []
    for med_name, dose in _MED_WITH_DOSE_RE.findall(transcript):
        medications.append(
            {"name": med_name, "dose": dose.replace(" ", ""), "route": route}
        )
    seen = {med["name"] for med in medications}
    for med_name in _MED_NAMED_RE.findall(transcript):
        if med_name not in seen and not _looks_like_common_word(med_name):
            medications.append({"name": med_name, "dose": None, "route": route})
            seen.add(med_name)
    if medications:
        note["medications"] = medications

    lowered = transcript.lower()
    symptoms = [
        {"text": keyword} for keyword in _SYMPTOM_KEYWORDS if keyword in lowered
    ]
    if symptoms:
        note["symptoms"] = symptoms

    note["note_summary"] = _first_sentence(transcript)
    return note


# Capitalized sentence-starters that the "administered/given X" pattern could
# mistake for medication names.
_COMMON_WORDS = {"Patient", "Nurse", "Blood", "Heart", "Doctor", "After"}


def _looks_like_common_word(word: str) -> bool:
    return word in _COMMON_WORDS


class SimulatedProvider(ExtractionProvider):
    """Deterministic local extraction, packaged as a normal provider.

    Only ``_complete`` is overridden, so timing, cost (0.0 — the model name is
    unknown to the pricing table), and result normalization behave exactly like
    every other provider.
    """

    name = "simulated"

    def _complete(self, system_prompt: str, user_content: str) -> RawCompletion:
        note = simulate_note(user_content)
        return RawCompletion(text=json.dumps(note))
