"""Unit tests for mcp_client utility functions."""

import sys
import os
import types
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))  # noqa: E402

# ---------------------------------------------------------------------------
# Stub out heavy google.adk MCP toolset classes BEFORE importing mcp_client.
# mcp_client.py has module-level code:
#   toolset = create_mcp_toolset_from_config(http_mcp_config)
# which instantiates McpToolset / DeployableMcpToolset. We provide lightweight
# stubs so the module can be imported without network or SDK requirements.
# We use setdefault so the real package (if installed) is preferred.
# ---------------------------------------------------------------------------


class _StubStreamableHTTPConnectionParams:
    def __init__(self, url=None, headers=None, errlog=None):
        self.url = url
        self.headers = headers or {}


class _StubMcpToolset:
    def __init__(self, connection_params=None):
        self._connection_params = connection_params


_mcp_toolset_mod = sys.modules.get(
    "google.adk.tools.mcp_tool.mcp_toolset",
    types.SimpleNamespace(McpToolset=_StubMcpToolset),
)
_mcp_session_mod = sys.modules.get(
    "google.adk.tools.mcp_tool.mcp_session_manager",
    types.SimpleNamespace(
        StreamableHTTPConnectionParams=_StubStreamableHTTPConnectionParams
    ),
)

# Only register stubs if not already present (real package takes priority)
if "google.adk.tools.mcp_tool.mcp_toolset" not in sys.modules:
    sys.modules["google.adk.tools.mcp_tool.mcp_toolset"] = _mcp_toolset_mod
if "google.adk.tools.mcp_tool.mcp_session_manager" not in sys.modules:
    sys.modules["google.adk.tools.mcp_tool.mcp_session_manager"] = _mcp_session_mod

# Ensure McpToolset is accessible via the stub classes regardless
_mcp_toolset_mod.McpToolset = getattr(
    _mcp_toolset_mod, "McpToolset", _StubMcpToolset
)
_mcp_session_mod.StreamableHTTPConnectionParams = getattr(
    _mcp_session_mod,
    "StreamableHTTPConnectionParams",
    _StubStreamableHTTPConnectionParams,
)

from root_agent.tools.mcp_client import (  # noqa: E402
    create_bearer_auth_headers,
    merge_headers,
    create_http_connection_params,
    create_http_mcp_toolset,
    create_mcp_toolset_from_config,
    DeployableMcpToolset,
)


# ---------------------------------------------------------------------------
# create_bearer_auth_headers
# ---------------------------------------------------------------------------


class TestCreateBearerAuthHeaders:
    def test_returns_correct_header(self):
        headers = create_bearer_auth_headers("my-token")
        assert headers == {"Authorization": "Bearer my-token"}

    def test_empty_token(self):
        headers = create_bearer_auth_headers("")
        assert headers == {"Authorization": "Bearer "}

    def test_token_preserved_exactly(self):
        token = "eyJhbGciOiJSUzI1NiJ9.abc.def"
        headers = create_bearer_auth_headers(token)
        assert headers["Authorization"] == f"Bearer {token}"


# ---------------------------------------------------------------------------
# merge_headers
# ---------------------------------------------------------------------------


class TestMergeHeaders:
    def test_single_dict(self):
        result = merge_headers({"X-Key": "val"})
        assert result == {"X-Key": "val"}

    def test_two_dicts_combined(self):
        result = merge_headers({"A": "1"}, {"B": "2"})
        assert result == {"A": "1", "B": "2"}

    def test_later_dict_overrides_earlier(self):
        result = merge_headers({"A": "first"}, {"A": "second"})
        assert result["A"] == "second"

    def test_none_dicts_ignored(self):
        result = merge_headers(None, {"B": "2"}, None)
        assert result == {"B": "2"}

    def test_empty_dict_ignored(self):
        result = merge_headers({}, {"C": "3"})
        assert result == {"C": "3"}

    def test_no_args_returns_empty(self):
        assert merge_headers() == {}

    def test_all_none_returns_empty(self):
        assert merge_headers(None, None) == {}


# ---------------------------------------------------------------------------
# create_http_connection_params
# ---------------------------------------------------------------------------


class TestCreateHttpConnectionParams:
    def test_returns_connection_params_object(self):
        params = create_http_connection_params("https://example.com/mcp")
        assert params is not None
        assert params.url == "https://example.com/mcp"

    def test_default_headers_empty(self):
        params = create_http_connection_params("https://example.com/mcp")
        assert params.headers == {}

    def test_custom_headers_passed_through(self):
        headers = {"Authorization": "Bearer tok", "X-Custom": "value"}
        params = create_http_connection_params("https://example.com", headers)
        assert params.headers == headers

    def test_empty_url_raises(self):
        with pytest.raises(ValueError, match="URL is required"):
            create_http_connection_params("")

    def test_none_url_raises(self):
        with pytest.raises((ValueError, TypeError)):
            create_http_connection_params(None)


# ---------------------------------------------------------------------------
# create_http_mcp_toolset
# ---------------------------------------------------------------------------


