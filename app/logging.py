"""
Structured JSON logging with a per-request ``request_id`` contextvar.

The contextvar is set by :class:`RequestIDMiddleware` (added in M3); until then
``request_id`` is simply absent from log entries.
"""
# Sets up structured JSON logging and tracks request IDs across logs.

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from typing import Any

# Create a storage slot for request IDs (one per request)
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    """One JSON object per log line. Drops fields that are absent."""

    def format(self, record: logging.LogRecord) -> str:   # Called for each log line
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "name": record.name,
            "msg": record.getMessage(),
        }
         # If a request ID exists, add it to the log
        request_id = request_id_var.get()
        if request_id:
            payload["request_id"] = request_id
        # If there's an exception, add traceback    
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        #Add any extra fields attached to the log (e.g., app.status, app.route) 
        for key, value in record.__dict__.items():
            if key.startswith("app."):
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """Install the JSON formatter on the root logger. Idempotent."""
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level.upper())
    # Silence uvicorn's plain-text access logger; we emit our own in M9.
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").propagate = False


# output Result of the file will be : Every log line is JSON with request ID included. Example:

