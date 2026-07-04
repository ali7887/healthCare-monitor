"""Versioned prompt registry.

Prompts are stored as plain files under ``healthCare-monitor/backend/prompts`` and loaded
by an explicit version identifier. Keeping prompts on disk (rather than inline
strings) makes them inspectable, auditable, and easy to version over time.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# healthCare-monitor/backend/prompts  (this file is app/services/prompts.py)
PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"

DEFAULT_PROMPT_VERSION = "clinical-extraction-v1"

# Map stable version identifiers to prompt files.
_PROMPT_FILES: dict[str, str] = {
    "clinical-extraction-v1": "clinical_extraction_v1.md",
}


@dataclass(frozen=True)
class Prompt:
    """A loaded prompt and its version identifier."""

    version: str
    system: str


def available_versions() -> list[str]:
    """Return the known prompt version identifiers."""
    return sorted(_PROMPT_FILES)


def load_prompt(version: str = DEFAULT_PROMPT_VERSION) -> Prompt:
    """Load a prompt by version identifier.

    Raises KeyError if the version is unknown and FileNotFoundError if the
    registered file is missing.
    """
    if version not in _PROMPT_FILES:
        raise KeyError(
            f"Unknown prompt version {version!r}. "
            f"Available: {available_versions()}"
        )
    path = PROMPT_DIR / _PROMPT_FILES[version]
    system = path.read_text(encoding="utf-8").strip()
    return Prompt(version=version, system=system)
