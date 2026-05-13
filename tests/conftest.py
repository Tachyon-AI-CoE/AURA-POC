"""Shared pytest fixtures."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.settings import Settings, get_settings


@pytest.fixture()
def settings_override() -> Settings:
    return Settings(
        github_app_id="test-app-id",
        github_installation_id="test-install-id",
        github_org="test-org",
        generated_agents_repo="test-generated-agents",
        github_private_key_file=None,
        github_private_key=None,
        scaffold_api_key="test-secret-key",  # type: ignore[arg-type]
        cors_allowlist=[],
        log_level="WARNING",
    )


@pytest.fixture()
def app(settings_override: Settings) -> FastAPI:
    application = create_app()
    application.dependency_overrides[get_settings] = lambda: settings_override
    return application


@pytest.fixture()
async def client(app: FastAPI) -> AsyncClient:  # type: ignore[misc]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac  # type: ignore[misc]


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-secret-key"}


@pytest.fixture()
def valid_agent_input() -> dict[str, Any]:
    return {
        "scaffold_type": "single_agent",
        "repo_name": "test-agent",
        "description": "Test agent for unit tests.",
        "root_agent": {
            "name": "TestAgent",
            "agent_type": "LLMAgent",
            "description": "A test agent.",
            "multiagent": False,
            "model": "gemini-2.0-flash-001",
            "instruction": "You are a test agent.",
            "generate_content_config": {
                "temperature": 0.1,
                "max_output_tokens": 1024,
            },
        },
        "agents": [],
    }
