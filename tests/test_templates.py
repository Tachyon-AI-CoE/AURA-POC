"""Tests for GET /templates (FR-2)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.template_registry import list_supported_types


@pytest.mark.asyncio
async def test_templates_returns_200(client: AsyncClient) -> None:
    resp = await client.get("/templates")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_templates_shape(client: AsyncClient) -> None:
    resp = await client.get("/templates")
    body = resp.json()
    assert "monorepo" in body
    assert "supported_scaffold_types" in body
    assert "registry" in body


@pytest.mark.asyncio
async def test_templates_lists_all_registered_types(client: AsyncClient) -> None:
    resp = await client.get("/templates")
    returned = set(resp.json()["supported_scaffold_types"])
    expected = set(list_supported_types())
    assert returned == expected


@pytest.mark.asyncio
async def test_templates_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get("/templates")
    assert resp.status_code == 200
