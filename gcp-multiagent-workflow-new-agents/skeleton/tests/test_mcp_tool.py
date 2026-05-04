"""Tests for root_agent/tools/mcp_tool.py — MCPTool."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import pytest
from unittest.mock import patch, MagicMock
from root_agent.tools.mcp_tool import MCPTool


def test_mcp_tool_init():
    config = {"server_url": "http://test", "api_key": "key", "base_path": "/api", "health_path": "/health"}
    tool = MCPTool("name", config)
    assert tool.name == "name"
    assert tool.server_url == "http://test"
    assert tool.api_key == "key"
    assert tool.base_path == "/api"
    assert tool.health_path == "/health"
    config2 = {"server_url": "http://test/", "api_key": "key"}
    tool2 = MCPTool("name", config2)
    assert tool2.server_url == "http://test"

def test_mcp_tool_build_url():
    config = {"server_url": "http://test", "base_path": "/api"}
    tool = MCPTool("name", config)
    assert tool._build_url("http://other/path") == "http://other/path"
    assert tool._build_url("/foo") == "http://test/api/foo"
    assert tool._build_url("") == "http://test/api"


class TestMCPToolHeaders:
    def test_headers_with_api_key(self):
        tool = MCPTool("t", {"server_url": "http://x", "api_key": "mykey"})
        h = tool.headers()
        assert h["Authorization"] == "Bearer mykey"
        assert h["Content-Type"] == "application/json"

    def test_headers_without_api_key(self):
        tool = MCPTool("t", {"server_url": "http://x"})
        assert "Authorization" not in tool.headers()

    def test_headers_with_extra(self):
        tool = MCPTool("t", {"server_url": "http://x"})
        assert tool.headers(extra={"X-Custom": "val"})["X-Custom"] == "val"

    def test_api_key_from_env_key(self):
        tool = MCPTool("t", {"server_url": "http://x", "api_key_env": "MY_KEY"})
        assert tool.api_key == "MY_KEY"


class TestMCPToolBuildUrl:
    def test_absolute_url_passthrough(self):
        tool = MCPTool("t", {"server_url": "http://s"})
        assert tool._build_url("https://other.com/p") == "https://other.com/p"

    def test_with_base_path_no_leading_slash(self):
        tool = MCPTool("t", {"server_url": "http://s", "base_path": "api"})
        assert tool._build_url("/foo") == "http://s/api/foo"

    def test_base_path_trailing_slash_stripped(self):
        tool = MCPTool("t", {"server_url": "http://s", "base_path": "/api/"})
        assert tool._build_url("/foo") == "http://s/api/foo"

    def test_path_without_leading_slash(self):
        tool = MCPTool("t", {"server_url": "http://s", "base_path": "/api"})
        assert tool._build_url("foo") == "http://s/api/foo"

    def test_none_path(self):
        assert MCPTool("t", {"server_url": "http://s"})._build_url(None) == "http://s"

    def test_empty_base_path(self):
        assert MCPTool("t", {"server_url": "http://s"})._build_url("/foo") == "http://s/foo"


class TestMCPToolHealth:
    @patch("root_agent.tools.mcp_tool.requests")
    def test_health_success(self, mock_requests):
        mock_resp = MagicMock(status_code=200, text="ok")
        mock_requests.get.return_value = mock_resp
        result = MCPTool("t", {"server_url": "http://s", "health_path": "/healthz"}).health()
        assert result["status_code"] == 200

    @patch("root_agent.tools.mcp_tool.requests")
    def test_health_default_path(self, mock_requests):
        mock_requests.get.return_value = MagicMock(status_code=200, text="ok")
        MCPTool("t", {"server_url": "http://s"}).health()
        assert "/health" in mock_requests.get.call_args[0][0]

    @patch("root_agent.tools.mcp_tool.requests")
    def test_health_failure(self, mock_requests):
        mock_requests.get.side_effect = ConnectionError("refused")
        result = MCPTool("t", {"server_url": "http://s"}).health()
        assert result["status_code"] is None
        assert "error" in result


class TestMCPToolRequest:
    @patch("root_agent.tools.mcp_tool.requests")
    def test_request_get(self, mock_requests):
        mock_resp = MagicMock(status_code=200, content=b'{"data": 1}', text='{"data": 1}')
        mock_resp.json.return_value = {"data": 1}
        mock_requests.request.return_value = mock_resp
        result = MCPTool("t", {"server_url": "http://s"}).request("GET", "/api/data")
        assert result["status_code"] == 200
        assert result["json"] == {"data": 1}

    @patch("root_agent.tools.mcp_tool.requests")
    def test_request_post_with_json(self, mock_requests):
        mock_resp = MagicMock(status_code=201, content=b'{"id": 1}', text='{"id": 1}')
        mock_resp.json.return_value = {"id": 1}
        mock_requests.request.return_value = mock_resp
        result = MCPTool("t", {"server_url": "http://s"}).request("POST", "/api/create", json={"name": "x"})
        assert result["status_code"] == 201

    @patch("root_agent.tools.mcp_tool.requests")
    def test_request_empty_content(self, mock_requests):
        mock_requests.request.return_value = MagicMock(status_code=204, content=b"", text="")
        result = MCPTool("t", {"server_url": "http://s"}).request("DELETE", "/api/item/1")
        assert result["json"] is None

    @patch("root_agent.tools.mcp_tool.requests")
    def test_request_failure(self, mock_requests):
        mock_requests.request.side_effect = ConnectionError("timeout")
        result = MCPTool("t", {"server_url": "http://s"}).request("GET", "/fail")
        assert result["status_code"] is None
        assert "error" in result
