"""OpenAI provider (default model: gpt-4o-mini).

The OpenAI SDK and API key are only required when ``extract`` is actually
called, so constructing this provider (e.g. via the factory) is side-effect
free and does not need credentials.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.services.providers.base import (
    ExtractionProvider,
    ProviderError,
    RawCompletion,
)


class OpenAIProvider(ExtractionProvider):
    """Structured extraction via the OpenAI Chat Completions API."""

    name = "openai"

    def _complete(self, system_prompt: str, user_content: str) -> RawCompletion:
        settings = get_settings()
        if not settings.openai_api_key:
            raise ProviderError(
                "OPENAI_API_KEY is not configured.", retryable=False
            )

        # Lazy import so the providers package imports without the SDK present.
        try:
            from openai import (
                APIConnectionError,
                APIStatusError,
                APITimeoutError,
                OpenAI,
                RateLimitError,
            )
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise ProviderError(
                f"openai package is not installed: {exc}", retryable=False
            ) from exc

        client = OpenAI(api_key=settings.openai_api_key)
        try:
            response = client.chat.completions.create(
                model=self.model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            )
        except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
            raise ProviderError(str(exc), retryable=True) from exc
        except APIStatusError as exc:
            raise ProviderError(
                str(exc), retryable=exc.status_code >= 500
            ) from exc

        text = response.choices[0].message.content or ""
        usage = response.usage
        return RawCompletion(
            text=text,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
        )
