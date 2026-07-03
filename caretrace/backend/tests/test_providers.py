"""Focused, no-network tests for the AI orchestration layer.

These verify the orchestration contract (result shape, timing, cost, error
normalization) and the factory/prompt registry without any live provider call.
"""

import pytest

from app.services.prompts import DEFAULT_PROMPT_VERSION, load_prompt
from app.services.providers import (
    ExtractionProvider,
    ExtractionResult,
    OllamaProvider,
    OpenAIProvider,
    ProviderError,
    RawCompletion,
    get_provider,
)


class _FakeProvider(ExtractionProvider):
    name = "openai"

    def _complete(self, system_prompt: str, user_content: str) -> RawCompletion:
        assert system_prompt  # prompt was loaded and passed through
        return RawCompletion(text="```json\n{\"ok\": true}\n```", prompt_tokens=10, completion_tokens=5)


class _FailingProvider(ExtractionProvider):
    name = "openai"

    def _complete(self, system_prompt: str, user_content: str) -> RawCompletion:
        raise ProviderError("boom", retryable=True)


def test_prompt_loads_with_version():
    prompt = load_prompt()
    assert prompt.version == DEFAULT_PROMPT_VERSION == "clinical-extraction-v1"
    assert prompt.system.strip()


def test_unknown_prompt_version_raises():
    with pytest.raises(KeyError):
        load_prompt("does-not-exist")


def test_factory_returns_correct_types():
    assert isinstance(get_provider("openai"), OpenAIProvider)
    assert isinstance(get_provider("ollama"), OllamaProvider)


def test_factory_accepts_enum_like_and_overrides_model():
    class _EnumLike:
        value = "openai"

    provider = get_provider(_EnumLike(), model="gpt-4o-mini")
    assert isinstance(provider, OpenAIProvider)
    assert provider.model == "gpt-4o-mini"


def test_factory_rejects_unknown_provider():
    with pytest.raises(ValueError):
        get_provider("anthropic")


def test_successful_extract_normalizes_result():
    result = _FakeProvider(model="gpt-4o-mini").extract("transcript text")
    assert isinstance(result, ExtractionResult)
    assert result.succeeded
    assert result.provider == "openai"
    assert result.model == "gpt-4o-mini"
    assert result.prompt_version == "clinical-extraction-v1"
    assert result.raw_response_text == '```json\n{"ok": true}\n```'
    assert result.content == '{"ok": true}'  # code fences stripped
    assert result.estimated_cost > 0
    assert result.latency_ms is not None and result.latency_ms >= 0
    assert result.retryable_error is False


def test_failed_extract_captures_error_without_raising():
    result = _FailingProvider(model="gpt-4o-mini").extract("transcript text")
    assert not result.succeeded
    assert result.error == "boom"
    assert result.retryable_error is True
    assert result.raw_response_text is None
    assert result.estimated_cost == 0.0
