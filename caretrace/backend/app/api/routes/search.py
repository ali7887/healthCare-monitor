"""Global search endpoint backing the Ctrl+K command palette."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.logging import get_logger, log_event
from app.models import Run
from app.schemas.search import SearchResponse, SearchResult
from app.services.persistence import pending_review_id, search_runs

router = APIRouter(prefix="/search", tags=["search"])

_logger = get_logger("search")

_SNIPPET_RADIUS = 48


def _snippet(transcript: str, query: str) -> str:
    """A short excerpt centered on the first match (or the transcript head)."""
    lowered = transcript.lower()
    index = lowered.find(query.lower())
    if index < 0:
        head = transcript[: _SNIPPET_RADIUS * 2].strip()
        return head + ("…" if len(transcript) > len(head) else "")
    start = max(0, index - _SNIPPET_RADIUS)
    end = min(len(transcript), index + len(query) + _SNIPPET_RADIUS)
    excerpt = transcript[start:end].strip()
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(transcript) else ""
    return f"{prefix}{excerpt}{suffix}"


@router.get("", response_model=SearchResponse)
def search(
    q: str = Query(min_length=2, max_length=200),
    limit: int = Query(default=10, ge=1, le=25),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """Search runs by transcript text, run-id prefix, or routing reason.

    Runs with a pending review item are flagged so the palette can present
    them as review-queue results.
    """
    runs = search_runs(db, query=q, limit=limit)
    # PHI-safe telemetry: only the query length and hit count, never the text.
    log_event(_logger, "search_query", query_length=len(q), result_count=len(runs))
    return SearchResponse(
        query=q,
        results=[
            SearchResult(
                run_id=run.id,
                status=run.status.value,
                routing_decision=(
                    run.routing_decision.value if run.routing_decision else None
                ),
                confidence=run.confidence,
                snippet=_snippet(run.transcript, q),
                created_at=run.created_at,
                pending_review=pending_review_id(run) is not None,
            )
            for run in runs
        ],
    )
