"""Environment-based application settings.

Settings are loaded from environment variables (and an optional local `.env`
file) using Pydantic v2 settings. Values are read lazily via `get_settings()`
so importing this module never requires the environment to be fully configured.
"""

import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Recognised deployment modes. `dev` is the local default; `demo` is a public
# demo instance (deterministic seeded data, optional reseed); `production` is a
# real deployment (external database, migrations owned by Alembic).
ENV_DEV = "dev"
ENV_DEMO = "demo"
ENV_PRODUCTION = "production"
_KNOWN_ENVS = {ENV_DEV, ENV_DEMO, ENV_PRODUCTION}


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

    # Deployment mode: dev | demo | production. Read from `CARETRACE_ENV`.
    # Only affects operational concerns (logging profile, boot-time seeding);
    # the request/validation logic is identical across modes.
    caretrace_env: str = ENV_DEV

    # When true, the app seeds the deterministic demo dataset on startup *if the
    # database is empty*. Read from `CARETRACE_DEMO_SEED` (accepts 1/true/yes).
    # Off by default so a real production database is never touched implicitly.
    caretrace_demo_seed: bool = False

    # Log level for the structured application logger. Read from
    # `CARETRACE_LOG_LEVEL` (e.g. DEBUG, INFO, WARNING). Falls back to INFO when
    # unset or unrecognised.
    caretrace_log_level: str = "INFO"

    # Database. Defaults to a local SQLite file so the app runs from a clean
    # checkout with zero external infrastructure (ideal for local dev and demos).
    # Point DATABASE_URL at Postgres for a production-like setup — the models are
    # dialect-portable (VARCHAR+CHECK enums, generic Uuid/JSON, Python-side
    # defaults) and the same code runs on either engine.
    database_url: str = "sqlite:///./caretrace_demo.db"

    # Browser origins allowed to call the API (comma-separated). The Next.js dev
    # server runs on :3000 by default; add deployed origins here as needed.
    cors_origins: str = "http://localhost:3000"

    # Optional regex of additional allowed origins, applied *in addition to*
    # `cors_origins`. Read from `CORS_ORIGIN_REGEX`. Useful for Vercel preview
    # deployments, whose subdomain changes per branch/commit, e.g.
    #   ^https://caretrace-frontend-[a-z0-9-]+\.vercel\.app$
    # Left unset (None) by default, so behaviour is unchanged for local/demo.
    cors_origin_regex: str | None = None

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

    @property
    def env(self) -> str:
        """Normalised deployment mode, one of dev|demo|production.

        Unknown values fall back to `dev` so a typo can never silently enable
        production behaviour.
        """
        value = self.caretrace_env.strip().lower()
        return value if value in _KNOWN_ENVS else ENV_DEV

    @property
    def is_production(self) -> bool:
        """True when running as a real production deployment."""
        return self.env == ENV_PRODUCTION

    @property
    def is_demo(self) -> bool:
        """True when running as a public demo instance."""
        return self.env == ENV_DEMO

    @property
    def is_dev(self) -> bool:
        """True when running locally in development (the default)."""
        return self.env == ENV_DEV

    @property
    def demo_seed_enabled(self) -> bool:
        """True when the deterministic demo dataset should be seeded on boot."""
        return bool(self.caretrace_demo_seed)

    @property
    def log_level(self) -> int:
        """Resolve the configured log level to a stdlib ``logging`` constant.

        Defaults to INFO when the value is unset or not a recognised level name.
        """
        resolved = logging.getLevelName(self.caretrace_log_level.strip().upper())
        return resolved if isinstance(resolved, int) else logging.INFO


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
