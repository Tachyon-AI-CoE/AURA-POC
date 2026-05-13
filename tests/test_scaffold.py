"""Integration tests for POST /scaffold (FR-3..FR-11, GitHub API mocked)."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.errors import AgentAlreadyExistsError
from app.main import create_app
from app.settings import Settings, get_settings


@pytest.fixture()
def _mock_pipeline() -> Any:
    """Patch both GitHub auth and the scaffold pipeline for happy-path tests."""
    with (
        patch(
            "app.routers.scaffold.get_installation_token",
            return_value="fake-iat",
        ),
        patch(
            "app.routers.scaffold.scaffold_new_agent",
            return_value=(
                "https://github.com/test-org/test-generated-agents/tree/main/test-agent",
                "test-agent/config/agents-config.json",
            ),
        ),
    ):
        yield


@pytest.mark.asyncio
async def test_scaffold_happy_path(
    client: AsyncClient,
    auth_headers: dict[str, str],
    valid_agent_input: dict[str, Any],
    _mock_pipeline: None,
) -> None:
    resp = await client.post("/scaffold", json=valid_agent_input, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "success"
    assert body["scaffold_type"] == "single_agent"
    assert "repo_url" in body
    assert "config_path" in body
    assert "job_id" in body
    assert "created_at" in body


@pytest.mark.asyncio
async def test_scaffold_response_has_request_id_header(
    client: AsyncClient,
    auth_headers: dict[str, str],
    valid_agent_input: dict[str, Any],
    _mock_pipeline: None,
) -> None:
    resp = await client.post("/scaffold", json=valid_agent_input, headers=auth_headers)
    assert "x-request-id" in resp.headers


@pytest.mark.asyncio
async def test_scaffold_missing_bearer_returns_401(
    client: AsyncClient,
    valid_agent_input: dict[str, Any],
    _mock_pipeline: None,
) -> None:
    resp = await client.post("/scaffold", json=valid_agent_input)
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_scaffold_wrong_bearer_returns_401(
    client: AsyncClient,
    valid_agent_input: dict[str, Any],
    _mock_pipeline: None,
) -> None:
    resp = await client.post(
        "/scaffold",
        json=valid_agent_input,
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_scaffold_invalid_body_returns_422(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.post(
        "/scaffold",
        json={"scaffold_type": "single_agent"},  # missing root_agent
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert resp.headers["content-type"].startswith("application/problem+json")


@pytest.mark.asyncio
async def test_scaffold_extra_top_level_key_returns_422(
    client: AsyncClient,
    auth_headers: dict[str, str],
    valid_agent_input: dict[str, Any],
) -> None:
    payload = {**valid_agent_input, "injected_key": "evil"}
    resp = await client.post("/scaffold", json=payload, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_scaffold_unknown_type_returns_400(
    client: AsyncClient,
    auth_headers: dict[str, str],
    valid_agent_input: dict[str, Any],
) -> None:
    payload = {**valid_agent_input, "scaffold_type": "not_registered"}
    with patch("app.routers.scaffold.get_installation_token", return_value="fake-iat"):
        resp = await client.post("/scaffold", json=payload, headers=auth_headers)
    assert resp.status_code == 400
    assert resp.json()["code"] == "TEMPLATE_NOT_FOUND"


@pytest.mark.asyncio
async def test_scaffold_github_auth_failure_returns_502(
    client: AsyncClient,
    auth_headers: dict[str, str],
    valid_agent_input: dict[str, Any],
) -> None:
    with patch(
        "app.routers.scaffold.get_installation_token",
        side_effect=RuntimeError("GitHub down"),
    ):
        resp = await client.post("/scaffold", json=valid_agent_input, headers=auth_headers)
    assert resp.status_code == 502
    assert resp.json()["code"] == "GITHUB_AUTH_FAILED"


@pytest.mark.asyncio
async def test_scaffold_agent_already_exists_returns_409(
    client: AsyncClient,
    auth_headers: dict[str, str],
    valid_agent_input: dict[str, Any],
) -> None:
    with (
        patch("app.routers.scaffold.get_installation_token", return_value="fake-iat"),
        patch(
            "app.routers.scaffold.scaffold_new_agent",
            side_effect=AgentAlreadyExistsError("test-agent already exists"),
        ),
    ):
        resp = await client.post("/scaffold", json=valid_agent_input, headers=auth_headers)
    assert resp.status_code == 409
    assert resp.json()["code"] == "AGENT_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_scaffold_pipeline_failure_returns_500(
    client: AsyncClient,
    auth_headers: dict[str, str],
    valid_agent_input: dict[str, Any],
) -> None:
    with (
        patch("app.routers.scaffold.get_installation_token", return_value="fake-iat"),
        patch(
            "app.routers.scaffold.scaffold_new_agent",
            side_effect=RuntimeError("Push failed"),
        ),
    ):
        resp = await client.post("/scaffold", json=valid_agent_input, headers=auth_headers)
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_scaffold_fr11_file_fallback_when_no_body(
    auth_headers: dict[str, str],
    valid_agent_input: dict[str, Any],
    tmp_path: Any,
) -> None:
    """FR-11: body-less POST falls back to AGENT_INPUT_PATH file (deprecated path)."""
    input_file = tmp_path / "agent_input.json"
    input_file.write_text(json.dumps(valid_agent_input))

    settings = Settings(
        github_app_id="test",
        github_installation_id="test",
        github_org="test",
        generated_agents_repo="test",
        scaffold_api_key="test-secret-key",  # type: ignore[arg-type]
        cors_allowlist=[],
        agent_input_path=str(input_file),
        log_level="WARNING",
    )
    fallback_app = create_app()
    fallback_app.dependency_overrides[get_settings] = lambda: settings

    async with AsyncClient(transport=ASGITransport(app=fallback_app), base_url="http://test") as ac:
        with (
            patch("app.routers.scaffold.get_installation_token", return_value="fake-iat"),
            patch(
                "app.routers.scaffold.scaffold_new_agent",
                return_value=(
                    "https://github.com/test/repo/tree/main/test-agent",
                    "test-agent/config/agents-config.json",
                ),
            ),
        ):
            resp = await ac.post("/scaffold", headers=auth_headers)

    assert resp.status_code == 201
    assert resp.json()["status"] == "success"


@pytest.mark.asyncio
async def test_scaffold_fr11_fallback_missing_file_returns_400(
    auth_headers: dict[str, str],
) -> None:
    """FR-11: fallback file not found → 400 INVALID_AGENT_INPUT."""
    settings = Settings(
        github_app_id="test",
        github_installation_id="test",
        github_org="test",
        generated_agents_repo="test",
        scaffold_api_key="test-secret-key",  # type: ignore[arg-type]
        cors_allowlist=[],
        agent_input_path="/nonexistent/path/agent_input.json",
        log_level="WARNING",
    )
    fallback_app = create_app()
    fallback_app.dependency_overrides[get_settings] = lambda: settings

    async with AsyncClient(transport=ASGITransport(app=fallback_app), base_url="http://test") as ac:
        resp = await ac.post("/scaffold", headers=auth_headers)

    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_AGENT_INPUT"


@pytest.mark.asyncio
async def test_scaffold_accepts_multiagent_input(
    client: AsyncClient,
    auth_headers: dict[str, str],
    _mock_pipeline: None,
) -> None:
    multiagent_payload = {
        "scaffold_type": "multiagent_orchestrator",
        "repo_name": "test-multi-agent",
        "description": "Test multiagent.",
        "root_agent": {
            "name": "Orchestrator",
            "agent_type": "LLMAgent",
            "description": "Root orchestrator.",
            "multiagent": True,
            "model": "gemini-2.0-flash-001",
            "instruction": "Orchestrate.",
        },
        "agents": [
            {
                "name": "worker",
                "agent_type": "LLMAgent",
                "description": "Worker agent.",
                "model": "gemini-2.0-flash-001",
                "instruction": "Do work.",
                "sub_agents": [],
            }
        ],
        "custom_agents": [],
    }
    resp = await client.post("/scaffold", json=multiagent_payload, headers=auth_headers)
    assert resp.status_code == 201
