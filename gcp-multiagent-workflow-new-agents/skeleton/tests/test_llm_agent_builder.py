"""Tests for root_agent/sub_agents/llm_agent.py — LlmAgentBuilder."""

import sys
import os
import types

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import pytest
from unittest.mock import patch, MagicMock
from root_agent.sub_agents.llm_agent import LlmAgentBuilder


# ---------------------------------------------------------------------------
# Basic setters (original tests)
# ---------------------------------------------------------------------------

def test_llm_agent_builder_setters():
    builder = LlmAgentBuilder()
    builder.set_name("test").set_description("desc").set_instruction("do this")
    builder.set_disallow_transfer_to_parent(False)
    builder.set_disallow_transfer_to_peers(False)
    builder.set_output_key("output")
    assert builder._name == "test"
    assert builder._description == "desc"
    assert builder._instruction == "do this"
    assert builder._disallow_transfer_to_parent is False
    assert builder._disallow_transfer_to_peers is False
    assert builder._output_key == "output"

def test_llm_agent_builder_add_sub_agents():
    builder = LlmAgentBuilder()
    dummy_agent = object()
    builder.add_sub_agent(dummy_agent)
    assert dummy_agent in builder._sub_agents
    builder.set_sub_agents([dummy_agent])
    assert builder._sub_agents == [dummy_agent]
    builder.add_sub_agents([dummy_agent, dummy_agent])
    assert builder._sub_agents.count(dummy_agent) >= 3

def test_llm_agent_builder_generate_content_config():
    builder = LlmAgentBuilder()
    config = builder._generate_content_config
    assert hasattr(config, "temperature")
    assert hasattr(config, "top_p")


# ---------------------------------------------------------------------------
# Extended setters
# ---------------------------------------------------------------------------

class TestLlmAgentBuilderSetters:
    def test_set_model(self):
        b = LlmAgentBuilder()
        ret = b.set_model("gemini-2.0-flash")
        assert b._model == "gemini-2.0-flash"
        assert ret is b

    def test_add_tool(self):
        b = LlmAgentBuilder()
        b.add_tool("t1")
        assert "t1" in b._tools

    def test_add_tools(self):
        b = LlmAgentBuilder()
        b.add_tools(["t1", "t2"])
        assert b._tools == ["t1", "t2"]

    def test_set_tools(self):
        b = LlmAgentBuilder()
        b.add_tool("old")
        b.set_tools(["new1", "new2"])
        assert b._tools == ["new1", "new2"]

    def test_set_generate_content_config(self):
        from google.genai.types import GenerateContentConfig
        b = LlmAgentBuilder()
        cfg = GenerateContentConfig(temperature=0.9)
        b.set_generate_content_config(cfg)
        assert b._generate_content_config is cfg

    def test_set_temperature(self):
        b = LlmAgentBuilder()
        b.set_temperature(0.7)
        assert b._generate_content_config.temperature == 0.7

    def test_set_temperature_creates_config_if_none(self):
        b = LlmAgentBuilder()
        b._generate_content_config = None
        b.set_temperature(0.5)
        assert b._generate_content_config is not None
        assert b._generate_content_config.temperature == 0.5

    def test_set_top_p(self):
        b = LlmAgentBuilder()
        b.set_top_p(0.9)
        assert b._generate_content_config.top_p == 0.9

    def test_set_top_p_creates_config_if_none(self):
        b = LlmAgentBuilder()
        b._generate_content_config = None
        b.set_top_p(0.8)
        assert b._generate_content_config is not None
        assert b._generate_content_config.top_p == 0.8

    def test_set_before_agent_callback(self):
        b = LlmAgentBuilder()
        cb = lambda: None
        b.set_before_agent_callback(cb)
        assert b._before_agent_callback is cb

    def test_set_after_agent_callback(self):
        b = LlmAgentBuilder()
        cb = lambda: None
        b.set_after_agent_callback(cb)
        assert b._after_agent_callback is cb

    def test_set_before_model_callback(self):
        b = LlmAgentBuilder()
        cb = lambda: None
        b.set_before_model_callback(cb)
        assert b._before_model_callback is cb

    def test_set_after_model_callback(self):
        b = LlmAgentBuilder()
        cb = lambda: None
        b.set_after_model_callback(cb)
        assert b._after_model_callback is cb

    def test_set_global_config(self):
        b = LlmAgentBuilder()
        b.set_global_config({"project_id": "p1"})
        assert b._global_config == {"project_id": "p1"}

    def test_clear_sub_agents(self):
        b = LlmAgentBuilder()
        b.add_sub_agent("a1")
        b.clear_sub_agents()
        assert b._sub_agents == []

    def test_clear_tools(self):
        b = LlmAgentBuilder()
        b.add_tool("t1")
        b.clear_tools()
        assert b._tools == []


# ---------------------------------------------------------------------------
# apply_callbacks
# ---------------------------------------------------------------------------

class TestApplyCallbacks:
    def test_apply_callbacks_sets_default_before_model(self):
        b = LlmAgentBuilder()
        b.set_name("test")
        b.apply_callbacks()
        assert b._before_model_callback is not None

    def test_apply_callbacks_does_not_override_existing(self):
        b = LlmAgentBuilder()
        custom_cb = lambda ctx, req: None
        b.set_before_model_callback(custom_cb)
        b.apply_callbacks()
        assert b._before_model_callback is custom_cb


# ---------------------------------------------------------------------------
# from_yaml_config
# ---------------------------------------------------------------------------

