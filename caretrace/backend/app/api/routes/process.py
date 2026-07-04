"""Processing endpoint: run a transcript through the pipeline and persist it."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_pipeline
from app.models import Run
from app.schemas.process import ProcessRequest, ProcessResponse
from app.services.persistence import persist_run
from app.services.pipeline import PipelineRunResult, ProcessingPipeline

router = APIRouter(tags=["process"])


def _to_response(run: Run, result: PipelineRunResult) -> ProcessResponse:
    return ProcessResponse(
        run_id=run.id,
        status=run.status.value,
        provider=run.provider.value,
        prompt_version=result.final_response.prompt_version,
        note=result.extracted_note,
        issues=result.issues,
        retry_used=run.retry_count > 0,
        confidence=run.confidence,
        latency_ms=run.latency_ms,
        estimated_cost_usd=run.cost,
        created_at=run.created_at,
        routing_decision=run.routing_decision.value if run.routing_decision else None,
        routing_reason=run.routing_reason,
        confidence_breakdown=run.confidence_breakdown,
    )


@router.post("/process", response_model=ProcessResponse)
def process(
    payload: ProcessRequest,
    db: Session = Depends(get_db),
    pipeline: ProcessingPipeline = Depends(get_pipeline),
) -> ProcessResponse:
    """Process a transcript and persist the run (and any review item)."""
    result = pipeline.run(payload.transcript, payload.provider, model=payload.model)
    run = persist_run(
        db,
        transcript=payload.transcript,
        provider_name=payload.provider,
        result=result,
    )
    return _to_response(run, result)
