"""GET /templates — list supported scaffold types (FR-2)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.core.template_registry import (
    TEMPLATE_MONOREPO,
    TEMPLATE_REGISTRY,
    list_supported_types,
)

router = APIRouter(tags=["Templates"])


@router.get("/templates")
async def list_templates() -> dict[str, Any]:
    return {
        "monorepo": TEMPLATE_MONOREPO,
        "supported_scaffold_types": list_supported_types(),
        "registry": {k: f"{TEMPLATE_MONOREPO}/{v}/skeleton" for k, v in TEMPLATE_REGISTRY.items()},
    }