class TestFromYamlConfig:
    @patch("root_agent.sub_agents.llm_agent.create_tools_from_yaml_config", return_value=[])
    def test_basic_config(self, mock_tools):
        b = LlmAgentBuilder()
        config = {"name": "agent1", "description": "desc1", "model_id": "gemini-2.0-flash", "instruction": "do stuff"}
        b.from_yaml_config(config)
        assert b._name == "agent1"
        assert b._description == "desc1"
        assert b._model == "gemini-2.0-flash"
        assert b._instruction == "do stuff"

    @patch("root_agent.sub_agents.llm_agent.create_tools_from_yaml_config", return_value=[])
    def test_list_instruction(self, mock_tools):
        b = LlmAgentBuilder()
        b.from_yaml_config({"name": "a", "description": "d", "instruction": ["step1", "step2"]})
        assert "- step1" in b._instruction
        assert "- step2" in b._instruction

    @patch("root_agent.sub_agents.llm_agent.create_tools_from_yaml_config", return_value=[])
    def test_output_key_appended_to_instruction(self, mock_tools):
        b = LlmAgentBuilder()
        b.from_yaml_config({"name": "a", "description": "d", "instruction": "base", "output_key": "result"})
        assert "result" in b._instruction
        assert b._output_key == "result"

    @patch("root_agent.sub_agents.llm_agent.create_tools_from_yaml_config", return_value=[])
    def test_output_key_with_empty_instruction(self, mock_tools):
        b = LlmAgentBuilder()
        b.from_yaml_config({"name": "a", "description": "d", "output_key": "res"})
        assert "Output Key: res" in b._instruction

    @patch("root_agent.sub_agents.llm_agent.create_tools_from_yaml_config", return_value=[])
    def test_llm_config_temperature_and_top_p(self, mock_tools):
        b = LlmAgentBuilder()
        b.from_yaml_config({"name": "a", "description": "d", "llm_config": {"temperature": 0.8, "top_p": 0.95}})
        assert b._generate_content_config.temperature == 0.8
        assert b._generate_content_config.top_p == 0.95

    @patch("root_agent.sub_agents.llm_agent.create_tools_from_yaml_config", return_value=[])
    def test_llm_config_extended_params(self, mock_tools):
        b = LlmAgentBuilder()
        b.from_yaml_config({"name": "a", "description": "d", "llm_config": {"temperature": 0.5, "top_p": 0.7, "top_k": 40, "max_output_tokens": 1024}})
        assert b._generate_content_config.top_k == 40
        assert b._generate_content_config.max_output_tokens == 1024

    @patch("root_agent.sub_agents.llm_agent.create_tools_from_yaml_config", return_value=["tool1"])
    def test_tools_from_config(self, mock_tools):
        b = LlmAgentBuilder()
        b.from_yaml_config({"name": "a", "description": "d", "tools": {"rag": [{"name": "r1"}]}}, global_config={"project_id": "p1"})
        assert b._tools == ["tool1"]
        assert b._global_config == {"project_id": "p1"}

    @patch("root_agent.sub_agents.llm_agent.create_tools_from_yaml_config", side_effect=Exception("fail"))
    def test_tools_creation_failure_handled(self, mock_tools):
        b = LlmAgentBuilder()
        b.from_yaml_config({"name": "a", "description": "d", "tools": {"rag": [{"name": "r1"}]}})
        assert b._tools == []

    @patch("root_agent.sub_agents.llm_agent.create_tools_from_yaml_config", return_value=[])
    def test_defaults_when_config_empty(self, mock_tools):
        b = LlmAgentBuilder()
        b.from_yaml_config({})
        assert b._name == "unnamed_agent"
        assert b._model == "gemini-2.0-flash-001"


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

class TestBuild:
    def test_build_success(self):
        b = LlmAgentBuilder()
        b.set_name("a").set_model("m").set_description("d").set_instruction("i")
        assert b.build().name == "a"

    def test_build_missing_name_raises(self):
        b = LlmAgentBuilder()
        b.set_model("m").set_description("d")
        with pytest.raises(ValueError, match="name"):
            b.build()

    def test_build_missing_model_raises(self):
        b = LlmAgentBuilder()
        b.set_name("a").set_description("d")
        with pytest.raises(ValueError, match="Model"):
            b.build()

    def test_build_missing_description_raises(self):
        b = LlmAgentBuilder()
        b.set_name("a").set_model("m")
        with pytest.raises(ValueError, match="description"):
            b.build()

    def test_build_with_all_options(self):
        cb = lambda: None
        b = LlmAgentBuilder()
        b.set_name("a").set_model("m").set_description("d").set_instruction("i")
        b.set_output_key("out")
        b.set_before_agent_callback(cb).set_after_agent_callback(cb)
        b.set_before_model_callback(cb).set_after_model_callback(cb)
        assert b.build().name == "a"


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_clears_all_fields(self):
        b = LlmAgentBuilder()
        b.set_name("a").set_model("m").set_description("d")
        b.set_instruction("i").set_output_key("o")
        b.add_tool("t").add_sub_agent("s")
        b.set_global_config({"k": "v"})
        b.set_before_agent_callback(lambda: None)
        b.set_after_agent_callback(lambda: None)
        b.reset()
        assert b._name is None
        assert b._model is None
        assert b._description is None
        assert b._tools == []
        assert b._sub_agents == []
        assert b._global_config is None
        assert b._before_agent_callback is None
