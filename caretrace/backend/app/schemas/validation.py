"""Validation issue schema (structure only).

This defines the shape a deterministic validator will emit in Phase 5; it
contains no rules or logic. See docs/API.md for the API-level `ValidationIssue`;
this Phase 4 shape is purpose-built for deterministic validation and dashboard
metrics (via ``rule_id``) and is the reconciliation target noted in
project_status.md.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SeverityLiteral = Literal["warning", "critical"]
IssueTypeLiteral = Literal["schema", "clinical", "completeness", "format"]


class ValidationIssue(BaseModel):
    """A single deterministic validation finding."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "severity": "critical",
                "issue_type": "clinical",
                "field_path": "vitals.blood_pressure.systolic",
                "message": "Systolic BP 320 mmHg is outside the plausible range.",
                "rule_id": "vitals.bp.systolic.range",
            }
        },
    )

    severity: SeverityLiteral
    issue_type: IssueTypeLiteral
    field_path: str | None = Field(
        default=None,
        description="Dotted path to the offending field, e.g. 'vitals.heart_rate.value'.",
    )
    message: str
    rule_id: str | None = Field(
        default=None,
        description="Stable rule identifier used for metrics and dashboards.",
    )
