"""DTOs for the AI Reviewer Assistant (advisory differential analysis).

The assistant is *advisory only*: it inspects the reviewer's current structured
output for potential clinical risks and returns a suggestion and a synthetic
confidence. It never approves, rejects, or mutates a run — those decisions stay
with the human reviewer.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AssistantAnalyzeRequest(BaseModel):
    """The reviewer's current structured output to analyze.

    ``edited_output`` must be a JSON object; a non-object payload (list, string)
    is rejected at the contract boundary with a 422.
    """

    model_config = ConfigDict(extra="forbid")

    edited_output: dict[str, Any] = Field(
        description="The reviewer's current or edited structured output to analyze."
    )


class AssistantAnalysisResponse(BaseModel):
    """Advisory analysis of the current output."""

    clinical_risks: list[str] = Field(default_factory=list)
    suggestion: str
    confidence_score: float
