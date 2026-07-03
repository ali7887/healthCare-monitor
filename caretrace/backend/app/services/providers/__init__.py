"""AI orchestration provider layer.

Public surface for structured-extraction providers: a shared result type, the
provider abstraction, concrete implementations, and a selection factory.
"""

from app.services.providers.base import (
    ExtractionProvider,
    ExtractionResult,
    ProviderError,
    RawCompletion,
)
from app.services.providers.factory import SUPPORTED_PROVIDERS, get_provider
from app.services.providers.ollama_provider import OllamaProvider
from app.services.providers.openai_provider import OpenAIProvider

__all__ = [
    "ExtractionProvider",
    "ExtractionResult",
    "ProviderError",
    "RawCompletion",
    "OpenAIProvider",
    "OllamaProvider",
    "get_provider",
    "SUPPORTED_PROVIDERS",
]
