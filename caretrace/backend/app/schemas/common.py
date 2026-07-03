"""Shared type aliases for the schema layer.

These Literals mirror the vocabularies defined in docs/API.md shared types and
in app.models.enums, kept here as plain typing aliases so the schema layer does
not import the ORM.
"""

from __future__ import annotations

from typing import Literal

# A numeric value that may be an integer or a float. Range checks are a Phase 5
# concern; here we only constrain the type.
Number = int | float

# Matches app.models.enums.Provider values and docs/API.md `Provider`.
ProviderLiteral = Literal["openai", "ollama"]

# Matches app.models.enums.RunStatus values and docs/API.md `Status`.
RunStatusLiteral = Literal[
    "auto_saved",
    "needs_review",
    "reviewed",
    "rejected",
    "failed",
]
