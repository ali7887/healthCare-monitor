"""Phase 23 — production readiness: config modes, health, and readiness.

Covers the deployment-facing surface added in Phase 23: the environment/mode
resolution and log-level handling on ``Settings``, and the ``/health`` +
``/ready`` platform probes.
"""

from __future__ import annotations

import logging

from app.core.config import Settings


# --- configuration: deployment modes ---------------------------------------


def test_env_defaults_to_dev():
    assert Settings().env == "dev"
    assert Settings().is_dev is True
    assert Settings().is_production is False
    assert Settings().is_demo is False


def test_env_recognises_production_and_demo():
    prod = Settings(caretrace_env="production")
    assert prod.env == "production"
    assert prod.is_production is True

    demo = Settings(caretrace_env="DEMO")  # case-insensitive
    assert demo.env == "demo"
    assert demo.is_demo is True


def test_unknown_env_falls_back_to_dev():
    # A typo must never silently enable production behaviour.
    assert Settings(caretrace_env="prod").env == "dev"
    assert Settings(caretrace_env="").env == "dev"


def test_demo_seed_flag_defaults_off():
    assert Settings().demo_seed_enabled is False
    assert Settings(caretrace_demo_seed=True).demo_seed_enabled is True


# --- configuration: database URL normalization -------------------------------


def test_database_url_normalizes_bare_postgres_schemes():
    # Providers hand out postgres:// / postgresql:// — both must resolve to the
    # installed psycopg (v3) driver instead of crashing on missing psycopg2.
    assert (
        Settings(database_url="postgres://u:p@host/db").database_url
        == "postgresql+psycopg://u:p@host/db"
    )
    assert (
        Settings(database_url="postgresql://u:p@host/db?sslmode=require").database_url
        == "postgresql+psycopg://u:p@host/db?sslmode=require"
    )


def test_database_url_with_explicit_driver_or_sqlite_is_untouched():
    assert (
        Settings(database_url="postgresql+psycopg://u:p@host/db").database_url
        == "postgresql+psycopg://u:p@host/db"
    )
    assert Settings().database_url == "sqlite:///./caretrace_demo.db"
    assert Settings(database_url="sqlite:///./x.db").database_url == "sqlite:///./x.db"


# --- configuration: log level -----------------------------------------------


def test_log_level_defaults_to_info():
    assert Settings().log_level == logging.INFO


def test_log_level_resolves_named_levels():
    assert Settings(caretrace_log_level="DEBUG").log_level == logging.DEBUG
    assert Settings(caretrace_log_level="warning").log_level == logging.WARNING


def test_invalid_log_level_falls_back_to_info():
    assert Settings(caretrace_log_level="LOUD").log_level == logging.INFO


# --- health endpoint --------------------------------------------------------


def test_health_reports_ok_with_stable_contract(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "healthCare-monitor-backend"


# --- readiness endpoint -----------------------------------------------------


def test_ready_reports_ready_when_db_and_schema_present(client):
    response = client.get("/api/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"] == {"database": True, "schema": True}
    assert body["env"] == "dev"


def test_ready_returns_503_when_schema_missing(client):
    # Drop the core table out from under the app to simulate an un-migrated
    # database; readiness must report not-ready with a 503 and name the probe.
    from app.db.base import Base
    from app.db.session import get_db as _real_get_db  # noqa: F401

    # The `client` fixture overrides get_db with an in-memory engine; reach it
    # via the session bound to that engine and drop the runs table.
    from app.main import app as fastapi_app

    override = fastapi_app.dependency_overrides
    gen = override[_real_get_db]()
    session = next(gen)
    engine = session.get_bind()
    session.close()
    Base.metadata.tables["runs"].drop(engine)

    response = client.get("/api/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["schema"] is False

    # Credential-free diagnostics identify the resolved engine and the failing
    # probe's error class, so a remote 503 is diagnosable from the response.
    diagnostics = body["diagnostics"]
    assert diagnostics["db_backend"] == "sqlite"
    assert "schema" in diagnostics["errors"]
    assert "password" not in str(diagnostics).lower()
