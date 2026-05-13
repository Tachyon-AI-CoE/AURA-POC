"""Tests: each typed exception maps to the correct HTTP status and problem+json code."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.errors import (
    AgentAlreadyExistsError,
    AuraError,
    GitHubAuthError,
    InvalidAgentInputError,
    ScaffoldFailedError,
    TemplateNotFoundError,
    UnauthorizedError,
)


@pytest.mark.parametrize(
    ("exc_class", "expected_status", "expected_code"),
    [
        (TemplateNotFoundError, 400, "TEMPLATE_NOT_FOUND"),
        (InvalidAgentInputError, 400, "INVALID_AGENT_INPUT"),
        (AgentAlreadyExistsError, 409, "AGENT_ALREADY_EXISTS"),
        (GitHubAuthError, 502, "GITHUB_AUTH_FAILED"),
        (ScaffoldFailedError, 500, "SCAFFOLD_FAILED"),
        (UnauthorizedError, 401, "UNAUTHORIZED"),
    ],
)
def test_exception_attributes(
    exc_class: type[AuraError],
    expected_status: int,
    expected_code: str,
) -> None:
    exc = exc_class("test message")
    assert exc.status_code == expected_status
    assert exc.code == expected_code
    assert str(exc) == "test message"


@pytest.mark.asyncio
async def test_validation_error_returns_problem_json(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.post(
        "/scaffold",
        json={"scaffold_type": "single_agent"},  # missing required fields
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert resp.headers["content-type"].startswith("application/problem+json")
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "request_id" in body


@pytest.mark.asyncio
async def test_unknown_scaffold_type_returns_problem_json(
    client: AsyncClient,
    auth_headers: dict[str, str],
    valid_agent_input: dict,  # type: ignore[type-arg]
) -> None:
    payload = {**valid_agent_input, "scaffold_type": "nonexistent_type"}
    resp = await client.post("/scaffold", json=payload, headers=auth_headers)
    assert resp.status_code == 400
    assert resp.headers["content-type"].startswith("application/problem+json")
    body = resp.json()
    assert body["code"] == "TEMPLATE_NOT_FOUND"
