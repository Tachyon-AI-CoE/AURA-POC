"""Tests for root_agent/tools/tools_builder.py — ToolsBuilder + convenience functions."""

import sys
import os
import types
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import pytest
from unittest.mock import patch, MagicMock
from root_agent.tools.tools_builder import (
    ToolsBuilder, MCPToolAdapter,
    create_tools_from_yaml_config,
    create_rag_tools_from_yaml_config,
    create_mcp_tools_from_yaml_config,
    create_tool_by_type,
)
from root_agent.tools.mcp_tool import MCPTool


# ---------------------------------------------------------------------------
# Original tests
# ---------------------------------------------------------------------------

def test_tools_builder_global_config():
    builder = ToolsBuilder()
    config = {"foo": "bar"}
    builder.set_global_config(config)
    assert builder._global_config == config

def test_tools_builder_add_tool():
    builder = ToolsBuilder()
    builder.add_tool("tool1")
    assert "tool1" in builder._tools
    builder.add_tools(["tool2", "tool3"])
    assert "tool2" in builder._tools and "tool3" in builder._tools
    builder._tools = ["tool4"]
    assert builder._tools == ["tool4"]

def test_mcp_tool_adapter_call_and_health(monkeypatch):
    class DummyMCP:
        def request(self, **kwargs):
            return {"ok": True}
        def health(self, timeout=5):
            return "healthy"
        name = "dummy"
        description = "desc"
    adapter = MCPToolAdapter(DummyMCP())
    assert adapter() == {"ok": True}
    assert adapter.health() == "healthy"
    assert adapter.name == "dummy"
    assert adapter.description == "desc"


# ---------------------------------------------------------------------------
# Extended ToolsBuilder methods
# ---------------------------------------------------------------------------

class TestToolsBuilderMethods:
    def test_clear_tools(self):
        b = ToolsBuilder()
        b.add_tool("t1")
        b.clear_tools()
        assert b._tools == []

    def test_get_tools_returns_copy(self):
        b = ToolsBuilder()
        b.add_tool("t1")
        tools = b.get_tools()
        tools.append("t2")
        assert len(b._tools) == 1

    def test_get_tool_count(self):
        b = ToolsBuilder()
        b.add_tools(["t1", "t2"])
        assert b.get_tool_count() == 2

    def test_has_tools_true(self):
        b = ToolsBuilder()
        b.add_tool("t1")
        assert b.has_tools() is True

    def test_has_tools_false(self):
        assert ToolsBuilder().has_tools() is False

    def test_reset(self):
        b = ToolsBuilder()
        b.add_tool("t1")
        b.set_global_config({"k": "v"})
        b.reset()
        assert b._tools == []
        assert b._global_config is None

    def test_add_tool_skips_none(self):
        b = ToolsBuilder()
        b.add_tool(None)
        assert b._tools == []

    def test_add_tools_skips_none(self):
        b = ToolsBuilder()
        b.add_tools([None, "t1", None])
        assert b._tools == ["t1"]


class TestToolsBuilderCreateMcpTool:
    def test_create_mcp_tool_success(self):
        b = ToolsBuilder()
        tool = b.create_mcp_tool({"name": "my-mcp", "config": {"server_url": "http://s", "api_key": "k"}}, agent_name="a")
        assert isinstance(tool, MCPToolAdapter)
        assert tool.name == "my-mcp"

    def test_create_mcp_tool_default_name(self):
        assert ToolsBuilder().create_mcp_tool({"config": {"server_url": "http://s"}}).name == "gcp-mcp-tool"

    def test_create_mcp_tool_failure(self):
        with patch("root_agent.tools.tools_builder.MCPTool", side_effect=Exception("fail")):
            assert ToolsBuilder().create_mcp_tool({"name": "bad", "config": {}}) is None


class TestToolsBuilderCreateCustomTool:
    def test_create_custom_tool_returns_none(self):
        assert ToolsBuilder().create_custom_tool({"type": "my_type"}, agent_name="a") is None


