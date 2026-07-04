"""Typed enumerations for persistence models.

Enums are stored as portable `VARCHAR + CHECK` columns (``native_enum=False``)
rather than native Postgres enum types. This keeps migrations simple and avoids
duplicate-type conflicts when the same enum (e.g. Provider) is used by more than
one table.
"""

import enum

from sqlalchemy import Enum as SAEnum


class Provider(str, enum.Enum):
    """Supported LLM providers."""

    openai = "openai"
    ollama = "ollama"


class RunStatus(str, enum.Enum):
    """Terminal status of a processing run."""

    auto_saved = "auto_saved"
    needs_review = "needs_review"
    reviewed = "reviewed"
    rejected = "rejected"
    failed = "failed"


class IssueType(str, enum.Enum):
    """Category of a validation issue (unified taxonomy).

    Aligns with app.schemas.validation.IssueTypeLiteral. Describes *what kind*
    of issue occurred, not how severe it is (see ``Severity``).
    """

    schema = "schema"
    clinical = "clinical"
    completeness = "completeness"
    format = "format"


class Severity(str, enum.Enum):
    """Severity of a validation issue (unified taxonomy).

    Aligns with app.schemas.validation.SeverityLiteral. Persisting severity on
    ValidationLog (a dedicated column) is deferred to a later persistence phase;
    this enum defines the shared vocabulary now.
    """

    warning = "warning"
    critical = "critical"


class RoutingDecision(str, enum.Enum):
    """Persisted routing outcome for a run.

    Mirrors the values of the service-layer ``app.services.routing.RoutingDecision``;
    persistence bridges the two by value to keep the compute layer free of ORM
    imports (avoids the models/db bootstrap cycle).
    """

    auto_save = "auto_save"
    human_review = "human_review"
    reject = "reject"


class ReviewStatus(str, enum.Enum):
    """Human review outcome for a review item."""

    pending = "pending"
    approved = "approved"
    rejected = "rejected"


def enum_column(py_enum: type[enum.Enum]) -> SAEnum:
    """Return a portable, non-native Enum column type storing the enum value.

    No explicit constraint name is set so each table gets its own auto-named
    CHECK constraint, avoiding collisions for enums shared across tables.
    """
    return SAEnum(
        py_enum,
        native_enum=False,
        length=32,
        values_callable=lambda e: [member.value for member in e],
    )
