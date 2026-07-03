"""SQLAlchemy declarative base and model registration.

All ORM models inherit from `Base` so they share a single metadata registry.
The models are imported at the end of this module so that importing
`app.db.base` (e.g. from Alembic's env or for `metadata.create_all`) registers
every table on `Base.metadata`.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all CareTrace ORM models."""


# Import models after Base is defined to populate Base.metadata while avoiding
# circular imports (models import Base from this module).
from app.models import (  # noqa: E402,F401
    EvaluationResult,
    ReviewItem,
    Run,
    ValidationLog,
)
