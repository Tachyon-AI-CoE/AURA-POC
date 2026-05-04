"""Unit tests for MultiAgentBuilder and convenience functions."""

import sys
import os
import yaml
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))  # noqa: E402

from root_agent.multi_agent_builder import (  # noqa: E402
    MultiAgentBuilder,
    build_multi_agent_system,
    validate_config_file,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_ROOT_CONFIG = {
    "root_agent": {
        "agent_class": "LLMAgent",
        "model_id": "gemini-2.0-flash-001",
        "description": "Test root agent description",
        "instruction": "Test instruction",
        "agent_display_name": "test_root_agent",
    }
}


def _write_config(tmp_path, data):
    """Write a dict as YAML and return the file path string."""
    config_file = tmp_path / "agent-config.yaml"
    config_file.write_text(yaml.dump(data))
    return str(config_file)


def _mock_llm_builder(mock_agent):
    """Return a context manager that patches LlmAgentBuilder with mock_agent."""
    return patch("root_agent.multi_agent_builder.LlmAgentBuilder")


# ---------------------------------------------------------------------------
# __init__ / _load_config
# ---------------------------------------------------------------------------


class TestMultiAgentBuilderInit:
    def test_init_loads_valid_yaml(self, tmp_path):
        config_file = _write_config(tmp_path, MINIMAL_ROOT_CONFIG)
        builder = MultiAgentBuilder(config_file)
        assert builder.config == MINIMAL_ROOT_CONFIG

    def test_init_stores_config_path(self, tmp_path):
        config_file = _write_config(tmp_path, MINIMAL_ROOT_CONFIG)
        builder = MultiAgentBuilder(config_file)
        assert builder.config_path.name == "agent-config.yaml"

    def test_init_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            MultiAgentBuilder("/nonexistent/path/agent-config.yaml")

    def test_init_raises_on_invalid_yaml(self, tmp_path):
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("not: [valid: yaml: [}")
        with pytest.raises(Exception):
            MultiAgentBuilder(str(bad_file))

    def test_init_raises_on_empty_file(self, tmp_path):
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")
        with pytest.raises(ValueError, match="empty or invalid"):
            MultiAgentBuilder(str(empty_file))


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------


class TestValidateConfig:
    def test_valid_config_returns_true(self, tmp_path):
        config_file = _write_config(tmp_path, MINIMAL_ROOT_CONFIG)
        builder = MultiAgentBuilder(config_file)
        assert builder.validate_config() is True

    def test_missing_root_agent_raises(self, tmp_path):
        config_file = _write_config(tmp_path, {"agents": []})
        builder = MultiAgentBuilder(config_file)
        with pytest.raises(ValueError, match="Missing 'root_agent'"):
            builder.validate_config()

    def test_missing_required_field_instruction_raises(self, tmp_path):
        config = {
            "root_agent": {
                "agent_class": "LLMAgent",
                "model_id": "gemini-2.0-flash-001",
                "description": "desc",
                # 'instruction' is missing
            }
        }
        config_file = _write_config(tmp_path, config)
        builder = MultiAgentBuilder(config_file)
        with pytest.raises(ValueError, match="Missing required field 'instruction'"):
            builder.validate_config()

    def test_missing_required_field_description_raises(self, tmp_path):
        config = {
            "root_agent": {
                "agent_class": "LLMAgent",
                "model_id": "gemini-2.0-flash-001",
                "instruction": "do work",
                # 'description' is missing
            }
        }
        config_file = _write_config(tmp_path, config)
        builder = MultiAgentBuilder(config_file)
        with pytest.raises(ValueError, match="Missing required field 'description'"):
            builder.validate_config()

    def test_with_agents_list_validates_sub_agents(self, tmp_path):
        config = dict(MINIMAL_ROOT_CONFIG)
        config["agents"] = [
            {
                "name": "sub_agent",
                "agent_class": "LLMAgent",
                "model_id": "gemini-2.0-flash-001",
                "description": "Sub agent description",
                "instruction": "Sub agent instruction",
            }
        ]
        config_file = _write_config(tmp_path, config)
        builder = MultiAgentBuilder(config_file)
        assert builder.validate_config() is True

    def test_agents_missing_required_field_raises(self, tmp_path):
        config = dict(MINIMAL_ROOT_CONFIG)
        config["agents"] = [
            {
                "name": "broken_agent",
                "agent_class": "LLMAgent",
                "model_id": "gemini-2.0-flash-001",
                # 'description' and 'instruction' missing
            }
        ]
        config_file = _write_config(tmp_path, config)
        builder = MultiAgentBuilder(config_file)
        with pytest.raises(ValueError):
            builder.validate_config()


# ---------------------------------------------------------------------------
# _process_instructions
# ---------------------------------------------------------------------------


class TestProcessInstructions:
    def _builder(self, tmp_path):
        return MultiAgentBuilder(_write_config(tmp_path, MINIMAL_ROOT_CONFIG))

    def test_both_strings_combined(self, tmp_path):
        b = self._builder(tmp_path)
        result = b._process_instructions("do this", "global rule")
        assert "GLOBAL INSTRUCTIONS:" in result
        assert "global rule" in result
        assert "SPECIFIC INSTRUCTIONS:" in result
        assert "do this" in result

    def test_list_instruction_formats(self, tmp_path):
        b = self._builder(tmp_path)
        result = b._process_instructions(["step1", "step2"], ["global1", "global2"])
        assert "- step1" in result
        assert "- step2" in result
        assert "- global1" in result
        assert "- global2" in result

    def test_only_specific_instruction(self, tmp_path):
        b = self._builder(tmp_path)
        result = b._process_instructions("do this", "")
        assert "SPECIFIC INSTRUCTIONS:" in result
        assert "GLOBAL INSTRUCTIONS:" not in result

    def test_only_global_instruction(self, tmp_path):
        b = self._builder(tmp_path)
        result = b._process_instructions("", "global rule")
        assert "GLOBAL INSTRUCTIONS:" in result
        assert "SPECIFIC INSTRUCTIONS:" not in result

    def test_both_empty_returns_empty_string(self, tmp_path):
        b = self._builder(tmp_path)
        assert b._process_instructions("", "") == ""

    def test_none_values_returns_empty_string(self, tmp_path):
        b = self._builder(tmp_path)
        assert b._process_instructions(None, None) == ""


# ---------------------------------------------------------------------------
# build_agent dispatch
# ---------------------------------------------------------------------------


class TestBuildAgent:
    def _builder(self, tmp_path):
        return MultiAgentBuilder(_write_config(tmp_path, MINIMAL_ROOT_CONFIG))

    def test_empty_config_raises(self, tmp_path):
        b = self._builder(tmp_path)
        with pytest.raises(ValueError):
            b.build_agent({})

    def test_unsupported_class_raises(self, tmp_path):
        b = self._builder(tmp_path)
        with pytest.raises(ValueError, match="Unsupported agent class"):
            b.build_agent({"agent_class": "GhostAgent", "name": "x"})

    def test_build_llm_agent(self, tmp_path):
        b = self._builder(tmp_path)
        agent_config = {
            "agent_class": "LLMAgent",
            "name": "my_llm",
            "model_id": "gemini-2.0-flash-001",
            "description": "LLM desc",
            "instruction": "Do LLM work",
        }
        mock_agent = MagicMock()
        mock_agent.name = "my_llm"
        with patch("root_agent.multi_agent_builder.LlmAgentBuilder") as MockCls:
            inst = MockCls.return_value
            inst.from_yaml_config.return_value = inst
            inst.set_sub_agents.return_value = inst
            inst.apply_callbacks.return_value = inst
            inst.build.return_value = mock_agent
            result = b.build_agent(agent_config)
        assert result is mock_agent

    def test_build_loop_agent(self, tmp_path):
        b = self._builder(tmp_path)
        agent_config = {
            "agent_class": "LoopAgent",
            "name": "my_loop",
            "description": "Loop desc",
            "max_iterations": 3,
        }
        mock_agent = MagicMock()
        mock_agent.name = "my_loop"
        with patch("root_agent.multi_agent_builder.LoopAgentBuilder") as MockCls:
            inst = MockCls.return_value
            inst.set_name.return_value = inst
            inst.set_description.return_value = inst
            inst.set_max_iterations.return_value = inst
            inst.set_sub_agents.return_value = inst
            inst.build.return_value = mock_agent
            result = b.build_agent(agent_config)
        assert result is mock_agent

    def test_build_sequential_agent(self, tmp_path):
        b = self._builder(tmp_path)
        agent_config = {
            "agent_class": "SequentialAgent",
            "name": "my_seq",
            "description": "Seq desc",
        }
        mock_agent = MagicMock()
        with patch("root_agent.multi_agent_builder.SequentialAgentBuilder") as MockCls:
            inst = MockCls.return_value
            inst.set_name.return_value = inst
            inst.set_description.return_value = inst
            inst.set_sub_agents.return_value = inst
            inst.build.return_value = mock_agent
            result = b.build_agent(agent_config)
        assert result is mock_agent

    def test_build_parallel_agent(self, tmp_path):
        b = self._builder(tmp_path)
        agent_config = {
            "agent_class": "ParallelAgent",
            "name": "my_par",
            "description": "Par desc",
        }
        mock_agent = MagicMock()
        with patch("root_agent.multi_agent_builder.ParallelAgentBuilder") as MockCls:
            inst = MockCls.return_value
            inst.set_name.return_value = inst
            inst.set_description.return_value = inst
            inst.set_sub_agents.return_value = inst
            inst.build.return_value = mock_agent
            result = b.build_agent(agent_config)
        assert result is mock_agent


# ---------------------------------------------------------------------------
# build_agents_from_config
# ---------------------------------------------------------------------------


class TestBuildAgentsFromConfig:
    def test_no_agents_key_returns_empty(self, tmp_path):
        b = MultiAgentBuilder(_write_config(tmp_path, MINIMAL_ROOT_CONFIG))
        assert b.build_agents_from_config() == []

    def test_empty_agents_list_returns_empty(self, tmp_path):
        config = dict(MINIMAL_ROOT_CONFIG)
        config["agents"] = []
        b = MultiAgentBuilder(_write_config(tmp_path, config))
        assert b.build_agents_from_config() == []

    def test_builds_single_agent(self, tmp_path):
        config = dict(MINIMAL_ROOT_CONFIG)
        config["agents"] = [
            {
                "name": "agent1",
                "agent_class": "LLMAgent",
                "model_id": "gemini-2.0-flash-001",
                "description": "Agent 1 desc",
                "instruction": "Work 1",
            }
        ]
        b = MultiAgentBuilder(_write_config(tmp_path, config))
        mock_agent = MagicMock()
        mock_agent.name = "agent1"
        with patch("root_agent.multi_agent_builder.LlmAgentBuilder") as MockCls:
            inst = MockCls.return_value
            inst.from_yaml_config.return_value = inst
            inst.set_sub_agents.return_value = inst
            inst.apply_callbacks.return_value = inst
            inst.build.return_value = mock_agent
            agents = b.build_agents_from_config()
        assert len(agents) == 1
        assert agents[0] is mock_agent

    def test_failed_agent_skipped_others_returned(self, tmp_path):
        config = dict(MINIMAL_ROOT_CONFIG)
        config["agents"] = [
            {
                "name": "bad_agent",
                "agent_class": "LLMAgent",
                "model_id": "gemini-2.0-flash-001",
                "description": "Bad",
                "instruction": "Fail",
            },
            {
                "name": "good_agent",
                "agent_class": "LLMAgent",
                "model_id": "gemini-2.0-flash-001",
                "description": "Good",
                "instruction": "Work",
            },
        ]
        b = MultiAgentBuilder(_write_config(tmp_path, config))
        mock_good = MagicMock()
        mock_good.name = "good_agent"
        call_count = {"n": 0}

        def side_effect():
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("build failed")
            return mock_good

        with patch("root_agent.multi_agent_builder.LlmAgentBuilder") as MockCls:
            inst = MockCls.return_value
            inst.from_yaml_config.return_value = inst
            inst.set_sub_agents.return_value = inst
            inst.apply_callbacks.return_value = inst
            inst.build.side_effect = side_effect
            agents = b.build_agents_from_config()
        assert len(agents) == 1
        assert agents[0] is mock_good


# ---------------------------------------------------------------------------
# build_root_agent
# ---------------------------------------------------------------------------


class TestBuildRootAgent:
    def test_missing_root_agent_section_raises(self, tmp_path):
        b = MultiAgentBuilder(_write_config(tmp_path, {"agents": []}))
        with pytest.raises(ValueError, match="No root_agent"):
            b.build_root_agent()

    def test_builds_root_agent_without_sub_agents(self, tmp_path):
        b = MultiAgentBuilder(_write_config(tmp_path, MINIMAL_ROOT_CONFIG))
        mock_agent = MagicMock()
        mock_agent.name = "test_root_agent"
        mock_agent.sub_agents = []
        with patch("root_agent.multi_agent_builder.LlmAgentBuilder") as MockCls:
            inst = MockCls.return_value
            inst.from_yaml_config.return_value = inst
            inst.set_sub_agents.return_value = inst
            inst.build.return_value = mock_agent
            result = b.build_root_agent(include_sub_agents=False)
        assert result is mock_agent

    def test_sets_global_instruction_attribute(self, tmp_path):
        config = {
            "root_agent": {
                "agent_class": "LLMAgent",
                "model_id": "gemini-2.0-flash-001",
                "description": "desc",
                "instruction": "inst",
                "agent_display_name": "myagent",
                "global_instruction": "Always be helpful",
            }
        }
        b = MultiAgentBuilder(_write_config(tmp_path, config))
        mock_agent = MagicMock()
        mock_agent.name = "myagent"
        mock_agent.sub_agents = []
        with patch("root_agent.multi_agent_builder.LlmAgentBuilder") as MockCls:
            inst = MockCls.return_value
            inst.from_yaml_config.return_value = inst
            inst.set_sub_agents.return_value = inst
            inst.build.return_value = mock_agent
            result = b.build_root_agent(include_sub_agents=False)
        assert hasattr(result, "global_instruction")
        assert result.global_instruction == "Always be helpful"

    def test_non_llm_root_agent_class_logs_warning(self, tmp_path):
        config = {
            "root_agent": {
                "agent_class": "LoopAgent",
                "model_id": "gemini-2.0-flash-001",
                "description": "desc",
                "instruction": "inst",
                "agent_display_name": "myagent",
            }
        }
        b = MultiAgentBuilder(_write_config(tmp_path, config))
        mock_agent = MagicMock()
        mock_agent.sub_agents = []
        with patch("root_agent.multi_agent_builder.LlmAgentBuilder") as MockCls:
            inst = MockCls.return_value
            inst.from_yaml_config.return_value = inst
            inst.set_sub_agents.return_value = inst
            inst.build.return_value = mock_agent
            # Should NOT raise - just logs warning
            result = b.build_root_agent(include_sub_agents=False)
        assert result is mock_agent


# ---------------------------------------------------------------------------
# get_agent_count
# ---------------------------------------------------------------------------


class TestGetAgentCount:
    def test_single_agent_count(self, tmp_path):
        b = MultiAgentBuilder(_write_config(tmp_path, MINIMAL_ROOT_CONFIG))
        mock_agent = MagicMock()
        mock_agent.sub_agents = []
        # type(mock_agent).__name__ would be "MagicMock"
        counts = b.get_agent_count(mock_agent)
        assert counts.get("MagicMock", 0) == 1

    def test_nested_agent_count(self, tmp_path):
        b = MultiAgentBuilder(_write_config(tmp_path, MINIMAL_ROOT_CONFIG))
        sub1 = MagicMock()
        sub1.sub_agents = []
        sub2 = MagicMock()
        sub2.sub_agents = []
        root = MagicMock()
        root.sub_agents = [sub1, sub2]
        counts = b.get_agent_count(root)
        assert sum(counts.values()) == 3


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


class TestConvenienceFunctions:
    def test_validate_config_file_valid(self, tmp_path):
        config_file = _write_config(tmp_path, MINIMAL_ROOT_CONFIG)
        assert validate_config_file(config_file) is True

    def test_validate_config_file_missing_root_raises(self, tmp_path):
        config_file = _write_config(tmp_path, {"agents": []})
        with pytest.raises(ValueError):
            validate_config_file(config_file)

    def test_build_multi_agent_system(self, tmp_path):
        config_file = _write_config(tmp_path, MINIMAL_ROOT_CONFIG)
        mock_agent = MagicMock()
        mock_agent.name = "test_root_agent"
        mock_agent.sub_agents = []
        with patch("root_agent.multi_agent_builder.LlmAgentBuilder") as MockCls:
            inst = MockCls.return_value
            inst.from_yaml_config.return_value = inst
            inst.set_sub_agents.return_value = inst
            inst.build.return_value = mock_agent
            result = build_multi_agent_system(config_file)
        assert result is mock_agent

    def test_build_multi_agent_system_failure(self, tmp_path):
        config_file = _write_config(tmp_path, {"agents": []})
        with pytest.raises(ValueError):
            build_multi_agent_system(config_file)


# ---------------------------------------------------------------------------
# _build_sub_agents
# ---------------------------------------------------------------------------


class TestBuildSubAgents:
    def _builder(self, tmp_path):
        return MultiAgentBuilder(_write_config(tmp_path, MINIMAL_ROOT_CONFIG))

    def test_empty_sub_agents_returns_empty(self, tmp_path):
        b = self._builder(tmp_path)
        assert b._build_sub_agents([]) == []

    def test_builds_sub_agents_recursively(self, tmp_path):
        b = self._builder(tmp_path)
        sub_config = [
            {
                "name": "sub1",
                "agent_class": "LLMAgent",
                "model_id": "gemini-2.0-flash-001",
                "description": "Sub1 desc",
                "instruction": "Do sub1",
            }
        ]
        mock_agent = MagicMock()
        mock_agent.name = "sub1"
        with patch("root_agent.multi_agent_builder.LlmAgentBuilder") as MockCls:
            inst = MockCls.return_value
            inst.from_yaml_config.return_value = inst
            inst.set_sub_agents.return_value = inst
            inst.apply_callbacks.return_value = inst
            inst.build.return_value = mock_agent
            result = b._build_sub_agents(sub_config)
        assert len(result) == 1
        assert result[0] is mock_agent

    def test_failed_sub_agent_skipped(self, tmp_path):
        b = self._builder(tmp_path)
        sub_config = [
            {"name": "bad", "agent_class": "LLMAgent", "description": "d", "instruction": "i"},
            {"name": "good", "agent_class": "LLMAgent", "description": "d", "instruction": "i"},
        ]
        call_count = {"n": 0}
        mock_good = MagicMock()
        mock_good.name = "good"

        def side_effect():
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("fail")
            return mock_good

        with patch("root_agent.multi_agent_builder.LlmAgentBuilder") as MockCls:
            inst = MockCls.return_value
            inst.from_yaml_config.return_value = inst
            inst.set_sub_agents.return_value = inst
            inst.apply_callbacks.return_value = inst
            inst.build.side_effect = side_effect
            result = b._build_sub_agents(sub_config)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# _build_llm_agent with sub_agents
# ---------------------------------------------------------------------------


class TestBuildLlmAgentWithSubAgents:
    def test_llm_agent_with_sub_agents(self, tmp_path):
        b = MultiAgentBuilder(_write_config(tmp_path, MINIMAL_ROOT_CONFIG))
        agent_config = {
            "agent_class": "LLMAgent",
            "name": "parent_llm",
            "model_id": "gemini-2.0-flash-001",
            "description": "Parent",
            "instruction": "Do work",
            "sub_agents": [
                {"name": "child", "agent_class": "LLMAgent", "model_id": "gemini-2.0-flash-001",
                 "description": "Child", "instruction": "Child work"}
            ],
        }
        mock_child = MagicMock()
        mock_child.name = "child"
        mock_parent = MagicMock()
        mock_parent.name = "parent_llm"
        with patch("root_agent.multi_agent_builder.LlmAgentBuilder") as MockCls:
            inst = MockCls.return_value
            inst.from_yaml_config.return_value = inst
            inst.set_sub_agents.return_value = inst
            inst.apply_callbacks.return_value = inst
            inst.build.return_value = mock_parent
            result = b._build_llm_agent(agent_config)
        assert result is mock_parent
        inst.set_sub_agents.assert_called()

    def test_llm_agent_build_failure(self, tmp_path):
        b = MultiAgentBuilder(_write_config(tmp_path, MINIMAL_ROOT_CONFIG))
        agent_config = {"name": "fail_llm", "description": "d", "instruction": "i"}
        with patch("root_agent.multi_agent_builder.LlmAgentBuilder") as MockCls:
            inst = MockCls.return_value
            inst.from_yaml_config.side_effect = Exception("boom")
            with pytest.raises(Exception):
                b._build_llm_agent(agent_config)


# ---------------------------------------------------------------------------
# _build_loop/sequential/parallel_agent with sub_agents and exceptions
# ---------------------------------------------------------------------------


class TestBuildAgentTypesWithSubAgents:
    def _builder(self, tmp_path):
        return MultiAgentBuilder(_write_config(tmp_path, MINIMAL_ROOT_CONFIG))

    def test_loop_agent_with_sub_agents(self, tmp_path):
        b = self._builder(tmp_path)
        config = {
            "name": "loop1", "description": "d", "max_iterations": 3,
            "sub_agents": [{"name": "s", "agent_class": "LLMAgent", "description": "d", "instruction": "i"}],
        }
        mock_sub = MagicMock()
        mock_sub.name = "s"
        mock_loop = MagicMock()
        mock_loop.name = "loop1"
        with patch("root_agent.multi_agent_builder.LlmAgentBuilder") as MockLlm, \
             patch("root_agent.multi_agent_builder.LoopAgentBuilder") as MockLoop:
            llm_inst = MockLlm.return_value
            llm_inst.from_yaml_config.return_value = llm_inst
            llm_inst.set_sub_agents.return_value = llm_inst
            llm_inst.apply_callbacks.return_value = llm_inst
            llm_inst.build.return_value = mock_sub
            loop_inst = MockLoop.return_value
            loop_inst.set_name.return_value = loop_inst
            loop_inst.set_description.return_value = loop_inst
            loop_inst.set_max_iterations.return_value = loop_inst
            loop_inst.set_sub_agents.return_value = loop_inst
            loop_inst.build.return_value = mock_loop
            result = b._build_loop_agent(config)
        assert result is mock_loop
        loop_inst.set_sub_agents.assert_called()

    def test_loop_agent_build_failure(self, tmp_path):
        b = self._builder(tmp_path)
        with patch("root_agent.multi_agent_builder.LoopAgentBuilder") as MockCls:
            inst = MockCls.return_value
            inst.set_name.return_value = inst
            inst.set_description.return_value = inst
            inst.set_max_iterations.return_value = inst
            inst.build.side_effect = Exception("boom")
            with pytest.raises(Exception):
                b._build_loop_agent({"name": "l", "description": "d"})

    def test_sequential_agent_with_sub_agents(self, tmp_path):
        b = self._builder(tmp_path)
        config = {
            "name": "seq1", "description": "d",
            "sub_agents": [{"name": "s", "agent_class": "LLMAgent", "description": "d", "instruction": "i"}],
        }
        mock_sub = MagicMock()
        mock_sub.name = "s"
        mock_seq = MagicMock()
        mock_seq.name = "seq1"
        with patch("root_agent.multi_agent_builder.LlmAgentBuilder") as MockLlm, \
             patch("root_agent.multi_agent_builder.SequentialAgentBuilder") as MockSeq:
            llm_inst = MockLlm.return_value
            llm_inst.from_yaml_config.return_value = llm_inst
            llm_inst.set_sub_agents.return_value = llm_inst
            llm_inst.apply_callbacks.return_value = llm_inst
            llm_inst.build.return_value = mock_sub
            seq_inst = MockSeq.return_value
            seq_inst.set_name.return_value = seq_inst
            seq_inst.set_description.return_value = seq_inst
            seq_inst.set_sub_agents.return_value = seq_inst
            seq_inst.build.return_value = mock_seq
            result = b._build_sequential_agent(config)
        assert result is mock_seq
        seq_inst.set_sub_agents.assert_called()

    def test_sequential_agent_build_failure(self, tmp_path):
        b = self._builder(tmp_path)
        with patch("root_agent.multi_agent_builder.SequentialAgentBuilder") as MockCls:
            inst = MockCls.return_value
            inst.set_name.return_value = inst
            inst.set_description.return_value = inst
            inst.build.side_effect = Exception("boom")
            with pytest.raises(Exception):
                b._build_sequential_agent({"name": "s", "description": "d"})

    def test_parallel_agent_with_sub_agents(self, tmp_path):
        b = self._builder(tmp_path)
        config = {
            "name": "par1", "description": "d",
            "sub_agents": [{"name": "s", "agent_class": "LLMAgent", "description": "d", "instruction": "i"}],
        }
        mock_sub = MagicMock()
        mock_sub.name = "s"
        mock_par = MagicMock()
        mock_par.name = "par1"
        with patch("root_agent.multi_agent_builder.LlmAgentBuilder") as MockLlm, \
             patch("root_agent.multi_agent_builder.ParallelAgentBuilder") as MockPar:
            llm_inst = MockLlm.return_value
            llm_inst.from_yaml_config.return_value = llm_inst
            llm_inst.set_sub_agents.return_value = llm_inst
            llm_inst.apply_callbacks.return_value = llm_inst
            llm_inst.build.return_value = mock_sub
            par_inst = MockPar.return_value
            par_inst.set_name.return_value = par_inst
            par_inst.set_description.return_value = par_inst
            par_inst.set_sub_agents.return_value = par_inst
            par_inst.build.return_value = mock_par
            result = b._build_parallel_agent(config)
        assert result is mock_par
        par_inst.set_sub_agents.assert_called()

    def test_parallel_agent_build_failure(self, tmp_path):
        b = self._builder(tmp_path)
        with patch("root_agent.multi_agent_builder.ParallelAgentBuilder") as MockCls:
            inst = MockCls.return_value
            inst.set_name.return_value = inst
            inst.set_description.return_value = inst
            inst.build.side_effect = Exception("boom")
            with pytest.raises(Exception):
                b._build_parallel_agent({"name": "p", "description": "d"})


# ---------------------------------------------------------------------------
# build_root_agent with multiagent + exception
# ---------------------------------------------------------------------------


class TestBuildRootAgentExtended:
    def test_multiagent_builds_sub_agents(self, tmp_path):
        config = {
            "root_agent": {
                "agent_class": "LLMAgent",
                "model_id": "gemini-2.0-flash-001",
                "description": "desc",
                "instruction": "inst",
                "agent_display_name": "root",
                "multiagent": True,
            },
            "agents": [
                {"name": "a1", "agent_class": "LLMAgent", "model_id": "gemini-2.0-flash-001",
                 "description": "d", "instruction": "i"}
            ],
        }
        b = MultiAgentBuilder(_write_config(tmp_path, config))
        mock_agent = MagicMock()
        mock_agent.name = "root"
        mock_agent.sub_agents = [MagicMock()]
        with patch("root_agent.multi_agent_builder.LlmAgentBuilder") as MockCls:
            inst = MockCls.return_value
            inst.from_yaml_config.return_value = inst
            inst.set_sub_agents.return_value = inst
            inst.apply_callbacks.return_value = inst
            inst.build.return_value = mock_agent
            result = b.build_root_agent(include_sub_agents=True)
        assert result is mock_agent
        # set_sub_agents should be called for the root agent
        inst.set_sub_agents.assert_called()

    def test_build_root_agent_exception(self, tmp_path):
        b = MultiAgentBuilder(_write_config(tmp_path, MINIMAL_ROOT_CONFIG))
        with patch("root_agent.multi_agent_builder.LlmAgentBuilder") as MockCls:
            inst = MockCls.return_value
            inst.from_yaml_config.side_effect = Exception("boom")
            with pytest.raises(Exception):
                b.build_root_agent()


# ---------------------------------------------------------------------------
# _validate_agent_config — unsupported class warning
# ---------------------------------------------------------------------------


class TestValidateAgentConfigWarnings:
    def test_unsupported_root_agent_class_warns(self, tmp_path):
        config = {
            "root_agent": {
                "agent_class": "CustomAgent",
                "model_id": "gemini-2.0-flash-001",
                "description": "desc",
                "instruction": "inst",
            }
        }
        b = MultiAgentBuilder(_write_config(tmp_path, config))
        # Should not raise, just warns
        assert b.validate_config() is True

    def test_unsupported_sub_agent_class_warns(self, tmp_path):
        config = {
            "root_agent": {
                "agent_class": "LLMAgent",
                "model_id": "gemini-2.0-flash-001",
                "description": "desc",
                "instruction": "inst",
            },
            "agents": [
                {
                    "name": "weird",
                    "agent_class": "WeirdAgent",
                    "model_id": "gemini-2.0-flash-001",
                    "description": "d",
                    "instruction": "i",
                }
            ],
        }
        b = MultiAgentBuilder(_write_config(tmp_path, config))
        assert b.validate_config() is True


# ---------------------------------------------------------------------------
# print_agent_hierarchy
# ---------------------------------------------------------------------------


class TestPrintAgentHierarchy:
    def test_with_agent(self, tmp_path):
        b = MultiAgentBuilder(_write_config(tmp_path, MINIMAL_ROOT_CONFIG))
        mock_agent = MagicMock()
        mock_agent.name = "root"
        mock_agent.sub_agents = []
        # Should not raise
        b.print_agent_hierarchy(mock_agent)

    def test_with_nested_agents(self, tmp_path):
        b = MultiAgentBuilder(_write_config(tmp_path, MINIMAL_ROOT_CONFIG))
        child = MagicMock()
        child.name = "child"
        child.sub_agents = []
        root = MagicMock()
        root.name = "root"
        root.sub_agents = [child]
        b.print_agent_hierarchy(root)

    def test_with_none_agent(self, tmp_path):
        b = MultiAgentBuilder(_write_config(tmp_path, MINIMAL_ROOT_CONFIG))
        mock_agent = MagicMock()
        mock_agent.name = "root"
        mock_agent.sub_agents = []
        with patch.object(b, "build_root_agent", return_value=mock_agent):
            b.print_agent_hierarchy(None)

    def test_with_build_failure(self, tmp_path):
        b = MultiAgentBuilder(_write_config(tmp_path, MINIMAL_ROOT_CONFIG))
        with patch.object(b, "build_root_agent", side_effect=Exception("fail")):
            # Should not raise, just logs error
            b.print_agent_hierarchy(None)


# ---------------------------------------------------------------------------
# get_agent_count without passing agent
# ---------------------------------------------------------------------------


class TestGetAgentCountExtended:
    def test_count_without_agent_arg(self, tmp_path):
        b = MultiAgentBuilder(_write_config(tmp_path, MINIMAL_ROOT_CONFIG))
        mock_agent = MagicMock()
        mock_agent.sub_agents = []
        with patch.object(b, "build_root_agent", return_value=mock_agent):
            counts = b.get_agent_count()
        assert sum(counts.values()) == 1