class TestCreateHttpMcpToolset:
    def test_returns_deployable_mcp_toolset(self):
        toolset = create_http_mcp_toolset("https://example.com/mcp")
        assert isinstance(toolset, DeployableMcpToolset)

    def test_auth_token_sets_auth_config(self):
        toolset = create_http_mcp_toolset(
            "https://example.com/mcp", auth_token="my-token"
        )
        auth_cfg = getattr(toolset, "_auth_config", None)
        assert auth_cfg is not None
        assert auth_cfg.get("auth_token") == "my-token"

    def test_no_auth_token_empty_auth_config(self):
        toolset = create_http_mcp_toolset("https://example.com/mcp")
        auth_cfg = getattr(toolset, "_auth_config", None)
        assert auth_cfg is not None
        assert auth_cfg == {}

    def test_additional_headers_merged(self):
        extra = {"X-Custom": "custom-value"}
        # Should not raise; headers are merged internally
        toolset = create_http_mcp_toolset(
            "https://example.com/mcp", auth_token="tok", headers=extra
        )
        assert isinstance(toolset, DeployableMcpToolset)


# ---------------------------------------------------------------------------
# create_mcp_toolset_from_config
# ---------------------------------------------------------------------------


class TestCreateMcpToolsetFromConfig:
    def test_url_config_creates_toolset(self):
        config = {"url": "https://example.com/mcp"}
        toolset = create_mcp_toolset_from_config(config)
        assert isinstance(toolset, DeployableMcpToolset)

    def test_auth_token_in_config(self):
        config = {"url": "https://example.com/mcp", "auth_token": "secret"}
        toolset = create_mcp_toolset_from_config(config)
        assert isinstance(toolset, DeployableMcpToolset)

    def test_bearer_token_in_config(self):
        config = {"url": "https://example.com/mcp", "bearer_token": "tok"}
        toolset = create_mcp_toolset_from_config(config)
        assert isinstance(toolset, DeployableMcpToolset)

    def test_missing_url_and_connection_params_raises(self):
        with pytest.raises(ValueError, match="'connection_params' or 'url'"):
            create_mcp_toolset_from_config({"headers": {}})

    def test_connection_params_config_creates_toolset(self):
        stub_params = _StubStreamableHTTPConnectionParams(url="https://x.com")
        config = {"connection_params": stub_params}
        toolset = create_mcp_toolset_from_config(config)
        assert toolset is not None

    def test_headers_in_config(self):
        config = {"url": "https://example.com/mcp", "headers": {"X-Custom": "val"}}
        toolset = create_mcp_toolset_from_config(config)
        assert isinstance(toolset, DeployableMcpToolset)


# ---------------------------------------------------------------------------
# DeployableMcpToolset.__deepcopy__
# ---------------------------------------------------------------------------


class TestDeployableMcpToolsetDeepCopy:
    def test_deepcopy_basic(self):
        import copy
        params = _StubStreamableHTTPConnectionParams(url="https://x.com")
        original = DeployableMcpToolset(connection_params=params)
        copied = copy.deepcopy(original)
        assert copied is not original
        assert isinstance(copied, DeployableMcpToolset)

    def test_deepcopy_preserves_connection_params(self):
        import copy
        params = _StubStreamableHTTPConnectionParams(url="https://x.com")
        original = DeployableMcpToolset(connection_params=params)
        copied = copy.deepcopy(original)
        assert copied._connection_params is params

    def test_deepcopy_preserves_auth_config(self):
        import copy
        params = _StubStreamableHTTPConnectionParams(url="https://x.com")
        original = DeployableMcpToolset(connection_params=params)
        original._auth_config = {"auth_token": "tok"}
        copied = copy.deepcopy(original)
        auth = getattr(copied, "_auth_config", None)
        assert auth == {"auth_token": "tok"}

    def test_deepcopy_handles_missing_auth_attrs(self):
        import copy
        params = _StubStreamableHTTPConnectionParams(url="https://x.com")
        original = DeployableMcpToolset(connection_params=params)
        # Ensure _auth_config and _use_mcp_resources don't exist
        if hasattr(original, "_auth_config"):
            delattr(original, "_auth_config")
        copied = copy.deepcopy(original)
        assert isinstance(copied, DeployableMcpToolset)


# ---------------------------------------------------------------------------
# create_mcp_toolset_with_connection_params & create_example_toolset
# ---------------------------------------------------------------------------


class TestMcpClientMiscFunctions:
    def test_create_mcp_toolset_with_connection_params(self):
        from root_agent.tools.mcp_client import create_mcp_toolset_with_connection_params
        params = _StubStreamableHTTPConnectionParams(url="https://x.com")
        toolset = create_mcp_toolset_with_connection_params(params)
        assert toolset is not None

    def test_create_example_toolset(self):
        from root_agent.tools.mcp_client import create_example_toolset
        toolset = create_example_toolset()
        assert isinstance(toolset, DeployableMcpToolset)

    def test_no_auth_token_no_headers(self):
        """Test create_http_mcp_toolset with no auth and no extra headers."""
        toolset = create_http_mcp_toolset("https://x.com")
        assert isinstance(toolset, DeployableMcpToolset)
        assert getattr(toolset, "_auth_config", None) == {}
