"""Request correlation + timing middleware (pure ASGI).

Assigns (or preserves) an ``X-Request-ID`` per request, binds it to the logging
context so every downstream log carries it, times the request, echoes the id on
the response, and emits one structured ``http_request`` event per completed
request. This is the backbone that lets a frontend observation be tied back to
the exact backend logs that produced it.

Implemented as a **pure ASGI** middleware rather than Starlette's
``BaseHTTPMiddleware``: the latter runs the downstream app in a separate anyio
task and pumps the response through a memory stream, which adds multi-second
latency to synchronous (threadpool) endpoints under load. A pure ASGI wrapper
has none of that overhead and keeps the correlation ``contextvar`` in the same
task as the endpoint.
"""

from __future__ import annotations

import logging
import time
import uuid

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import get_logger, log_event, set_request_id

REQUEST_ID_HEADER = "X-Request-ID"

_logger = get_logger("http")


class RequestContextMiddleware:
    """Correlation id + request timing for every HTTP request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        set_request_id(request_id)

        status_code = 500
        start = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            log_event(
                _logger,
                "http_request",
                level=logging.ERROR,
                method=scope.get("method"),
                path=scope.get("path"),
                status_code=500,
                duration_ms=duration_ms,
            )
            raise
        else:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            log_event(
                _logger,
                "http_request",
                method=scope.get("method"),
                path=scope.get("path"),
                status_code=status_code,
                duration_ms=duration_ms,
            )
        finally:
            # Reset so the id never leaks into an unrelated context afterwards.
            set_request_id(None)
