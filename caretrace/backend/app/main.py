"""FastAPI application entrypoint.

Run locally with:
    uv run uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.include_router(api_router, prefix=settings.api_prefix)
