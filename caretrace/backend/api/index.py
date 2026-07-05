"""Vercel serverless entrypoint for the FastAPI backend.

Vercel's `@vercel/python` runtime detects a module-level ASGI callable named
``app`` and serves it directly — no uvicorn/gunicorn process is needed. All
incoming routes are rewritten to this function by ``vercel.json``; the FastAPI
app keeps its own ``/api`` prefix, so a request to ``/api/health`` reaches the
matching route unchanged.

The ``sys.path`` insert makes the sibling ``app`` package importable regardless
of the builder's working directory. Nothing here runs at import time except the
(connection-less) app construction, so cold starts stay cheap and the read-only
serverless filesystem is never written to.
"""

import os
import sys

# Backend root = the directory that contains both this `api/` folder and the
# `app/` package. Ensure it is importable before importing the application.
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from app.main import app  # noqa: E402  (import after sys.path setup)

# Vercel looks for a module-level ASGI application named `app`.
__all__ = ["app"]
