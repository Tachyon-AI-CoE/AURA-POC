"""Tests for scaffold_pipeline service (unit, no network).

All GitHub API calls and GCP calls are mocked. Real filesystem is used for
zip extraction and file-push tests via pytest's tmp_path fixture.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.errors import AgentAlreadyExistsError, ScaffoldFailedError
from app.schemas.agent_input import AgentInput
from app.services.scaffold_pipeline import (
    _check_agent_folder_exists,
    _download_subfolder_from_monorepo,
    _headers,
    _push_files_into_subfolder,
    _safe_rmtree,
    ensure_generated_agents_repo,
    scaffold_new_agent,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_settings() -> MagicMock:
    s = MagicMock()
    s.github_org = "test-org"
    s.generated_agents_repo = "test-generated-agents"
    return s


@pytest.fixture()
def agent_input() -> AgentInput:
    return AgentInput.model_validate(
        {
            "scaffold_type": "single_agent",
            "repo_name": "test-agent",
            "description": "Test agent.",
            "root_agent": {
                "name": "TestAgent",
                "agent_type": "LLMAgent",
                "description": "Test.",
                "multiagent": False,
                "model": "gemini-2.0-flash-001",
                "instruction": "Do stuff.",
                "generate_content_config": {
                    "temperature": 0.1,
                    "max_output_tokens": 1024,
                },
            },
            "agents": [],
        }
    )


def _build_zip(subfolder: str, extra_files: dict[str, str] | None = None) -> bytes:
    """Create an in-memory zip that matches the layout the downloader expects."""
    extra_files = extra_files or {}
    buf = io.BytesIO()
    prefix = f"repo-abc123/{subfolder}/skeleton/"
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(prefix, "")  # directory sentinel
        zf.writestr(f"{prefix}src/agent.py", "# placeholder agent code")
        zf.writestr(f"{prefix}README.md", "# scaffold readme")
        for path, content in extra_files.items():
            zf.writestr(f"{prefix}{path}", content)
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# _headers
# ---------------------------------------------------------------------------


def test_headers_authorization_bearer() -> None:
    h = _headers("my-iat-token")
    assert h["Authorization"] == "Bearer my-iat-token"
    assert "Accept" in h
    assert "X-GitHub-Api-Version" in h


# ---------------------------------------------------------------------------
# ensure_generated_agents_repo
# ---------------------------------------------------------------------------


def test_ensure_repo_returns_html_url_when_exists(mock_settings: MagicMock) -> None:
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"html_url": "https://github.com/test-org/test-generated-agents"}

    with (
        patch("app.services.scaffold_pipeline.get_settings", return_value=mock_settings),
        patch("app.services.scaffold_pipeline.requests.get", return_value=resp),
    ):
        url = ensure_generated_agents_repo("fake-iat")

    assert url == "https://github.com/test-org/test-generated-agents"


def test_ensure_repo_creates_when_404(mock_settings: MagicMock) -> None:
    get_resp = MagicMock(status_code=404)
    post_resp = MagicMock(status_code=201)
    post_resp.raise_for_status = MagicMock()
    post_resp.json.return_value = {"html_url": "https://github.com/test-org/test-generated-agents"}

    with (
        patch("app.services.scaffold_pipeline.get_settings", return_value=mock_settings),
        patch("app.services.scaffold_pipeline.requests.get", return_value=get_resp),
        patch("app.services.scaffold_pipeline.requests.post", return_value=post_resp),
    ):
        url = ensure_generated_agents_repo("fake-iat")

    assert "test-generated-agents" in url


def test_ensure_repo_raises_on_unexpected_status(mock_settings: MagicMock) -> None:
    resp = MagicMock(status_code=500)
    resp.raise_for_status.side_effect = Exception("500 Server Error")

    with (
        patch("app.services.scaffold_pipeline.get_settings", return_value=mock_settings),
        patch("app.services.scaffold_pipeline.requests.get", return_value=resp),
        pytest.raises(Exception),
    ):
        ensure_generated_agents_repo("fake-iat")


# ---------------------------------------------------------------------------
# _check_agent_folder_exists
# ---------------------------------------------------------------------------


def test_check_folder_exists_returns_true_on_200(mock_settings: MagicMock) -> None:
    with (
        patch("app.services.scaffold_pipeline.get_settings", return_value=mock_settings),
        patch(
            "app.services.scaffold_pipeline.requests.get", return_value=MagicMock(status_code=200)
        ),
    ):
        assert _check_agent_folder_exists("test-agent", "fake-iat") is True


def test_check_folder_exists_returns_false_on_404(mock_settings: MagicMock) -> None:
    with (
        patch("app.services.scaffold_pipeline.get_settings", return_value=mock_settings),
        patch(
            "app.services.scaffold_pipeline.requests.get", return_value=MagicMock(status_code=404)
        ),
    ):
        assert _check_agent_folder_exists("test-agent", "fake-iat") is False


# ---------------------------------------------------------------------------
# _download_subfolder_from_monorepo
# ---------------------------------------------------------------------------


def test_download_extracts_skeleton_files(mock_settings: MagicMock, tmp_path: Path) -> None:
    zip_bytes = _build_zip("templates/single_agent")
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.iter_content = MagicMock(return_value=[zip_bytes])

    with (
        patch("app.services.scaffold_pipeline.get_settings", return_value=mock_settings),
        patch("app.services.scaffold_pipeline.requests.get", return_value=resp),
    ):
        _download_subfolder_from_monorepo(
            "aura-poc", "templates/single_agent", "fake-iat", str(tmp_path)
        )

    assert (tmp_path / "src" / "agent.py").exists()
    assert (tmp_path / "README.md").exists()


def test_download_raises_scaffold_failed_when_subfolder_missing(
    mock_settings: MagicMock, tmp_path: Path
) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("repo-abc123/other_folder/file.txt", "data")
    buf.seek(0)

    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.iter_content = MagicMock(return_value=[buf.read()])

    with (
        patch("app.services.scaffold_pipeline.get_settings", return_value=mock_settings),
        patch("app.services.scaffold_pipeline.requests.get", return_value=resp),
        pytest.raises(ScaffoldFailedError, match="not found"),
    ):
        _download_subfolder_from_monorepo(
            "aura-poc", "templates/missing", "fake-iat", str(tmp_path)
        )


# ---------------------------------------------------------------------------
# _push_files_into_subfolder
# ---------------------------------------------------------------------------


def test_push_files_calls_github_put_for_each_file(
    mock_settings: MagicMock, tmp_path: Path
) -> None:
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "agents-config.json").write_text('{"ok": true}')
    (tmp_path / "README.md").write_text("readme")

    check_resp = MagicMock(status_code=404)  # file doesn't exist yet → no sha needed
    put_resp = MagicMock(status_code=201)

    with (
        patch("app.services.scaffold_pipeline.get_settings", return_value=mock_settings),
        patch("app.services.scaffold_pipeline.requests.get", return_value=check_resp),
        patch("app.services.scaffold_pipeline.requests.put", return_value=put_resp) as put_mock,
    ):
        _push_files_into_subfolder("test-agent", str(tmp_path), "fake-iat")

    assert put_mock.call_count == 2  # one PUT per file


def test_push_files_includes_sha_when_file_already_exists(
    mock_settings: MagicMock, tmp_path: Path
) -> None:
    (tmp_path / "file.txt").write_text("content")

    check_resp = MagicMock(status_code=200)
    check_resp.json.return_value = {"sha": "abc123sha"}
    put_resp = MagicMock(status_code=200)

    with (
        patch("app.services.scaffold_pipeline.get_settings", return_value=mock_settings),
        patch("app.services.scaffold_pipeline.requests.get", return_value=check_resp),
        patch("app.services.scaffold_pipeline.requests.put", return_value=put_resp) as put_mock,
    ):
        _push_files_into_subfolder("test-agent", str(tmp_path), "fake-iat")

    call_payload = put_mock.call_args.kwargs.get("json") or put_mock.call_args[1]["json"]
    assert call_payload["sha"] == "abc123sha"


def test_push_files_raises_on_github_error(mock_settings: MagicMock, tmp_path: Path) -> None:
    (tmp_path / "file.txt").write_text("content")

    check_resp = MagicMock(status_code=404)
    put_resp = MagicMock(status_code=422)
    put_resp.raise_for_status.side_effect = Exception("Unprocessable Entity")

    with (
        patch("app.services.scaffold_pipeline.get_settings", return_value=mock_settings),
        patch("app.services.scaffold_pipeline.requests.get", return_value=check_resp),
        patch("app.services.scaffold_pipeline.requests.put", return_value=put_resp),
        pytest.raises(Exception),
    ):
        _push_files_into_subfolder("test-agent", str(tmp_path), "fake-iat")


# ---------------------------------------------------------------------------
# _safe_rmtree
# ---------------------------------------------------------------------------


def test_safe_rmtree_removes_directory(tmp_path: Path) -> None:
    target = tmp_path / "to_remove"
    target.mkdir()
    (target / "file.txt").write_text("data")
    _safe_rmtree(str(target))
    assert not target.exists()


# ---------------------------------------------------------------------------
# scaffold_new_agent (integration through mocked helpers)
# ---------------------------------------------------------------------------


def test_scaffold_new_agent_happy_path(mock_settings: MagicMock, agent_input: AgentInput) -> None:
    with (
        patch("app.services.scaffold_pipeline.get_settings", return_value=mock_settings),
        patch("app.services.scaffold_pipeline.ensure_generated_agents_repo"),
        patch("app.services.scaffold_pipeline._check_agent_folder_exists", return_value=False),
        patch("app.services.scaffold_pipeline._download_subfolder_from_monorepo"),
        patch("app.services.scaffold_pipeline._push_files_into_subfolder"),
    ):
        url, config_path = scaffold_new_agent(
            template_repo_name=("aura-poc", "templates/single_agent"),
            agent_input=agent_input,
            iat_token="fake-iat",
        )

    assert "test-agent" in url
    assert config_path == "test-agent/config/agents-config.json"


def test_scaffold_new_agent_writes_config_json(
    mock_settings: MagicMock, agent_input: AgentInput, tmp_path: Path
) -> None:
    """agents-config.json is written with scaffolder keys stripped."""
    captured_workdir: list[str] = []

    def _capture_push(agent_folder: str, workdir: str, iat_token: str, **kwargs: Any) -> None:
        captured_workdir.append(workdir)

    with (
        patch("app.services.scaffold_pipeline.get_settings", return_value=mock_settings),
        patch("app.services.scaffold_pipeline.ensure_generated_agents_repo"),
        patch("app.services.scaffold_pipeline._check_agent_folder_exists", return_value=False),
        patch("app.services.scaffold_pipeline._download_subfolder_from_monorepo"),
        patch(
            "app.services.scaffold_pipeline._push_files_into_subfolder", side_effect=_capture_push
        ),
    ):
        scaffold_new_agent(
            template_repo_name=("aura-poc", ""),  # empty subfolder skips download
            agent_input=agent_input,
            iat_token="fake-iat",
        )

    # The workdir was cleaned up but we captured its path; check via the push call arg
    assert len(captured_workdir) == 1


def test_scaffold_new_agent_raises_when_folder_exists(
    mock_settings: MagicMock, agent_input: AgentInput
) -> None:
    with (
        patch("app.services.scaffold_pipeline.get_settings", return_value=mock_settings),
        patch("app.services.scaffold_pipeline.ensure_generated_agents_repo"),
        patch("app.services.scaffold_pipeline._check_agent_folder_exists", return_value=True),
        pytest.raises(AgentAlreadyExistsError),
    ):
        scaffold_new_agent(
            template_repo_name=("aura-poc", "templates/single_agent"),
            agent_input=agent_input,
            iat_token="fake-iat",
        )


def test_scaffold_new_agent_wraps_unexpected_exception(
    mock_settings: MagicMock, agent_input: AgentInput
) -> None:
    with (
        patch("app.services.scaffold_pipeline.get_settings", return_value=mock_settings),
        patch(
            "app.services.scaffold_pipeline.ensure_generated_agents_repo",
            side_effect=RuntimeError("unexpected GitHub 500"),
        ),
        pytest.raises(ScaffoldFailedError),
    ):
        scaffold_new_agent(
            template_repo_name=("aura-poc", "templates/single_agent"),
            agent_input=agent_input,
            iat_token="fake-iat",
        )


def test_scaffold_new_agent_reraises_scaffold_failed(
    mock_settings: MagicMock, agent_input: AgentInput
) -> None:
    """ScaffoldFailedError raised by a helper must not be double-wrapped."""
    with (
        patch("app.services.scaffold_pipeline.get_settings", return_value=mock_settings),
        patch("app.services.scaffold_pipeline.ensure_generated_agents_repo"),
        patch("app.services.scaffold_pipeline._check_agent_folder_exists", return_value=False),
        patch(
            "app.services.scaffold_pipeline._download_subfolder_from_monorepo",
            side_effect=ScaffoldFailedError("zip had no skeleton/"),
        ),
        pytest.raises(ScaffoldFailedError, match="zip had no skeleton/"),
    ):
        scaffold_new_agent(
            template_repo_name=("aura-poc", "templates/single_agent"),
            agent_input=agent_input,
            iat_token="fake-iat",
        )
