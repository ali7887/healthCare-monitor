"""Provider selection factory.

Resolves a provider name (``"openai"`` or ``"ollama"``) to a concrete
provider instance, using configured model defaults unless overridden. Provider
names intentionally match the values of ``app.models.enums.Provider`` without
importing it, keeping orchestration decoupled from persistence.
"""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.services.prompts import DEFAULT_PROMPT_VERSION
from app.services.providers.base import ExtractionProvider
from app.services.providers.ollama_provider import OllamaProvider
from app.services.providers.openai_provider import OpenAIProvider

SUPPORTED_PROVIDERS = ("openai", "ollama")


def _normalize(name: Any) -> str:
    value = getattr(name, "value", name)
    return str(value).strip().lower()


def get_provider(
    name: Any,
    *,
    model: str | None = None,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
) -> ExtractionProvider:
    """Return a provider instance for the given name.

    Accepts a string or any object exposing a ``.value`` (e.g. the Provider
    enum). Raises ValueError for unsupported providers.
    """
    key = _normalize(name)
    settings = get_settings()

    if key == "openai":
        return OpenAIProvider(
            model=model or settings.openai_model,
            prompt_version=prompt_version,
        )
    if key == "ollama":
        return OllamaProvider(
            model=model or settings.ollama_model,
            prompt_version=prompt_version,
        )

    raise ValueError(
        f"Unknown provider {name!r}. Supported providers: {SUPPORTED_PROVIDERS}."
    )
