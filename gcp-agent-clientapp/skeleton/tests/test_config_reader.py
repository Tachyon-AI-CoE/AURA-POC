"""
Unit tests for config_reader module
"""
import json
import yaml
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
import pytest

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from config.config_reader import ConfigReader  # type: ignore[import-not-found]


class TestConfigReader:
    """Test suite for ConfigReader class"""
    
    def test_load_json_configuration(self, mock_config_file):
        """Test loading JSON configuration file"""
        config = ConfigReader(mock_config_file)
        
        assert ConfigReader._data is not None
        assert ConfigReader.get_value("PROJECT_ID") == "test-project"
        assert ConfigReader.get_value("REGION") == "us-central1"
        assert ConfigReader.get_value("AGENT_ID") == "agent-123"
    
    def test_load_yaml_configuration(self, mock_yaml_config_file):
        """Test loading YAML configuration file"""
        config = ConfigReader(mock_yaml_config_file)
        
        assert ConfigReader._data is not None
        assert ConfigReader.get_value("PROJECT_ID") == "test-project-yaml"
        assert ConfigReader.get_value("REGION") == "europe-west1"
        assert ConfigReader.get_value("AGENT_ID") == "agent-yaml-123"
    
    def test_get_value_existing_key(self, mock_config_file):
        """Test getting value for existing key"""
        config = ConfigReader(mock_config_file)
        
        value = ConfigReader.get_value("PROJECT_ID")
        assert value == "test-project"
        
        name = ConfigReader.get_value("NAME")
        assert name == "Test Agent"
    
    def test_get_value_missing_key_returns_none(self, mock_config_file):
        """Test getting value for non-existent key returns None"""
        config = ConfigReader(mock_config_file)
        
        value = ConfigReader.get_value("NON_EXISTENT_KEY")
        assert value is None
    
    def test_get_value_with_default(self, mock_config_file):
        """Test getting value with default for missing key"""
        config = ConfigReader(mock_config_file)
        
        value = ConfigReader.get_value("MISSING_KEY", default_value="default_val")
        assert value == "default_val"
    
    def test_get_value_without_initialization_raises_error(self):
        """Test getting value before initialization raises RuntimeError"""
        # Reset class variable
        ConfigReader._data = None
        
        with pytest.raises(RuntimeError, match="Configuration not loaded"):
            ConfigReader.get_value("ANY_KEY")
    
    def test_load_nonexistent_file_raises_error(self):
        """Test loading non-existent file raises FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            ConfigReader("/nonexistent/path/config.json")
    
    def test_load_invalid_json_raises_error(self, tmp_path):
        """Test loading invalid JSON raises error"""
        config_file = tmp_path / "invalid.json"
        config_file.write_text("{ invalid json content }")
        
        with pytest.raises(json.JSONDecodeError):
            ConfigReader(str(config_file))
    
    def test_load_invalid_yaml_raises_error(self, tmp_path):
        """Test loading invalid YAML raises error"""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [[[")
        
        with pytest.raises(yaml.YAMLError):
            ConfigReader(str(config_file))
    
    def test_class_variable_shared_across_instances(self, mock_config_file):
        """Test that _data is shared across all instances"""
        config1 = ConfigReader(mock_config_file)
        
        # Create another instance - it should share the same _data
        value1 = ConfigReader.get_value("PROJECT_ID")
        value2 = ConfigReader.get_value("PROJECT_ID")
        
        assert value1 == value2
        assert value1 == "test-project"
    
    def test_json_file_extension_detected(self, mock_config_file):
        """Test that JSON files are properly detected by extension"""
        config = ConfigReader(mock_config_file)
        
        assert ConfigReader._data is not None
        assert isinstance(ConfigReader._data, dict)
    
    def test_yaml_file_extension_detected(self, mock_yaml_config_file):
        """Test that YAML files are properly detected by extension"""
        config = ConfigReader(mock_yaml_config_file)
        
        assert ConfigReader._data is not None
        assert isinstance(ConfigReader._data, dict)
    
    def test_get_value_returns_all_data_types(self, tmp_path):
        """Test get_value returns different data types correctly"""
        config_file = tmp_path / "types.json"
        config_data = {
            "string_key": "string_value",
            "int_key": 123,
            "float_key": 45.67,
            "bool_key": True,
            "list_key": [1, 2, 3],
            "dict_key": {"nested": "value"}
        }
        config_file.write_text(json.dumps(config_data))
        
        config = ConfigReader(str(config_file))
        
        assert ConfigReader.get_value("string_key") == "string_value"
        assert ConfigReader.get_value("int_key") == 123
        assert ConfigReader.get_value("float_key") == 45.67
        assert ConfigReader.get_value("bool_key") is True
        assert ConfigReader.get_value("list_key") == [1, 2, 3]
        assert ConfigReader.get_value("dict_key") == {"nested": "value"}
    
    def test_empty_json_file(self, tmp_path):
        """Test loading empty JSON file"""
        config_file = tmp_path / "empty.json"
        config_file.write_text("{}")
        
        config = ConfigReader(str(config_file))
        
        assert ConfigReader._data == {}
        assert ConfigReader.get_value("ANY_KEY") is None
    
    def test_get_value_with_empty_string(self, tmp_path):
        """Test get_value when value is empty string"""
        config_file = tmp_path / "empty_value.json"
        config_data = {"empty_key": ""}
        config_file.write_text(json.dumps(config_data))
        
        config = ConfigReader(str(config_file))
        
        # Empty string is falsy, so should return default
        value = ConfigReader.get_value("empty_key", "default")
        assert value == "default"
    
    def test_get_value_with_zero(self, tmp_path):
        """Test get_value when value is 0 (falsy but valid)"""
        config_file = tmp_path / "zero.json"
        config_data = {"zero_key": 0}
        config_file.write_text(json.dumps(config_data))
        
        config = ConfigReader(str(config_file))
        
        # 0 is falsy, so should return default
        value = ConfigReader.get_value("zero_key", "default")
        assert value == "default"
