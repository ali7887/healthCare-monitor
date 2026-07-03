"""Environment-based application settings.

Settings are loaded from environment variables (and an optional local `.env`
file) using Pydantic v2 settings. Values are read lazily via `get_settings()`
so importing this module never requires the environment to be fully configured.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration.

    Field names map to environment variables case-insensitively, e.g.
    `DATABASE_URL` -> `database_url`.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application metadata
    app_name: str = "CareTrace Backend"
    app_version: str = "0.1.0"
    service_name: str = "caretrace-backend"
    api_prefix: str = "/api"

    # Database (Postgres-ready; not connected until a session is opened)
    database_url: str = (
        "postgresql+psycopg://caretrace:caretrace@localhost:5432/caretrace"
    )

    # Default provider selection (used by the orchestration factory)
    default_provider: str = "openai"
    default_model: str = "gpt-4o-mini"

    # OpenAI provider
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    # Ollama provider (local)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
