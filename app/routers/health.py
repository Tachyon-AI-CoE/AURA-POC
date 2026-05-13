"""GET /healthz — liveness probe (FR-1)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/healthz")
async def health_check() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": "0.1.0",
        "timestamp": datetime.now(UTC).isoformat(),
    }
