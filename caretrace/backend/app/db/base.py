"""SQLAlchemy declarative base.

All ORM models inherit from ``Base`` so they share a single metadata registry.

Note: this module intentionally does NOT import the model modules. Doing so
created a fragile import cycle (base -> models -> base) that only resolved when
``app.db.base`` happened to be imported first. To register every table on
``Base.metadata`` (for Alembic autogenerate or ``metadata.create_all``), import
the ``app.models`` package explicitly (e.g. ``import app.models``); the Alembic
env and the app's service imports do this.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all healthCare-monitor ORM models."""
