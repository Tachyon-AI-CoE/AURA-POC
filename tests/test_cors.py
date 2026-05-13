"""Tests for CORS hardening (T9.2, NFR-8).

Verifies that origins not in cors_allowlist do not receive
Access-Control-Allow-Origin in the response.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.settings import Settings, get_settings


def _make_app(cors_allowlist: list[str]) -> FastAPI:
    """Create app with a specific CORS allowlist.

    Patching app.main.get_settings ensures the CORSMiddleware constructor
    receives the correct allowlist (it reads settings at create_app() time,
    not per-request, so dependency_overrides alone is not enough).
    """
    settings = Settings(
        github_app_id="test",
        github_installation_id="test",
        github_org="test",
        generated_agents_repo="test",
        scaffold_api_key="test-key",  # type: ignore[arg-type]
        cors_allowlist=cors_allowlist,
        log_level="WARNING",
    )
    with patch("app.main.get_settings", return_value=settings):
        app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    return app


@pytest.fixture()
def allowlisted_app() -> FastAPI:
    """App with a single-origin CORS allowlist."""
    return _make_app(["https://allowed.example.com"])


@pytest.mark.asyncio
async def test_allowed_origin_receives_acao_header(allowlisted_app: FastAPI) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=allowlisted_app), base_url="http://test"
    ) as client:
        resp = await client.get("/healthz", headers={"Origin": "https://allowed.example.com"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "https://allowed.example.com"


@pytest.mark.asyncio
async def test_disallowed_origin_no_acao_header(allowlisted_app: FastAPI) -> None:
    """CORS middleware must not echo Access-Control-Allow-Origin for unlisted origins."""
    async with AsyncClient(
        transport=ASGITransport(app=allowlisted_app), base_url="http://test"
    ) as client:
        resp = await client.get("/healthz", headers={"Origin": "https://evil.example.com"})
    assert resp.status_code == 200
    acao = resp.headers.get("access-control-allow-origin", "")
    assert acao != "https://evil.example.com"
    assert acao != "*"


@pytest.mark.asyncio
async def test_preflight_disallowed_origin_no_wildcard(allowlisted_app: FastAPI) -> None:
    """OPTIONS preflight from a disallowed origin must not receive a wildcard ACAO."""
    async with AsyncClient(
        transport=ASGITransport(app=allowlisted_app), base_url="http://test"
    ) as client:
        resp = await client.options(
            "/scaffold",
            headers={
                "Origin": "https://attacker.example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
    acao = resp.headers.get("access-control-allow-origin", "")
    assert acao != "*"
    assert acao != "https://attacker.example.com"


@pytest.mark.asyncio
async def test_empty_allowlist_no_cors_headers() -> None:
    """Empty cors_allowlist (the default) means no origin ever gets ACAO."""
    app = _make_app([])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/healthz", headers={"Origin": "https://any.example.com"})
    assert resp.headers.get("access-control-allow-origin", "") not in (
        "*",
        "https://any.example.com",
    )
