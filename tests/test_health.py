"""Tests for GET /healthz (FR-1)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_healthz_returns_200(client: AsyncClient) -> None:
    resp = await client.get("/healthz")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_healthz_shape(client: AsyncClient) -> None:
    resp = await client.get("/healthz")
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "timestamp" in body


@pytest.mark.asyncio
async def test_healthz_has_request_id_header(client: AsyncClient) -> None:
    resp = await client.get("/healthz")
    assert "x-request-id" in resp.headers


@pytest.mark.asyncio
async def test_healthz_echoes_provided_request_id(client: AsyncClient) -> None:
    resp = await client.get("/healthz", headers={"X-Request-Id": "my-req-id"})
    assert resp.headers.get("x-request-id") == "my-req-id"
