"""Deterministic confidence scoring engine.

Computes a normalized 0.0–1.0 confidence score for a ``PipelineRunResult`` using
only signals that already exist on the result and its ``ValidationIssue`` list.
The scorer is pure: no model, no network, no database, no I/O. Every applied
penalty is recorded in a breakdown and a human-readable reasons list so the
score is fully explainable and reproducible.

Confidence is *derived* from deterministic signals — it is never taken from the
model (see DECISIONS 003).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from app.schemas.validation import ValidationIssue

if TYPE_CHECKING:
    from app.services.pipeline import PipelineRunResult

# --- Penalty weights (absolute magnitudes) ----------------------------------

_PENALTY_NOT_SUCCEEDED = 0.40
_PENALTY_NO_NOTE = 0.50
_PENALTY_RETRY = 0.15

_RETRY_TRIGGER_PENALTIES: dict[str, float] = {
    "provider_retryable_error": 0.08,
    "invalid_json": 0.15,
    "schema_validation_failed": 0.12,
}

# severity -> (per-issue penalty, absolute cap)
_SEVERITY_PENALTIES: dict[str, tuple[float, float]] = {
    "critical": (0.12, 0.48),
    "warning": (0.04, 0.24),
}

# issue_type -> (per-issue penalty, absolute cap)
_TYPE_PENALTIES: dict[str, tuple[float, float]] = {
    "schema": (0.06, 0.18),
    "format": (0.05, 0.15),
    "clinical": (0.04, 0.16),
    "completeness": (0.03, 0.12),
}

_ROUND = 4


def _capped(count: int, weight: float, cap: float) -> float:
    """Return the capped absolute penalty for a count of issues."""
    return round(min(count * weight, cap), _ROUND)


class ConfidenceBreakdown(BaseModel):
    """Inspectable, additive breakdown of the confidence computation."""

    base_score: float = 1.0
    failure_penalties: float
    retry_penalties: float
    severity_penalties: float
    type_penalties: float
    raw_score: float
    final_score: float


class ConfidenceResult(BaseModel):
    """Confidence score plus its explanation."""

    score: float
    breakdown: ConfidenceBreakdown
    reasons: list[str]


class ConfidenceScorer:
    """Pure, deterministic confidence scorer."""

    def calculate(self, run_result: PipelineRunResult) -> ConfidenceResult:
        reasons: list[str] = []

        failure_penalties = self._failure_penalties(run_result, reasons)
        retry_penalties = self._retry_penalties(run_result, reasons)
        severity_penalties = self._severity_penalties(run_result.issues, reasons)
        type_penalties = self._type_penalties(run_result.issues, reasons)

        total = failure_penalties + retry_penalties + severity_penalties + type_penalties
        raw_score = round(1.0 - total, _ROUND)
        final_score = round(max(0.0, min(1.0, raw_score)), _ROUND)

        breakdown = ConfidenceBreakdown(
            base_score=1.0,
            failure_penalties=round(failure_penalties, _ROUND),
            retry_penalties=round(retry_penalties, _ROUND),
            severity_penalties=round(severity_penalties, _ROUND),
            type_penalties=round(type_penalties, _ROUND),
            raw_score=raw_score,
            final_score=final_score,
        )
        return ConfidenceResult(score=final_score, breakdown=breakdown, reasons=reasons)

    # -- penalty groups ------------------------------------------------------

    def _failure_penalties(
        self, run_result: PipelineRunResult, reasons: list[str]
    ) -> float:
        total = 0.0
        if not run_result.succeeded:
            total += _PENALTY_NOT_SUCCEEDED
            reasons.append(f"Pipeline did not succeed: -{_PENALTY_NOT_SUCCEEDED:.2f}")
        if run_result.extracted_note is None:
            total += _PENALTY_NO_NOTE
            reasons.append(f"No clinical note was extracted: -{_PENALTY_NO_NOTE:.2f}")
        return total

    def _retry_penalties(
        self, run_result: PipelineRunResult, reasons: list[str]
    ) -> float:
        if run_result.retry_count != 1:
            return 0.0
        total = _PENALTY_RETRY
        reasons.append(f"Retry used (retry_count=1): -{_PENALTY_RETRY:.2f}")
        addon = _RETRY_TRIGGER_PENALTIES.get(run_result.retry_trigger or "")
        if addon:
            total += addon
            reasons.append(f"Retry trigger '{run_result.retry_trigger}': -{addon:.2f}")
        return total

    def _severity_penalties(
        self, issues: list[ValidationIssue], reasons: list[str]
    ) -> float:
        total = 0.0
        for severity, (weight, cap) in _SEVERITY_PENALTIES.items():
            count = sum(1 for issue in issues if issue.severity == severity)
            if not count:
                continue
            penalty = _capped(count, weight, cap)
            total += penalty
            capped = " (capped)" if count * weight > cap else ""
            reasons.append(f"{count} {severity} issue(s): -{penalty:.2f}{capped}")
        return total

    def _type_penalties(
        self, issues: list[ValidationIssue], reasons: list[str]
    ) -> float:
        total = 0.0
        for issue_type, (weight, cap) in _TYPE_PENALTIES.items():
            count = sum(1 for issue in issues if issue.issue_type == issue_type)
            if not count:
                continue
            penalty = _capped(count, weight, cap)
            total += penalty
            capped = " (capped)" if count * weight > cap else ""
            reasons.append(f"{count} {issue_type}-type issue(s): -{penalty:.2f}{capped}")
        return total
