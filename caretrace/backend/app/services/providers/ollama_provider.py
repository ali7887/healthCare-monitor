"""Ollama provider (default model: qwen2.5).

Calls a local Ollama server's chat API over HTTP. Constructing the provider
does not require the server to be running; connection issues surface as a
retryable ProviderError only when ``extract`` is called.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.services.providers.base import (
    ExtractionProvider,
    ProviderError,
    RawCompletion,
)

_REQUEST_TIMEOUT_SECONDS = 120.0


class OllamaProvider(ExtractionProvider):
    """Structured extraction via a local Ollama chat endpoint."""

    name = "ollama"

    def _complete(self, system_prompt: str, user_content: str) -> RawCompletion:
        settings = get_settings()
        import httpx

        url = settings.ollama_base_url.rstrip("/") + "/api/chat"
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        }

        try:
            response = httpx.post(url, json=payload, timeout=_REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise ProviderError(
                f"Cannot reach Ollama at {url}: {exc}", retryable=True
            ) from exc
        except httpx.TimeoutException as exc:
            raise ProviderError(str(exc), retryable=True) from exc
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                str(exc), retryable=exc.response.status_code >= 500
            ) from exc

        data = response.json()
        text = data.get("message", {}).get("content", "")
        return RawCompletion(
            text=text,
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
        )
