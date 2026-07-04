"""Shared FastAPI dependencies.

``get_db`` yields a database session; ``get_pipeline`` provides the processing
pipeline. Both are overridable in tests via ``app.dependency_overrides`` (e.g.
to inject a stub provider or an in-memory database).
"""

from __future__ import annotations

from app.db.session import get_db  # re-exported for convenience
from app.services.pipeline import ProcessingPipeline

__all__ = ["get_db", "get_pipeline"]


def get_pipeline() -> ProcessingPipeline:
    """Provide a processing pipeline (default provider factory)."""
    return ProcessingPipeline()
