"""
RequestIDMiddleware — per-request ID propagation and access logging.

Sets a request_id contextvar for the lifetime of each request, echoes it on
the response via X-Request-Id, and emits one structured access-log line.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.logging import request_id_var

logger = logging.getLogger("aura.access")


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[..., object]) -> Response:
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        token = request_id_var.set(request_id)
        start = time.monotonic()
        try:
            response: Response = await call_next(request)  # type: ignore[misc]
        finally:
            latency_ms = round((time.monotonic() - start) * 1000)
            response.headers["X-Request-Id"] = request_id
            request_id_var.reset(token)
            logger.info(
                "request",
                extra={
                    "app.request_id": request_id,
                    "app.method": request.method,
                    "app.route": request.url.path,
                    "app.status": response.status_code,
                    "app.latency_ms": latency_ms,
                },
            )
        return response
