"""
RequestIDMiddleware — per-request ID propagation and access logging.

Sets a request_id contextvar for the lifetime of each request, echoes it on
the response via X-Request-Id, and emits one structured access-log line.
"""
#Runs before and after each request to add request IDs and log access.

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
        #get request id
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        #store the id
        token = request_id_var.set(request_id)
        start = time.monotonic()
        try:
            response: Response = await call_next(request)  # type: ignore[misc]
        finally:
            latency_ms = round((time.monotonic() - start) * 1000)
            response.headers["X-Request-Id"] = request_id
            request_id_var.reset(token)
   #Log one access line with details
            logger.info(
                "request",
                extra={
                    "app.request_id": request_id, # Include request ID in log
                    "app.method": request.method, # GET, POST, etc.
                    "app.route": request.url.path, # /healthz, /scaffold, etc.
                    "app.status": response.status_code, # 200, 201, 400, etc.
                    "app.latency_ms": latency_ms,  # How long it took
                },
            )
        return response


# workflow of this program
# Request comes in → generate/get request ID
# Store ID in request_id_var (now all logs will include it)
# Call the actual endpoint
# Record time taken
# Add request ID to response header
# Log one line with method/route/status/time
# Return response