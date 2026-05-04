"""Tests for config/config.py — module-level logic."""

import sys
import os
import importlib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))  # noqa: E402

from unittest.mock import patch, MagicMock  # noqa: E402


class TestConfigModule:
    """Test config.py module-level logic by reloading with mocked ConfigReader."""

    def _import_config_module(self, mock_root_agent_config):
        """Helper: reload config.config with a mocked ConfigReader."""
        mock_reader_instance = MagicMock()
        mock_reader_instance.get_value.side_effect = lambda key, default=None: mock_root_agent_config.get(key, default)

        MockConfigReaderCls = MagicMock(return_value=mock_reader_instance)
        MockConfigReaderCls.get_value = mock_reader_instance.get_value

        with patch("config.config_reader.ConfigReader", MockConfigReaderCls):
            with patch("config.config.load_dotenv"):
                # Ensure the module is loaded so we can always reload it.
                if "config.config" not in sys.modules:
                    import config.config  # noqa: F811
                mod = importlib.reload(sys.modules["config.config"])
                return mod

    def test_guardrail_disabled(self):
        root_agent_cfg = {
            "root_agent": {
                "project_id": "test-proj",
                "region": "us-central1",
                "agent_display_name": "TestAgent",
                "guardrail_enabled": False,
                "enable_groundtruth": False,
                "enable_general_groundtruth": False,
            }
        }
        mod = self._import_config_module(root_agent_cfg)
        assert mod.guardrail_enabled is False
        assert mod.guardrail_name is None
        assert mod.guardrail_url is None

    def test_guardrail_enabled_string(self):
        root_agent_cfg = {
            "root_agent": {
                "project_id": "p",
                "region": "r",
                "guardrail_enabled": "true",
                "guardrail_name": "gname",
                "guardrail_url": "https://storage.cloud.google.com/mybucket/folder1/folder2/guardrail.json",
                "enable_groundtruth": False,
                "enable_general_groundtruth": False,
            }
        }
        mod = self._import_config_module(root_agent_cfg)
        assert mod.guardrail_enabled is True
        assert mod.guardrail_name == "gname"
        assert mod.bucket_name == "mybucket"
        assert mod.GUARDRAIL_BUCKET_PREFIX == "folder1/folder2"
        assert mod.guardrail_file_name == "guardrail.json"

    def test_groundtruth_enabled(self):
        root_agent_cfg = {
            "root_agent": {
                "project_id": "p",
                "region": "r",
                "guardrail_enabled": False,
                "enable_groundtruth": "true",
                "groundtruth_name": "gt_name",
                "enable_general_groundtruth": "true",
                "general_groundtruth_name": "ggt_name",
            }
        }
        mod = self._import_config_module(root_agent_cfg)
        assert mod.enable_groundtruth is True
        assert mod.groundtruth_name == "gt_name"
        assert mod.enable_general_groundtruth is True
        assert mod.general_groundtruth_name == "ggt_name"

    def test_groundtruth_disabled(self):
        root_agent_cfg = {
            "root_agent": {
                "project_id": "p",
                "region": "r",
                "guardrail_enabled": False,
                "enable_groundtruth": False,
                "enable_general_groundtruth": False,
            }
        }
        mod = self._import_config_module(root_agent_cfg)
        assert mod.enable_groundtruth is False
        assert mod.groundtruth_name is None
        assert mod.general_groundtruth_name is None

    def test_env_variables(self):
        root_agent_cfg = {
            "root_agent": {
                "guardrail_enabled": False,
                "enable_groundtruth": False,
                "enable_general_groundtruth": False,
            }
        }
        with patch.dict(os.environ, {
            "ENVIRONMENT": "prod",
            "LOG_LEVEL": "DEBUG",
            "STAGING_BUCKET_NAME": "my-bucket",
        }):
            mod = self._import_config_module(root_agent_cfg)
            assert mod.ENVIRONMENT == "prod"
            assert mod.LOG_LEVEL == "DEBUG"
            assert mod.STAGING_BUCKET == "gs://my-bucket"
