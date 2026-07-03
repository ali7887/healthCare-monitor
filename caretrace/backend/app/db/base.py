"""SQLAlchemy declarative base.

All future ORM models (Run, ValidationLog, ReviewItem, EvaluationResult)
will inherit from `Base` so they share a single metadata registry. No models
are defined in Phase 1.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all CareTrace ORM models."""
