"""Unit tests for config_reader module."""

import sys
import os
import json
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import pytest

# Setup path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


class TestConfigReader:
    """Test suite for ConfigReader class."""

    def test_init_with_json_file(self, tmp_path):
        """Test initialization with a JSON file."""
        from config.config_reader import ConfigReader  # type: ignore
        
        # Create a test JSON file
        test_data = {"key": "value", "number": 123}
        json_file = tmp_path / "test_config.json"
        with open(json_file, "w") as f:
            json.dump(test_data, f)
        
        reader = ConfigReader(str(json_file))
        
        assert ConfigReader._data == test_data

    def test_init_with_yaml_file(self, tmp_path):
        """Test initialization with a YAML file."""
        from config.config_reader import ConfigReader  # type: ignore
        
        # Create a test YAML file
        test_data = {"key": "value", "list": [1, 2, 3]}
        yaml_file = tmp_path / "test_config.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(test_data, f)
        
        reader = ConfigReader(str(yaml_file))
        
        assert ConfigReader._data == test_data

    def test_init_with_yml_extension(self, tmp_path):
        """Test initialization with .yml extension."""
        from config.config_reader import ConfigReader  # type: ignore
        
        test_data = {"test": "yml_file"}
        yml_file = tmp_path / "test_config.yml"
        with open(yml_file, "w") as f:
            yaml.dump(test_data, f)
        
        reader = ConfigReader(str(yml_file))
        
        assert ConfigReader._data == test_data

    def test_init_file_not_found(self):
        """Test that FileNotFoundError is raised for missing file."""
        from config.config_reader import ConfigReader  # type: ignore
        
        with pytest.raises(FileNotFoundError):
            ConfigReader("/nonexistent/path/config.json")

    def test_init_invalid_json(self, tmp_path):
        """Test that invalid JSON raises JSONDecodeError."""
        from config.config_reader import ConfigReader  # type: ignore
        
        invalid_json_file = tmp_path / "invalid.json"
        with open(invalid_json_file, "w") as f:
            f.write("{invalid json content")
        
        with pytest.raises(json.JSONDecodeError):
            ConfigReader(str(invalid_json_file))

    def test_init_invalid_yaml(self, tmp_path):
        """Test that invalid YAML raises YAMLError."""
        from config.config_reader import ConfigReader  # type: ignore
        
        invalid_yaml_file = tmp_path / "invalid.yaml"
        with open(invalid_yaml_file, "w") as f:
            f.write("invalid: yaml: content: [")
        
        with pytest.raises(yaml.YAMLError):
            ConfigReader(str(invalid_yaml_file))

    def test_get_value_existing_key(self, tmp_path):
        """Test get_value returns correct value for existing key."""
        from config.config_reader import ConfigReader  # type: ignore
        
        test_data = {"existing_key": "test_value"}
        json_file = tmp_path / "config.json"
        with open(json_file, "w") as f:
            json.dump(test_data, f)
        
        ConfigReader(str(json_file))
        value = ConfigReader.get_value("existing_key")
        
        assert value == "test_value"

    def test_get_value_missing_key_with_default(self, tmp_path):
        """Test get_value returns default value for missing key."""
        from config.config_reader import ConfigReader  # type: ignore
        
        test_data = {"key": "value"}
        json_file = tmp_path / "config.json"
        with open(json_file, "w") as f:
            json.dump(test_data, f)
        
        ConfigReader(str(json_file))
        value = ConfigReader.get_value("missing_key", "default_value")
        
        assert value == "default_value"

    def test_get_value_missing_key_no_default(self, tmp_path):
        """Test get_value returns None for missing key without default."""
        from config.config_reader import ConfigReader  # type: ignore
        
        test_data = {"key": "value"}
        json_file = tmp_path / "config.json"
        with open(json_file, "w") as f:
            json.dump(test_data, f)
        
        ConfigReader(str(json_file))
        value = ConfigReader.get_value("missing_key")
        
        assert value is None

    def test_get_value_before_initialization(self):
        """Test that get_value raises error if config not loaded."""
        from config.config_reader import ConfigReader  # type: ignore
        
        ConfigReader._data = None
        
        with pytest.raises(RuntimeError, match="Configuration not loaded"):
            ConfigReader.get_value("any_key")

    def test_get_value_nested_structure(self, tmp_path):
        """Test get_value with nested data structure."""
        from config.config_reader import ConfigReader  # type: ignore
        
        test_data = {
            "level1": {
                "level2": {
                    "level3": "deep_value"
                }
            }
        }
        json_file = tmp_path / "config.json"
        with open(json_file, "w") as f:
            json.dump(test_data, f)
        
        ConfigReader(str(json_file))
        value = ConfigReader.get_value("level1")
        
        assert value["level2"]["level3"] == "deep_value"

    def test_class_variable_persistence(self, tmp_path):
        """Test that ConfigReader._data persists across instances."""
        from config.config_reader import ConfigReader  # type: ignore
        
        test_data = {"persistent": "data"}
        json_file = tmp_path / "config.json"
        with open(json_file, "w") as f:
            json.dump(test_data, f)
        
        reader1 = ConfigReader(str(json_file))
        value = ConfigReader.get_value("persistent")
        
        assert value == "data"

    def test_yaml_list_structure(self, tmp_path):
        """Test loading YAML with list structures."""
        from config.config_reader import ConfigReader  # type: ignore
        
        test_data = {
            "items": ["item1", "item2", "item3"],
            "nested": {
                "list": [1, 2, 3]
            }
        }
        yaml_file = tmp_path / "config.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(test_data, f)
        
        ConfigReader(str(yaml_file))
        items = ConfigReader.get_value("items")
        
        assert items == ["item1", "item2", "item3"]
        assert ConfigReader.get_value("nested")["list"] == [1, 2, 3]

    def test_empty_config_file(self, tmp_path):
        """Test loading an empty config file."""
        from config.config_reader import ConfigReader  # type: ignore
        
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")
        
        reader = ConfigReader(str(empty_file))
        
        # Empty YAML file should result in None
        assert ConfigReader._data is None

    def test_get_value_with_empty_string(self, tmp_path):
        """Test get_value when value is empty string."""
        from config.config_reader import ConfigReader  # type: ignore
        
        test_data = {"empty": ""}
        json_file = tmp_path / "config.json"
        with open(json_file, "w") as f:
            json.dump(test_data, f)
        
        ConfigReader(str(json_file))
        # Empty string should return default
        value = ConfigReader.get_value("empty", "default")
        
        assert value == "default"
