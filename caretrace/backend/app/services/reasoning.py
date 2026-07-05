"""Deterministic, human-readable reasoning summaries for a run's routing outcome.

The summary explains *why* a run was auto-saved, flagged, or rejected as a short
ordered sequence of steps. It is derived deterministically from the same signals
the routing engine used (validation issues + derived confidence) — the model is
never asked to narrate its own reasoning. Shared by the live pipeline
(``persist_run``) and the demo seed so both produce identical, honest text.
"""

from __future__ import annotations

# A single validation issue as (severity, message, rule_id).
Issue = tuple[str, str, "str | None"]

_REVIEW_LOW = 0.50
_AUTO_SAVE = 0.85


def _fmt_conf(confidence: float | None) -> str:
    return f"{confidence:.2f}" if confidence is not None else "n/a"


def _describe(issue: Issue | None, fallback: str) -> str:
    if issue is None:
        return fallback
    _, message, rule_id = issue
    return f"'{message}'" + (f" ({rule_id})" if rule_id else "")


def build_reasoning_summary(
    *,
    succeeded: bool,
    decision: str | None,
    confidence: float | None,
    issues: list[Issue],
) -> str:
    """Return a newline-separated 'Step N: ...' reasoning summary.

    ``decision`` is a routing value: ``auto_save`` / ``human_review`` / ``reject``.
    ``issues`` are (severity, message, rule_id) tuples; criticals are preferred
    when choosing the issue to highlight.
    """
    conf = _fmt_conf(confidence)

    if not succeeded:
        return (
            "Step 1: Requested structured extraction from the transcript.\n"
            "Step 2: The model response could not be parsed into a valid clinical "
            "note, even after one self-correction retry.\n"
            "Step 3: No structured output was produced, so no confidence could be derived.\n"
            "Step 4: Routed out (reject) and recorded as failed."
        )

    critical = [i for i in issues if i[0] == "critical"]
    highlighted = (critical or issues or [None])[0]

    if decision == "auto_save":
        return (
            "Step 1: Extraction parsed and passed schema validation.\n"
            "Step 2: Deterministic clinical rules found no policy violations.\n"
            f"Step 3: Derived confidence {conf} met the auto-save threshold "
            f"(≥ {_AUTO_SAVE:.2f}).\n"
            "Step 4: Saved automatically; no human review required."
        )

    if decision == "human_review":
        issue_text = _describe(highlighted, "a potential inconsistency")
        return (
            "Step 1: Extraction parsed and passed schema validation.\n"
            f"Step 2: Clinical validation flagged {issue_text}.\n"
            f"Step 3: Derived confidence {conf} fell in the review band "
            f"({_REVIEW_LOW:.2f}–{_AUTO_SAVE:.2f}).\n"
            "Step 4: Routed to human review for a clinician's decision."
        )

    # reject (with a produced note, e.g. a critical clinical issue or very low score)
    issue_text = _describe(highlighted, "a critical inconsistency")
    return (
        "Step 1: Extraction parsed successfully.\n"
        f"Step 2: A critical clinical issue was detected: {issue_text}.\n"
        f"Step 3: Derived confidence {conf} was below the safe-save threshold.\n"
        "Step 4: Routed out of auto-save (reject)."
    )
