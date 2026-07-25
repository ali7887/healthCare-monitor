"""Evaluation endpoints: aggregated reliability metrics + downloadable export."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.logging import get_logger, log_event
from app.schemas.evaluation import EvaluationResponse
from app.services.persistence import get_evaluation_rows, get_evaluation_summary

router = APIRouter(prefix="/evaluation", tags=["evaluation"])

_logger = get_logger("evaluation")

# Stable column order for the CSV export (matches the JSON row keys).
_EXPORT_COLUMNS = (
    "run_id",
    "provider",
    "status",
    "routing_decision",
    "confidence",
    "retry_count",
    "warnings_count",
    "latency_ms",
    "cost_usd",
    "created_at",
)


@router.get("", response_model=EvaluationResponse)
def evaluation(db: Session = Depends(get_db)) -> EvaluationResponse:
    """Aggregated reliability metrics: status totals + provider comparison."""
    summary = get_evaluation_summary(db)
    log_event(_logger, "evaluation_fetch", total_runs=summary["totals"]["runs"])
    return EvaluationResponse(**summary)


@router.get("/export")
def export_evaluation(
    format: Literal["json", "csv"] = Query(default="json"),
    db: Session = Depends(get_db),
) -> Response:
    """Download the evaluation dataset for external analysis.

    JSON carries the aggregate summary plus one metrics row per run; CSV is
    the per-run rows only. Rows contain scalar metrics exclusively — no
    transcripts or clinical payloads leave the system via this export.
    """
    rows = get_evaluation_rows(db)
    generated_at = datetime.now(timezone.utc)
    filename = f"caretrace-evaluation-{generated_at.date().isoformat()}.{format}"
    log_event(_logger, "evaluation_export", format=format, row_count=len(rows))

    if format == "csv":
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=_EXPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
        body: str = buffer.getvalue()
        media_type = "text/csv"
    else:
        body = json.dumps(
            {
                "generated_at": generated_at.isoformat(),
                "summary": get_evaluation_summary(db),
                "runs": rows,
            },
            indent=2,
        )
        media_type = "application/json"

    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
