"""Unit tests for agent_config_generator module."""

import sys
import json
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import pytest

# Setup path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


class TestAgentConfigGenerator:
    """Test suite for agent configuration generator functions."""

    def test_load_agents_from_json_success(self, tmp_path):
        """Test successful loading of agents from JSON file."""
        from config.agent_config_generator import load_agents_from_json  # type: ignore
        
        test_agents = [
            {"agent_name": "agent1", "model_id": "gemini-1.5-pro"},
            {"agent_name": "agent2", "model_id": "gemini-1.0-pro"}
        ]
        
        json_file = tmp_path / "agents.json"
        with open(json_file, "w") as f:
            json.dump(test_agents, f)
        
        result = load_agents_from_json(str(json_file))
        
        assert len(result) == 2
        assert result[0]["agent_name"] == "agent1"
        assert result[1]["agent_name"] == "agent2"

    def test_load_agents_from_json_file_not_found(self):
        """Test loading agents from non-existent file."""
        from config.agent_config_generator import load_agents_from_json  # type: ignore
        
        result = load_agents_from_json("/nonexistent/agents.json")
        
        assert result == []

    def test_load_agents_from_json_invalid_json(self, tmp_path):
        """Test loading agents from invalid JSON file."""
        from config.agent_config_generator import load_agents_from_json  # type: ignore
        
        invalid_json_file = tmp_path / "invalid.json"
        with open(invalid_json_file, "w") as f:
            f.write("{invalid json")
        
        result = load_agents_from_json(str(invalid_json_file))
        
        assert result == []

    def test_load_root_agent_config_success(self, tmp_path):
        """Test successful loading of root agent config."""
        from config.agent_config_generator import load_root_agent_config  # type: ignore
        
        test_config = {
            "root_agent": {
                "project_id": "test-project",
                "region": "us-central1"
            }
        }
        
        yaml_file = tmp_path / "config.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(test_config, f)
        
        result = load_root_agent_config(str(yaml_file))
        
        assert result["root_agent"]["project_id"] == "test-project"
        assert result["root_agent"]["region"] == "us-central1"

    def test_load_root_agent_config_file_not_found(self):
        """Test loading root agent config from non-existent file."""
        from config.agent_config_generator import load_root_agent_config  # type: ignore
        
        result = load_root_agent_config("/nonexistent/config.yaml")
        
        assert result == {}

    def test_load_root_agent_config_invalid_yaml(self, tmp_path):
        """Test loading root agent config from invalid YAML file."""
        from config.agent_config_generator import load_root_agent_config  # type: ignore
        
        invalid_yaml_file = tmp_path / "invalid.yaml"
        with open(invalid_yaml_file, "w") as f:
            f.write("invalid: yaml: content: [")
        
        result = load_root_agent_config(str(invalid_yaml_file))
        
        assert result == {}

    def test_transform_rag_config_with_valid_rag(self):
        """Test transforming RAG configuration with valid data."""
        from config.agent_config_generator import transform_rag_config  # type: ignore
        
        tools = {
            "rag": [
                {
                    "resource_id": "projects/test/locations/us-central1/ragCorpora/corpus1",
                    "rag_details": {
                        "value": {
                            "datasetname": "test-dataset",
                            "vectorizeddatasetbaseid": "corpus1",
                            "description": "Test RAG dataset"
                        }
                    },
                    "vector_distance_threshold": 0.5,
                    "similarity_top_k": 10
                }
            ]
        }
        
        result = transform_rag_config(tools)
        
        assert len(result) == 1
        assert result[0]["name"] == "test-dataset"
        assert result[0]["description"] == "Test RAG dataset"
        assert "rag_resources" in result[0]["config"]
        assert len(result[0]["config"]["rag_resources"]) == 1
        assert result[0]["config"]["vector_distance_threshold"] == 0.5
        assert result[0]["config"]["similarity_top_k"] == 10

    def test_transform_rag_config_no_rag(self):
        """Test transforming RAG configuration when no RAG tools exist."""
        from config.agent_config_generator import transform_rag_config  # type: ignore
        
        tools = {"other_tool": "value"}
        
        result = transform_rag_config(tools)
        
        assert result == []

    def test_transform_rag_config_empty_rag(self):
        """Test transforming empty RAG configuration."""
        from config.agent_config_generator import transform_rag_config  # type: ignore
        
        tools = {"rag": []}
        
        result = transform_rag_config(tools)
        
        assert result == []

    def test_transform_rag_config_missing_resource_id(self):
        """Test transforming RAG config with missing resource_id."""
        from config.agent_config_generator import transform_rag_config  # type: ignore
        
        tools = {
            "rag": [
                {
                    "rag_details": {
                        "value": {
                            "datasetname": "test-dataset",
                            "vectorizeddatasetbaseid": "corpus-backup-id",
                            "description": "Test dataset"
                        }
                    }
                }
            ]
        }
        
        result = transform_rag_config(tools)
        
        assert len(result) == 1
        assert result[0]["name"] == "test-dataset"
        # Should use vectorizeddatasetbaseid as fallback
        assert "rag_resources" in result[0]["config"]
        assert len(result[0]["config"]["rag_resources"]) == 1

    def test_transform_rag_config_single_dict(self):
        """Test transforming RAG configuration when rag is a dict instead of list."""
        from config.agent_config_generator import transform_rag_config  # type: ignore
        
        tools = {
            "rag": {
                "resource_id": "corpus1",
                "rag_details": {
                    "value": {
                        "datasetname": "single-dataset",
                        "description": "Single RAG"
                    }
                }
            }
        }
        
        result = transform_rag_config(tools)
        
        assert len(result) == 1
        assert result[0]["name"] == "single-dataset"

    def test_transform_mcp_config_with_list(self):
        """Test transforming MCP configuration when it's already a list."""
        from config.agent_config_generator import transform_mcp_config  # type: ignore
        
        tools = {
            "mcp": [
                {
                    "name": "server1",
                    "config": {"endpoint": "http://localhost:8000"}
                },
                {
                    "name": "server2",
                    "config": {"endpoint": "http://localhost:8001"}
                }
            ]
        }
        
        result = transform_mcp_config(tools)
        
        assert len(result) == 2
        assert result[0]["name"] == "server1"
        assert result[1]["name"] == "server2"

    def test_transform_mcp_config_no_mcp(self):
        """Test transforming MCP configuration when no MCP tools exist."""
        from config.agent_config_generator import transform_mcp_config  # type: ignore
        
        tools = {"rag": []}
        
        result = transform_mcp_config(tools)
        
        assert result == []

    @patch('config.agent_config_generator.get_mcp_server_config')
    def test_transform_mcp_config_with_server_names(self, mock_get_config):
        """Test transforming MCP configuration with server names."""
        from config.agent_config_generator import transform_mcp_config  # type: ignore
        
        mock_get_config.side_effect = [
            {"name": "server1", "config": {"endpoint": "http://localhost:8000"}},
            {"name": "server2", "config": {"endpoint": "http://localhost:8001"}}
        ]
        
        tools = {
            "mcp": {
                "mcp_servers": ["server1", "server2"]
            }
        }
        
        result = transform_mcp_config(tools)
        
        assert len(result) == 2
        assert mock_get_config.call_count == 2

    def test_transform_agent_for_yaml(self):
        """Test transforming agent configuration for YAML output."""
        from config.agent_config_generator import transform_agent_for_yaml  # type: ignore
        
        agent = {
            "name": "test-agent",
            "agent_class": "LlmAgent",
            "model_id": "gemini-1.5-pro",
            "description": "Test agent"
        }
        
        result = transform_agent_for_yaml(agent)
        
        # The function returns a transformed dict with 'name'
        assert result["name"] == "test-agent"
        assert result["agent_class"] == "LlmAgent"
        assert result["model_id"] == "gemini-1.5-pro"

    def test_merge_agents_to_root_config(self, sample_agents_json, sample_root_agent_config):
        """Test merging agents into root configuration."""
        from config.agent_config_generator import merge_agents_to_root_config  # type: ignore
        
        # merge_agents_to_root_config expects (root_config, agents) - root_config is a dict, agents is a list
        result = merge_agents_to_root_config(sample_root_agent_config, sample_agents_json)
        
        assert "root_agent" in result
        assert "agents" in result
        assert len(result["agents"]) == len(sample_agents_json)

    def test_save_agent_config_yaml(self, tmp_path):
        """Test saving agent configuration to YAML file."""
        from config.agent_config_generator import save_agent_config_yaml  # type: ignore
        
        config = {
            "root_agent": {
                "project_id": "test-project",
                "agent_name": "test-agent"
            }
        }
        
        output_file = tmp_path / "output.yaml"
        result = save_agent_config_yaml(config, str(output_file))
        
        assert result is True
        assert output_file.exists()
        
        # Verify content
        with open(output_file, "r") as f:
            loaded = yaml.safe_load(f)
        
        assert loaded["root_agent"]["project_id"] == "test-project"

    def test_generate_agent_config(self, tmp_path, sample_agents_json, sample_root_agent_config):
        """Test complete agent configuration generation."""
        from config.agent_config_generator import generate_agent_config  # type: ignore
        
        agents_file = tmp_path / "agents.json"
        config_file = tmp_path / "config.yaml"
        output_file = tmp_path / "output.yaml"
        
        with open(agents_file, "w") as f:
            json.dump(sample_agents_json, f)
        
        with open(config_file, "w") as f:
            yaml.dump(sample_root_agent_config, f)
        
        # generate_agent_config expects three file paths as strings
        result = generate_agent_config(
            str(agents_file),
            str(config_file),
            str(output_file)
        )
        
        assert result is True
        assert output_file.exists()

    def test_get_mcp_server_config(self):
        """Test retrieving MCP server configuration."""
        from config.agent_config_generator import get_mcp_server_config  # type: ignore
        
        # This function returns a default config, no need to mock requests
        result = get_mcp_server_config("test-server")
        
        assert result is not None
        assert result["name"] == "test-server"
        assert "config" in result
        assert "description" in result
