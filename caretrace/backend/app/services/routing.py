"""Deterministic routing engine.

Maps a confidence score plus validation state to one of three decisions. Pure
and side-effect free — persistence of review items lives in
``app.services.persistence`` (DB), not here.

Routing thresholds:
- AUTO_SAVE    : score >= 0.85 AND no critical issues
- HUMAN_REVIEW : 0.50 <= score < 0.85, OR score >= 0.85 with >=1 critical issue
- REJECT       : score < 0.50
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.services.confidence import ConfidenceResult
    from app.services.pipeline import PipelineRunResult

AUTO_SAVE_THRESHOLD = 0.85
REJECT_THRESHOLD = 0.50


class RoutingDecision(str, Enum):
    """Where a processed run should go next (service-layer enum).

    Values mirror ``app.models.enums.RoutingDecision``; persistence bridges the
    two by value.
    """

    AUTO_SAVE = "auto_save"
    HUMAN_REVIEW = "human_review"
    REJECT = "reject"


class RoutingResult(BaseModel):
    """Outcome of the routing decision, with an inspectable reason."""

    decision: RoutingDecision
    confidence_score: float
    routing_reason: str


class RoutingEngine:
    """Pure, deterministic router. No side effects."""

    def route(
        self, run_result: PipelineRunResult, confidence: ConfidenceResult
    ) -> RoutingResult:
        score = confidence.score
        critical_count = sum(
            1 for issue in run_result.issues if issue.severity == "critical"
        )

        if score < REJECT_THRESHOLD:
            decision = RoutingDecision.REJECT
            reason = f"Score {score:.2f} below {REJECT_THRESHOLD:.2f} -> REJECT"
        elif score >= AUTO_SAVE_THRESHOLD and critical_count == 0:
            decision = RoutingDecision.AUTO_SAVE
            reason = f"Score {score:.2f} with 0 critical issues -> AUTO_SAVE"
        elif score >= AUTO_SAVE_THRESHOLD:
            decision = RoutingDecision.HUMAN_REVIEW
            reason = (
                f"Score {score:.2f} but contains {critical_count} critical "
                f"issue(s) -> HUMAN_REVIEW"
            )
        else:
            decision = RoutingDecision.HUMAN_REVIEW
            reason = (
                f"Score {score:.2f} in review band "
                f"[{REJECT_THRESHOLD:.2f}, {AUTO_SAVE_THRESHOLD:.2f}) -> HUMAN_REVIEW"
            )

        return RoutingResult(
            decision=decision, confidence_score=score, routing_reason=reason
        )
