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
    app_name: str = "healthCare-monitor Backend"
    app_version: str = "0.1.0"
    service_name: str = "healthCare-monitor-backend"
    api_prefix: str = "/api"

    # Database. Defaults to a local SQLite file so the app runs from a clean
    # checkout with zero external infrastructure (ideal for local dev and demos).
    # Point DATABASE_URL at Postgres for a production-like setup — the models are
    # dialect-portable (VARCHAR+CHECK enums, generic Uuid/JSON, Python-side
    # defaults) and the same code runs on either engine.
    database_url: str = "sqlite:///./caretrace_demo.db"

    # Browser origins allowed to call the API (comma-separated). The Next.js dev
    # server runs on :3000 by default; add deployed origins here as needed.
    cors_origins: str = "http://localhost:3000"

    # Default provider selection (used by the orchestration factory)
    default_provider: str = "openai"
    default_model: str = "gpt-4o-mini"

    # OpenAI provider
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    # Ollama provider (local)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5"

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS origins as a clean list (drops blanks/whitespace)."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        """True when the configured database is SQLite (local/demo default)."""
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
