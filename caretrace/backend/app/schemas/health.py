"""Health and readiness response schemas."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response body for the liveness/health endpoint.

    `version`/`build`/`uptime_s` are additive, safe metadata (no hosts, no
    credentials): which build is serving traffic and how long this instance
    has been up. `build` is None when the host injects no commit SHA.
    """

    status: str
    service: str
    env: str
    version: str
    build: str | None = None
    uptime_s: float


class ReadinessResponse(BaseModel):
    """Response body for the readiness endpoint.

    Reports whether the service can actually serve traffic: the database is
    reachable and the core schema is present. `checks` carries the individual
    probe results so an operator can see *what* failed, not just that something
    did.
    """

    status: str
    service: str
    env: str
    checks: dict[str, bool]
