"""Search response schemas (global Ctrl+K search)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """A single run matched by the search query."""

    run_id: UUID
    status: str
    routing_decision: str | None = None
    confidence: float | None = None
    # A short transcript excerpt around the match (or the transcript head).
    snippet: str
    created_at: datetime
    # True when the run has an undecided review item — the palette labels
    # these as review-queue results.
    pending_review: bool = False


class SearchResponse(BaseModel):
    """Search results, newest first."""

    query: str
    results: list[SearchResult] = Field(default_factory=list)
