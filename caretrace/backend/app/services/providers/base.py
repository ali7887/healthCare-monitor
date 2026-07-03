"""Provider abstraction and the shared orchestration result.

Every provider implements the same template: load the versioned prompt, call
the model, measure latency, estimate cost, and normalize the outcome into a
single ``ExtractionResult``. Providers implement only the low-level
``_complete`` call; the base class owns timing, cost, and error normalization
so all providers behave identically from the caller's perspective.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from time import perf_counter

from app.services.prompts import DEFAULT_PROMPT_VERSION, load_prompt
from app.services.providers.pricing import estimate_cost

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class ProviderError(Exception):
    """A provider call failed.

    ``retryable`` signals whether a later phase's retry loop may reasonably
    attempt the call again (e.g. timeouts, connection errors, 5xx, rate limits)
    versus a permanent failure (e.g. missing API key, malformed request).
    """

    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True)
class RawCompletion:
    """Low-level provider output, before orchestration normalization."""

    text: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


@dataclass(frozen=True)
class ExtractionResult:
    """Standardized result returned by every provider call.

    Carries all fields required for later trace persistence. This layer does
    not validate or parse the model output into a clinical schema; it only
    normalizes and preserves it.
    """

    provider: str
    model: str
    prompt_version: str
    raw_response_text: str | None
    content: str | None
    latency_ms: int | None
    estimated_cost: float
    retryable_error: bool
    error: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None

    @property
    def succeeded(self) -> bool:
        return self.error is None


def _strip_code_fences(text: str) -> str:
    """Remove surrounding markdown code fences from a JSON-ish string."""
    stripped = text.strip()
    stripped = _FENCE_RE.sub("", stripped)
    return stripped.strip()


class ExtractionProvider(ABC):
    """Abstract base for structured-extraction providers.

    Subclasses set ``name`` and implement ``_complete``. Construction is cheap
    and must not require credentials or a reachable server, so factories can
    build providers without side effects.
    """

    name: str = "base"

    def __init__(
        self, model: str, prompt_version: str = DEFAULT_PROMPT_VERSION
    ) -> None:
        self.model = model
        self.prompt_version = prompt_version

    def extract(self, transcript: str) -> ExtractionResult:
        """Run structured extraction and return a normalized result.

        Never raises for provider failures; failures are captured in the
        returned ``ExtractionResult`` (``error`` set, ``retryable_error`` flag).
        """
        prompt = load_prompt(self.prompt_version)
        start = perf_counter()
        try:
            completion = self._complete(prompt.system, transcript)
        except ProviderError as exc:
            latency_ms = int((perf_counter() - start) * 1000)
            return ExtractionResult(
                provider=self.name,
                model=self.model,
                prompt_version=self.prompt_version,
                raw_response_text=None,
                content=None,
                latency_ms=latency_ms,
                estimated_cost=0.0,
                retryable_error=exc.retryable,
                error=str(exc),
            )

        latency_ms = int((perf_counter() - start) * 1000)
        cost = estimate_cost(
            self.model, completion.prompt_tokens, completion.completion_tokens
        )
        return ExtractionResult(
            provider=self.name,
            model=self.model,
            prompt_version=self.prompt_version,
            raw_response_text=completion.text,
            content=_strip_code_fences(completion.text),
            latency_ms=latency_ms,
            estimated_cost=cost,
            retryable_error=False,
            error=None,
            prompt_tokens=completion.prompt_tokens,
            completion_tokens=completion.completion_tokens,
        )

    @abstractmethod
    def _complete(self, system_prompt: str, user_content: str) -> RawCompletion:
        """Perform the raw model call. Raise ProviderError on failure."""
        raise NotImplementedError
