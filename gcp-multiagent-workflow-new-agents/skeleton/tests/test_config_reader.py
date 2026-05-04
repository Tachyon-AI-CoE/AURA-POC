"""Tests for config/config_reader.py — ConfigReader."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import pytest
import yaml
import json
import tempfile
from config.config_reader import ConfigReader


# ---------------------------------------------------------------------------
# Original tests
# ---------------------------------------------------------------------------

def test_config_reader_yaml(tmp_path):
    yaml_content = """
    foo: bar
    num: 42
    nested:
      key: value
    """
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(yaml_content)

    reader = ConfigReader(str(yaml_file))
    assert reader.get_value("foo") == "bar"
    assert reader.get_value("num") == 42
    assert reader.get_value("nested") == {"key": "value"}
    assert reader.get_value("missing", "default") == "default"


def test_config_reader_json(tmp_path):
    json_content = '{"foo": "bar", "num": 42, "nested": {"key": "value"}}'
    json_file = tmp_path / "test.json"
    json_file.write_text(json_content)

    reader = ConfigReader(str(json_file))
    assert reader.get_value("foo") == "bar"
    assert reader.get_value("num") == 42
    assert reader.get_value("nested") == {"key": "value"}
    assert reader.get_value("missing", "default") == "default"


def test_config_reader_invalid_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        ConfigReader(str(tmp_path / "nope.yaml"))


def test_config_reader_invalid_format(tmp_path):
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("not: [valid: yaml: [}")
    with pytest.raises(Exception):
        ConfigReader(str(bad_file))


def test_config_reader_classmethod(monkeypatch, tmp_path):
    yaml_content = "foo: bar"
    yaml_file = tmp_path / "test2.yaml"
    yaml_file.write_text(yaml_content)
    ConfigReader(str(yaml_file))
    assert ConfigReader.get_value("foo") == "bar"
    assert ConfigReader.get_value("missing", 123) == 123


# ---------------------------------------------------------------------------
# Extended tests (from test_config_reader_class.py)
# ---------------------------------------------------------------------------

def test_get_value_returns_value():
    data = {"foo": "bar", "num": 1}
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.dump(data, f)
        fpath = f.name
    reader = ConfigReader(fpath)
    assert reader.get_value("foo") == "bar"
    assert reader.get_value("num") == 1
    os.remove(fpath)

def test_get_value_returns_default():
    data = {"foo": "bar"}
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.dump(data, f)
        fpath = f.name
    reader = ConfigReader(fpath)
    assert reader.get_value("missing", 123) == 123
    os.remove(fpath)

def test_init_invalid_file():
    with pytest.raises(FileNotFoundError):
        ConfigReader("not_a_file.yaml")

def test_init_invalid_yaml(tmp_path):
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("not: [valid: yaml: [}")
    with pytest.raises(Exception):
        ConfigReader(str(bad_file))


# ---------------------------------------------------------------------------
# Root agent config test
# ---------------------------------------------------------------------------

def test_config_reader_root_agent(monkeypatch, tmp_path):
    yaml_content = """
    root_agent:
      project_id: test-proj
      region: us-central1
      agent_display_name: root
      agent_class: class
      multiagent: true
      model_id: model
      description: desc
      guardrail_enabled: true
    """
    config_file = tmp_path / "root-agent-config.yaml"
    config_file.write_text(yaml_content)
    reader = ConfigReader(str(config_file))
    root_agent = reader.get_value("root_agent")
    assert root_agent["project_id"] == "test-proj"
    assert root_agent["region"] == "us-central1"
    assert root_agent["guardrail_enabled"] is True or root_agent["guardrail_enabled"] == "true"
