"""Smoke test for the health endpoint and app wiring."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app

client = TestClient(app)


def test_health_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    # Stable contract, extended with safe build metadata.
    assert body["status"] == "ok"
    assert body["service"] == "healthCare-monitor-backend"
    assert body["env"] in {"dev", "demo", "production"}
    assert body["version"] == "0.1.0"
    assert body["uptime_s"] >= 0
    # No commit SHA is injected in the test environment.
    assert "build" in body


def test_build_ref_shortens_commit_sha():
    settings = Settings(vercel_git_commit_sha="0123456789abcdef0123456789abcdef01234567")
    assert settings.build_ref == "0123456"
    assert Settings(vercel_git_commit_sha=None).build_ref is None
    assert Settings(vercel_git_commit_sha="  ").build_ref is None
