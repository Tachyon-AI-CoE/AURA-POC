"""Tests that log output never contains secret values (T9.4, CLAUDE.md §4 §10).

Captures the aura.* logger hierarchy during a mocked scaffold request and
asserts that none of the log records include the IAT token value, the
scaffold API key, or any PEM-like content.
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import patch

import pytest
from httpx import AsyncClient

# Values that MUST NOT appear in any log record.
_FORBIDDEN = [
    "ghs_fake_iat_secret",  # IAT token value
    "test-secret-key",  # scaffold API key (present in conftest auth_headers)
    "PRIVATE KEY",  # PEM header guard
    "BEGIN RSA",  # PEM RSA marker
]


@pytest.mark.asyncio
async def test_scaffold_logs_contain_no_secrets(
    client: AsyncClient,
    auth_headers: dict[str, str],
    valid_agent_input: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    with (
        caplog.at_level(logging.DEBUG, logger="aura"),
        patch(
            "app.routers.scaffold.get_installation_token",
            return_value="ghs_fake_iat_secret",
        ),
        patch(
            "app.routers.scaffold.scaffold_new_agent",
            return_value=(
                "https://github.com/test-org/test-repo/tree/main/test-agent",
                "test-agent/config/agents-config.json",
            ),
        ),
    ):
        resp = await client.post("/scaffold", json=valid_agent_input, headers=auth_headers)

    assert resp.status_code == 201

    all_log_text = " ".join(r.getMessage() for r in caplog.records)
    for marker in _FORBIDDEN:
        assert marker not in all_log_text, (
            f"Sensitive marker '{marker}' found in log output. "
            "Review logging calls in app/routers/scaffold.py and middleware."
        )


@pytest.mark.asyncio
async def test_health_logs_contain_no_secrets(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG, logger="aura"):
        resp = await client.get("/healthz")

    assert resp.status_code == 200

    all_log_text = " ".join(r.getMessage() for r in caplog.records)
    for marker in _FORBIDDEN:
        assert marker not in all_log_text
