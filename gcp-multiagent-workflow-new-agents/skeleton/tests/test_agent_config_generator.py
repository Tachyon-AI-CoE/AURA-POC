"""Tests for config/agent_config_generator.py — all functions."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import pytest
import json
import yaml
import importlib
import config.agent_config_generator as acg


# ---------------------------------------------------------------------------
# Original tests
# ---------------------------------------------------------------------------

def test_load_agents_from_json_success(tmp_path):
    agents = [{"name": "agent1"}, {"name": "agent2"}]
    json_file = tmp_path / "agents.json"
    json_file.write_text(json.dumps(agents))
    result = acg.load_agents_from_json(str(json_file))
    assert isinstance(result, list)
    assert result[0]["name"] == "agent1"
    assert result[1]["name"] == "agent2"

def test_load_agents_from_json_file_not_found():
    with pytest.raises(FileNotFoundError):
        acg.load_agents_from_json("nonexistent.json")

def test_load_agents_from_json_invalid_json(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not valid json")
    with pytest.raises(json.JSONDecodeError):
        acg.load_agents_from_json(str(bad_file))

def test_mcp_server_registry_env(monkeypatch):
    monkeypatch.setenv("GCP_JIRA_MCP_URL", "http://custom-url")
    importlib.reload(acg)
    assert acg.MCP_SERVER_REGISTRY["gcp-jira-mcp"]["server_url"] == "http://custom-url"


# ---------------------------------------------------------------------------
# load_root_agent_config
# ---------------------------------------------------------------------------

class TestLoadRootAgentConfig:
    def test_loads_valid_yaml(self, tmp_path):
        data = {"root_agent": {"project_id": "proj", "model_id": "gemini"}}
        yaml_file = tmp_path / "root-agent-config.yaml"
        yaml_file.write_text(yaml.dump(data))
        result = acg.load_root_agent_config(str(yaml_file))
        assert result["root_agent"]["project_id"] == "proj"

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            acg.load_root_agent_config("/nonexistent/root-agent-config.yaml")

    def test_invalid_yaml_raises(self, tmp_path):
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("not: [valid: yaml: [}")
        with pytest.raises(Exception):
            acg.load_root_agent_config(str(bad_file))

    def test_returns_dict(self, tmp_path):
        data = {"key": "value"}
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml.dump(data))
        result = acg.load_root_agent_config(str(yaml_file))
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# transform_rag_config
# ---------------------------------------------------------------------------

class TestTransformRagConfig:
    def test_no_rag_key_returns_empty(self):
        assert acg.transform_rag_config({"mcp": {}}) == []

    def test_empty_rag_list(self):
        result = acg.transform_rag_config({"rag": []})
        assert result == []

    def test_single_rag_item_with_details(self):
        tools = {
            "rag": [
                {
                    "rag_details": {
                        "value": {
                            "datasetname": "my_dataset",
                            "vectorizeddatasetbaseid": "corpus_123",
                            "description": "My RAG corpus",
                        }
                    }
                }
            ]
        }
        result = acg.transform_rag_config(tools)
        assert len(result) == 1
        assert result[0]["name"] == "my_dataset"
        assert result[0]["description"] == "My RAG corpus"
        assert result[0]["config"]["rag_resources"] == [
            {"rag_resource": "corpus_123"}
        ]

    def test_rag_item_without_rag_details(self):
        tools = {"rag": [{"resource_id": "res_abc"}]}
        result = acg.transform_rag_config(tools)
        assert len(result) == 1
        assert result[0]["config"]["rag_resources"] == [{"rag_resource": "res_abc"}]

    def test_rag_item_without_resource_id_empty_rag_resources(self):
        tools = {
            "rag": [
                {
                    "rag_details": {
                        "value": {
                            "datasetname": "empty_ds",
                            "vectorizeddatasetbaseid": "",
                            "description": "",
                        }
                    }
                }
            ]
        }
        result = acg.transform_rag_config(tools)
        assert result[0]["config"]["rag_resources"] == []

    def test_non_list_rag_wrapped_in_list(self):
        tools = {
            "rag": {
                "rag_details": {
                    "value": {
                        "datasetname": "single",
                        "vectorizeddatasetbaseid": "c1",
                        "description": "",
                    }
                }
            }
        }
        result = acg.transform_rag_config(tools)
        assert len(result) == 1
        assert result[0]["name"] == "single"

    def test_optional_rag_fields_copied(self):
        tools = {
            "rag": [
                {
                    "rag_details": {
                        "value": {
                            "datasetname": "ds",
                            "vectorizeddatasetbaseid": "c1",
                            "description": "",
                        }
                    },
                    "vector_distance_threshold": 0.5,
                    "similarity_top_k": 10,
                }
            ]
        }
        result = acg.transform_rag_config(tools)
        assert result[0]["config"]["vector_distance_threshold"] == 0.5
        assert result[0]["config"]["similarity_top_k"] == 10


# ---------------------------------------------------------------------------
# transform_mcp_config
# ---------------------------------------------------------------------------

class TestTransformMcpConfig:
    def test_no_mcp_key_returns_empty(self):
        assert acg.transform_mcp_config({"rag": {}}) == []

    def test_mcp_list_returned_as_is(self):
        mcp_list = [{"name": "server1"}, {"name": "server2"}]
        result = acg.transform_mcp_config({"mcp": mcp_list})
        assert result == mcp_list

    def test_mcp_dict_with_known_registry_server(self, monkeypatch):
        monkeypatch.setattr(
            acg,
            "MCP_SERVER_REGISTRY",
            {
                "gcp-jira-mcp": {
                    "server_url": "http://jira-mcp.test",
                    "api_key_env": "JIRA_KEY",
                    "base_path": "/mcp/jira",
                    "health_path": "/mcp/jira/health",
                }
            },
        )
        monkeypatch.setenv("JIRA_KEY", "secret")
        result = acg.transform_mcp_config(
            {"mcp": {"mcp_servers": ["gcp-jira-mcp"]}}
        )
        assert len(result) == 1
        assert result[0]["name"] == "gcp-jira-mcp"
        assert result[0]["config"]["server_url"] == "http://jira-mcp.test"

    def test_mcp_dict_unknown_server_skipped(self, monkeypatch):
        monkeypatch.setattr(acg, "MCP_SERVER_REGISTRY", {})
        result = acg.transform_mcp_config(
            {"mcp": {"mcp_servers": ["unknown-mcp-server"]}}
        )
        assert result == []

    def test_mcp_empty_dict_returns_empty(self):
        result = acg.transform_mcp_config({"mcp": {}})
        assert result == []


# ---------------------------------------------------------------------------
# transform_agent_for_yaml
# ---------------------------------------------------------------------------

class TestTransformAgentForYaml:
    def test_name_preserved_first(self):
        agent = {"name": "my_agent", "agent_class": "LLMAgent", "description": "d"}
        result = acg.transform_agent_for_yaml(agent)
        assert result["name"] == "my_agent"

    def test_model_id_dict_extracted(self):
        agent = {
            "name": "a",
            "model_id": {"value": "gemini-2.0-flash-001"},
            "description": "d",
            "agent_class": "LLMAgent",
        }
        result = acg.transform_agent_for_yaml(agent)
        assert result["model_id"] == "gemini-2.0-flash-001"

    def test_model_id_string_kept(self):
        agent = {"name": "a", "model_id": "gemini-1.5-pro", "description": "d"}
        result = acg.transform_agent_for_yaml(agent)
        assert result["model_id"] == "gemini-1.5-pro"

    def test_model_id_missing_defaults(self):
        agent = {"name": "a", "description": "d"}
        result = acg.transform_agent_for_yaml(agent)
        assert result["model_id"] == "gemini-2.0-flash-001"

    def test_excluded_fields_not_in_output(self):
        agent = {
            "name": "a",
            "show_advanced_options": True,
            "show_sub_agent_advanced": True,
            "description": "d",
        }
        result = acg.transform_agent_for_yaml(agent)
        assert "show_advanced_options" not in result
        assert "show_sub_agent_advanced" not in result

    def test_sub_agents_recursively_transformed(self):
        agent = {
            "name": "parent",
            "description": "parent desc",
            "sub_agents": [
                {
                    "name": "child",
                    "description": "child desc",
                    "model_id": {"value": "gemini-2.0-flash-001"},
                }
            ],
        }
        result = acg.transform_agent_for_yaml(agent)
        assert len(result["sub_agents"]) == 1
        assert result["sub_agents"][0]["name"] == "child"
        assert result["sub_agents"][0]["model_id"] == "gemini-2.0-flash-001"

    def test_rag_tool_included_when_enabled(self):
        agent = {
            "name": "a",
            "description": "d",
            "tools": {
                "enabled_tools": ["RAG"],
                "rag": {
                    "rag_details": {
                        "value": {
                            "datasetname": "ds",
                            "vectorizeddatasetbaseid": "c1",
                            "description": "",
                        }
                    }
                },
            },
        }
        result = acg.transform_agent_for_yaml(agent)
        assert "tools" in result
        assert "rag" in result["tools"]

    def test_rag_tool_excluded_when_not_enabled(self):
        agent = {
            "name": "a",
            "description": "d",
            "tools": {
                "enabled_tools": [],
                "rag": {"rag_details": {"value": {}}},
            },
        }
        result = acg.transform_agent_for_yaml(agent)
        assert result.get("tools", {}).get("rag") is None


# ---------------------------------------------------------------------------
# merge_agents_to_root_config
# ---------------------------------------------------------------------------

class TestMergeAgentsToRootConfig:
    def test_agents_appended_to_existing_list(self):
        root = {"root_agent": {}, "agents": [{"name": "existing"}]}
        new_agents = [{"name": "new_agent", "description": "d"}]
        result = acg.merge_agents_to_root_config(root, new_agents)
        assert len(result["agents"]) == 2
        assert result["agents"][-1]["name"] == "new_agent"

    def test_agents_created_when_missing(self):
        root = {"root_agent": {}}
        result = acg.merge_agents_to_root_config(root, [{"name": "a"}])
        assert "agents" in result
        assert len(result["agents"]) == 1

    def test_agents_none_replaced(self):
        root = {"root_agent": {}, "agents": None}
        result = acg.merge_agents_to_root_config(root, [{"name": "a"}])
        assert result["agents"] is not None
        assert len(result["agents"]) == 1

    def test_root_config_shallow_copy(self):
        root = {"root_agent": {}, "agents": []}
        result = acg.merge_agents_to_root_config(root, [{"name": "new"}])
        assert result["agents"] is root["agents"]
        assert len(result["agents"]) == 1

    def test_missing_root_agent_section_created(self):
        root = {}
        result = acg.merge_agents_to_root_config(root, [{"name": "a"}])
        assert "root_agent" in result


# ---------------------------------------------------------------------------
# save_agent_config_yaml
# ---------------------------------------------------------------------------

class TestSaveAgentConfigYaml:
    def test_writes_yaml_file(self, tmp_path):
        config = {"root_agent": {"model_id": "gemini"}, "agents": []}
        out_file = tmp_path / "output.yaml"
        result = acg.save_agent_config_yaml(config, str(out_file))
        assert result is True
        assert out_file.exists()

    def test_yaml_content_is_valid(self, tmp_path):
        config = {"key": "value", "num": 42}
        out_file = tmp_path / "output.yaml"
        acg.save_agent_config_yaml(config, str(out_file))
        loaded = yaml.safe_load(out_file.read_text())
        assert loaded["key"] == "value"
        assert loaded["num"] == 42

    def test_nested_structures_preserved(self, tmp_path):
        config = {
            "root_agent": {"model_id": "gemini", "sub": {"nested": True}},
            "agents": [{"name": "a1"}],
        }
        out_file = tmp_path / "output.yaml"
        acg.save_agent_config_yaml(config, str(out_file))
        loaded = yaml.safe_load(out_file.read_text())
        assert loaded["root_agent"]["sub"]["nested"] is True
        assert loaded["agents"][0]["name"] == "a1"

    def test_invalid_path_raises(self):
        config = {"key": "val"}
        with pytest.raises(Exception):
            acg.save_agent_config_yaml(config, "/nonexistent/dir/output.yaml")


# ---------------------------------------------------------------------------
# get_mcp_server_config
# ---------------------------------------------------------------------------

class TestGetMcpServerConfig:
    def test_known_registry_server_returns_config(self, monkeypatch):
        monkeypatch.setattr(
            acg,
            "MCP_SERVER_REGISTRY",
            {
                "test-mcp": {
                    "server_url": "http://test-mcp.dev",
                    "api_key_env": "TEST_MCP_KEY",
                    "base_path": "/mcp",
                    "health_path": "/mcp/health",
                }
            },
        )
        monkeypatch.setenv("TEST_MCP_KEY", "my-api-key")
        result = acg.get_mcp_server_config("test-mcp")
        assert result is not None
        assert result["name"] == "test-mcp"
        assert result["config"]["server_url"] == "http://test-mcp.dev"
        assert result["config"]["api_key"] == "my-api-key"
        assert result["config"]["base_path"] == "/mcp"
        assert result["config"]["health_path"] == "/mcp/health"

    def test_known_registry_server_no_api_key(self, monkeypatch):
        monkeypatch.setattr(
            acg,
            "MCP_SERVER_REGISTRY",
            {"no-key-mcp": {"server_url": "http://no-key.dev", "api_key_env": "MISSING_KEY"}},
        )
        monkeypatch.delenv("MISSING_KEY", raising=False)
        result = acg.get_mcp_server_config("no-key-mcp")
        assert result is not None
        assert "api_key" not in result["config"]

    def test_unknown_server_returns_none(self, monkeypatch):
        monkeypatch.setattr(acg, "MCP_SERVER_REGISTRY", {})
        monkeypatch.delenv("TOTALLY_UNKNOWN_MCP_URL", raising=False)
        monkeypatch.delenv("TOTALLY_UNKNOWN_URL", raising=False)
        result = acg.get_mcp_server_config("totally-unknown-mcp")
        assert result is None

    def test_env_var_fallback_for_unknown_server(self, monkeypatch):
        monkeypatch.setattr(acg, "MCP_SERVER_REGISTRY", {})
        monkeypatch.setenv("CUSTOM_SERVER_URL", "http://custom.dev")
        result = acg.get_mcp_server_config("custom-server")
        assert result is not None
        assert result["config"]["server_url"] == "http://custom.dev"

    def test_env_var_fallback_with_api_key(self, monkeypatch):
        monkeypatch.setattr(acg, "MCP_SERVER_REGISTRY", {})
        monkeypatch.setenv("CUSTOM_SERVER_URL", "http://custom.dev")
        monkeypatch.setenv("CUSTOM_SERVER_API_KEY", "env-key")
        result = acg.get_mcp_server_config("custom-server")
        assert result["config"].get("api_key") == "env-key"


# ---------------------------------------------------------------------------
# generate_agent_config (integration)
# ---------------------------------------------------------------------------

class TestGenerateAgentConfig:
    def test_generate_creates_output_file(self, tmp_path):
        agents = [
            {
                "name": "test_agent",
                "agent_class": "LLMAgent",
                "model_id": {"value": "gemini-2.0-flash-001"},
                "description": "Test agent",
                "instruction": "Do work",
            }
        ]
        agents_file = tmp_path / "agents.json"
        agents_file.write_text(json.dumps(agents))

        root_config = {
            "root_agent": {
                "agent_class": "LLMAgent",
                "model_id": "gemini-2.0-flash-001",
                "description": "Root desc",
                "instruction": "Root inst",
                "agent_display_name": "root",
            }
        }
        root_config_file = tmp_path / "root-agent-config.yaml"
        root_config_file.write_text(yaml.dump(root_config))

        output_file = tmp_path / "agent-config.yaml"
        result = acg.generate_agent_config(
            str(agents_file), str(root_config_file), str(output_file)
        )
        assert result is True
        assert output_file.exists()

    def test_generate_output_contains_merged_agents(self, tmp_path):
        agents = [{"name": "agent1", "description": "A1", "instruction": "do1"}]
        agents_file = tmp_path / "agents.json"
        agents_file.write_text(json.dumps(agents))

        root_config = {
            "root_agent": {
                "agent_class": "LLMAgent",
                "model_id": "gemini-2.0-flash-001",
                "description": "Root",
                "instruction": "Root inst",
            }
        }
        root_config_file = tmp_path / "root-agent-config.yaml"
        root_config_file.write_text(yaml.dump(root_config))

        output_file = tmp_path / "agent-config.yaml"
        acg.generate_agent_config(
            str(agents_file), str(root_config_file), str(output_file)
        )
        loaded = yaml.safe_load(output_file.read_text())
        agent_names = [a["name"] for a in loaded.get("agents", [])]
        assert "agent1" in agent_names

    def test_generate_returns_false_for_empty_agents(self, tmp_path):
        agents_file = tmp_path / "agents.json"
        agents_file.write_text("[]")

        root_config = {"root_agent": {}}
        root_config_file = tmp_path / "root-agent-config.yaml"
        root_config_file.write_text(yaml.dump(root_config))

        output_file = tmp_path / "agent-config.yaml"
        result = acg.generate_agent_config(
            str(agents_file), str(root_config_file), str(output_file)
        )
        assert result is False