class TestToolsBuilderCreateRagTool:
    @patch("root_agent.tools.tools_builder.create_rag_tool_from_yaml_config")
    def test_create_rag_tool_success(self, mock_create):
        mock_create.return_value = MagicMock()
        b = ToolsBuilder()
        b.set_global_config({"project_id": "p1"})
        assert b.create_rag_tool({"name": "rag1", "config": {}}, agent_name="a") is not None

    @patch("root_agent.tools.tools_builder.create_rag_tool_from_yaml_config", side_effect=Exception("fail"))
    def test_create_rag_tool_failure(self, mock_create):
        assert ToolsBuilder().create_rag_tool({"name": "bad"}, agent_name="a") is None


class TestBuildToolsFromYamlConfig:
    @patch("root_agent.tools.tools_builder.create_rag_tool_from_yaml_config")
    def test_rag_tools_built(self, mock_create):
        mock_create.return_value = MagicMock()
        b = ToolsBuilder()
        b.build_tools_from_yaml_config({"rag": [{"name": "r1", "config": {}}]}, agent_name="a")
        assert b.get_tool_count() == 1

    def test_mcp_tools_built(self):
        b = ToolsBuilder()
        b.build_tools_from_yaml_config({"mcp": [{"name": "m1", "config": {"server_url": "http://s"}}]}, agent_name="a")
        assert b.get_tool_count() == 1

    def test_custom_tools_built(self):
        b = ToolsBuilder()
        b.build_tools_from_yaml_config({"custom": [{"type": "my_type"}]}, agent_name="a")
        assert b.get_tool_count() == 0

    def test_unknown_tool_type_logged(self):
        b = ToolsBuilder()
        b.build_tools_from_yaml_config({"exotic": [{"name": "e1"}]}, agent_name="a")
        assert b.get_tool_count() == 0

    def test_enabled_tools_key_ignored(self):
        b = ToolsBuilder()
        b.build_tools_from_yaml_config({"enabled_tools": ["rag"], "mcp": [{"name": "m", "config": {"server_url": "http://s"}}]})
        assert b.get_tool_count() == 1

    def test_empty_config_returns_self(self):
        b = ToolsBuilder()
        assert b.build_tools_from_yaml_config(None) is b


class TestConvenienceFunctions:
    def test_create_tools_from_yaml_config_with_global(self):
        tools = create_tools_from_yaml_config({"mcp": [{"name": "m", "config": {"server_url": "http://s"}}]}, global_config={"project_id": "p1"})
        assert len(tools) == 1

    def test_create_tools_from_yaml_config_no_global(self):
        assert len(create_tools_from_yaml_config({"mcp": [{"name": "m", "config": {"server_url": "http://s"}}]})) == 1

    @patch("root_agent.tools.tools_builder.create_rag_tool_from_yaml_config")
    def test_create_rag_tools_from_yaml_config(self, mock_create):
        mock_create.return_value = MagicMock()
        assert len(create_rag_tools_from_yaml_config([{"name": "r1"}])) == 1

    @patch("root_agent.tools.tools_builder.create_rag_tool_from_yaml_config", return_value=None)
    def test_create_rag_tools_none_skipped(self, mock_create):
        assert len(create_rag_tools_from_yaml_config([{"name": "r1"}])) == 0

    def test_create_mcp_tools_from_yaml_config(self):
        assert len(create_mcp_tools_from_yaml_config([{"name": "m1"}])) == 0

    @patch("root_agent.tools.tools_builder.create_rag_tool_from_yaml_config")
    def test_create_tool_by_type_rag(self, mock_create):
        mock_create.return_value = MagicMock()
        assert create_tool_by_type("rag", {"name": "r1"}) is not None

    def test_create_tool_by_type_mcp(self):
        assert create_tool_by_type("mcp", {"name": "m1"}) is None

    def test_create_tool_by_type_custom(self):
        assert create_tool_by_type("custom", {"name": "c1"}) is None

    def test_create_tool_by_type_unknown(self):
        assert create_tool_by_type("exotic", {"name": "e1"}) is None
