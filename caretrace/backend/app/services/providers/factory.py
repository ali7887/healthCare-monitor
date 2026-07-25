"""Provider selection factory.

Resolves a provider name (``"openai"`` or ``"ollama"``) to a concrete
provider instance, using configured model defaults unless overridden. Provider
names intentionally match the values of ``app.models.enums.Provider`` without
importing it, keeping orchestration decoupled from persistence.
"""

from __future__ import annotations

from typing import Any

from app.core.config import Settings, get_settings
from app.core.logging import get_logger, log_event
from app.services.prompts import DEFAULT_PROMPT_VERSION
from app.services.providers.base import ExtractionProvider
from app.services.providers.ollama_provider import OllamaProvider
from app.services.providers.openai_provider import OpenAIProvider
from app.services.providers.simulated import SimulatedProvider

SUPPORTED_PROVIDERS = ("openai", "ollama")

_logger = get_logger("providers")

# How long to wait for the local Ollama server before falling back to the
# simulator. Short on purpose: a demo must not hang on a dead socket.
_OLLAMA_PROBE_TIMEOUT_S = 0.75


def _normalize(name: Any) -> str:
    value = getattr(name, "value", name)
    return str(value).strip().lower()


def _openai_available(settings: Settings) -> bool:
    """OpenAI is usable when an API key is configured."""
    return bool(settings.openai_api_key)


def _ollama_available(settings: Settings) -> bool:
    """Quick reachability probe of the local Ollama server."""
    import httpx

    try:
        httpx.get(settings.ollama_base_url, timeout=_OLLAMA_PROBE_TIMEOUT_S)
        return True
    except Exception:
        return False


def _simulated(prompt_version: str, *, reason: str) -> SimulatedProvider:
    log_event(_logger, "simulated_provider_selected", reason=reason)
    return SimulatedProvider(model="simulated", prompt_version=prompt_version)


def get_provider(
    name: Any,
    *,
    model: str | None = None,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
) -> ExtractionProvider:
    """Return a provider instance for the given name.

    Accepts a string or any object exposing a ``.value`` (e.g. the Provider
    enum). Raises ValueError for unsupported providers.

    Demo safety: when ``DEMO_MODE=true``, when the OpenAI key is missing, or
    when the local Ollama server is unreachable, the deterministic
    ``SimulatedProvider`` is returned instead — a demo or local checkout must
    process transcripts, never error on absent credentials/servers.
    """
    key = _normalize(name)
    if key not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"Unknown provider {name!r}. Supported providers: {SUPPORTED_PROVIDERS}."
        )

    settings = get_settings()
    if settings.demo_mode:
        return _simulated(prompt_version, reason="demo_mode")

    if key == "openai":
        if not _openai_available(settings):
            return _simulated(prompt_version, reason="openai_key_missing")
        return OpenAIProvider(
            model=model or settings.openai_model,
            prompt_version=prompt_version,
        )

    if not _ollama_available(settings):
        return _simulated(prompt_version, reason="ollama_unreachable")
    return OllamaProvider(
        model=model or settings.ollama_model,
        prompt_version=prompt_version,
    )
