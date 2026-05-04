"""Tests for root_agent/content_filter/safety_settings.py — all functions."""

import sys
import os
import json
import types
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
class DummyRagResource:
    def __init__(self, *args, **kwargs):
        self.rag_corpus = kwargs.get('rag_corpus', 'dummy_corpus')
sys.modules['vertexai.rag'] = types.SimpleNamespace(RagResource=DummyRagResource)

import pytest
from unittest.mock import patch, MagicMock
from root_agent.content_filter.safety_settings import (
    read_guardrail_from_gcs,
    construct_safety_settings,
    get_safety_settings_from_gcs,
    get_safety_settings_from_file,
    save_guardrail_to_file,
    safety_settings_download_callback,
    safety_settings_model_callback,
)


# ---------------------------------------------------------------------------
# Original tests
# ---------------------------------------------------------------------------

def test_read_guardrail_from_gcs_not_found(monkeypatch):
    class DummyBlob:
        def exists(self):
            return False
    class DummyBucket:
        def blob(self, file_name):
            return DummyBlob()
    class DummyClient:
        def bucket(self, bucket_name):
            return DummyBucket()
    monkeypatch.setattr("google.cloud.storage.Client", lambda: DummyClient())
    result = read_guardrail_from_gcs("bucket", "file.json")
    assert result is None

def test_read_guardrail_from_gcs_success(monkeypatch):
    class DummyBlob:
        def exists(self):
            return True
        def download_as_text(self):
            return '{"foo": "bar"}'
    class DummyBucket:
        def blob(self, file_name):
            return DummyBlob()
    class DummyClient:
        def bucket(self, bucket_name):
            return DummyBucket()
    monkeypatch.setattr("google.cloud.storage.Client", lambda: DummyClient())
    result = read_guardrail_from_gcs("bucket", "file.json")
    assert result == {"foo": "bar"}


# ---------------------------------------------------------------------------
# construct_safety_settings
# ---------------------------------------------------------------------------

class TestConstructSafetySettings:
    def test_valid_config(self):
        config = {
            "content_filters": {
                "configurable_filters": {
                    "safety_settings": [
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_LOW_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    ]
                }
            }
        }
        result = construct_safety_settings(config)
        assert len(result) == 2

    def test_empty_safety_settings_list(self):
        config = {"content_filters": {"configurable_filters": {"safety_settings": []}}}
        result = construct_safety_settings(config)
        assert result == []

    def test_missing_category_skipped(self):
        config = {
            "content_filters": {
                "configurable_filters": {
                    "safety_settings": [{"threshold": "BLOCK_LOW_AND_ABOVE"}]
                }
            }
        }
        result = construct_safety_settings(config)
        assert len(result) == 0

    def test_missing_threshold_skipped(self):
        config = {
            "content_filters": {
                "configurable_filters": {
                    "safety_settings": [{"category": "HARM_CATEGORY_HATE_SPEECH"}]
                }
            }
        }
        result = construct_safety_settings(config)
        assert len(result) == 0

    def test_empty_config(self):
        result = construct_safety_settings({})
        assert result == []

    def test_exception_returns_empty(self):
        result = construct_safety_settings(None)
        assert result == []


# ---------------------------------------------------------------------------
# get_safety_settings_from_gcs
# ---------------------------------------------------------------------------

class TestGetSafetySettingsFromGcs:
    @patch.dict(os.environ, {}, clear=True)
    def test_no_bucket_returns_empty(self):
        result = get_safety_settings_from_gcs(bucket_name=None)
        assert result == []

    @patch.dict(os.environ, {"GUARDRAILS_ENABLED": "false"})
    def test_guardrails_disabled_returns_empty(self):
        result = get_safety_settings_from_gcs(bucket_name="mybucket")
        assert result == []

    @patch.dict(os.environ, {"GUARDRAILS_ENABLED": "true"})
    @patch("root_agent.content_filter.safety_settings.read_guardrail_from_gcs", return_value=None)
    def test_gcs_read_failure_returns_empty(self, mock_read):
        result = get_safety_settings_from_gcs(bucket_name="mybucket")
        assert result == []

    @patch.dict(os.environ, {"GUARDRAILS_ENABLED": "true"})
    @patch("root_agent.content_filter.safety_settings.read_guardrail_from_gcs")
    def test_success_returns_settings(self, mock_read):
        mock_read.return_value = {
            "content_filters": {
                "configurable_filters": {
                    "safety_settings": [
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_LOW_AND_ABOVE"}
                    ]
                }
            }
        }
        result = get_safety_settings_from_gcs(bucket_name="mybucket")
        assert len(result) == 1

    @patch.dict(os.environ, {"GUARDRAIL_BUCKET": "env-bucket", "GUARDRAILS_ENABLED": "true"})
    @patch("root_agent.content_filter.safety_settings.read_guardrail_from_gcs")
    def test_bucket_from_env(self, mock_read):
        mock_read.return_value = {"content_filters": {"configurable_filters": {"safety_settings": []}}}
        get_safety_settings_from_gcs()
        mock_read.assert_called_once_with("env-bucket", "guardrail.json")


# ---------------------------------------------------------------------------
# get_safety_settings_from_file
# ---------------------------------------------------------------------------

class TestGetSafetySettingsFromFile:
    def test_valid_file(self, tmp_path):
        config = {
            "content_filters": {
                "configurable_filters": {
                    "safety_settings": [
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_LOW_AND_ABOVE"}
                    ]
                }
            }
        }
        f = tmp_path / "guardrail.json"
        f.write_text(json.dumps(config))
        result = get_safety_settings_from_file(str(f))
        assert len(result) == 1

    def test_file_not_found(self):
        result = get_safety_settings_from_file("/nonexistent/path.json")
        assert result == []

    def test_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not json{{{")
        result = get_safety_settings_from_file(str(f))
        assert result == []


# ---------------------------------------------------------------------------
# save_guardrail_to_file
# ---------------------------------------------------------------------------

class TestSaveGuardrailToFile:
    def test_save_success(self, tmp_path):
        f = tmp_path / "out.json"
        config = {"key": "value"}
        result = save_guardrail_to_file(config, str(f))
        assert result is True
        assert json.loads(f.read_text()) == config

    def test_save_with_indent(self, tmp_path):
        f = tmp_path / "out.json"
        save_guardrail_to_file({"k": "v"}, str(f), indent=4)
        content = f.read_text()
        assert "    " in content

    def test_save_failure(self):
        result = save_guardrail_to_file({"k": "v"}, "/nonexistent/dir/file.json")
        assert result is False


# ---------------------------------------------------------------------------
# safety_settings_download_callback
# ---------------------------------------------------------------------------

class TestSafetySettingsDownloadCallback:
    @patch.dict(os.environ, {"GUARDRAILS_ENABLED": "false"}, clear=False)
    def test_disabled_returns_none(self):
        ctx = MagicMock()
        result = safety_settings_download_callback(ctx)
        assert result is None

    @patch.dict(os.environ, {"GUARDRAILS_ENABLED": "true"}, clear=False)
    def test_no_bucket_name_returns_error(self):
        if "GUARDRAIL_BUCKET_NAME" in os.environ:
            del os.environ["GUARDRAIL_BUCKET_NAME"]
        ctx = MagicMock()
        result = safety_settings_download_callback(ctx)
        assert result is not None

    @patch.dict(os.environ, {
        "GUARDRAILS_ENABLED": "true",
        "GUARDRAIL_BUCKET_NAME": "mybucket",
        "GUARDRAIL_BUCKET_PREFIX": "prefix",
        "GUARDRAIL_FILE": "guardrail.json",
    })
    @patch("root_agent.content_filter.safety_settings.read_guardrail_from_gcs", return_value=None)
    def test_gcs_read_failure(self, mock_read):
        ctx = MagicMock()
        result = safety_settings_download_callback(ctx)
        assert result is not None

    @patch.dict(os.environ, {
        "GUARDRAILS_ENABLED": "true",
        "GUARDRAIL_BUCKET_NAME": "mybucket",
        "GUARDRAIL_BUCKET_PREFIX": "prefix",
        "GUARDRAIL_FILE": "guardrail.json",
    })
    @patch("root_agent.content_filter.safety_settings.save_guardrail_to_file", return_value=True)
    @patch("root_agent.content_filter.safety_settings.read_guardrail_from_gcs", return_value={"config": True})
    def test_success(self, mock_read, mock_save):
        ctx = MagicMock()
        result = safety_settings_download_callback(ctx)
        assert result is None

    @patch.dict(os.environ, {
        "GUARDRAILS_ENABLED": "true",
        "GUARDRAIL_BUCKET_NAME": "mybucket",
        "GUARDRAIL_BUCKET_PREFIX": "prefix",
        "GUARDRAIL_FILE": "guardrail.json",
    })
    @patch("root_agent.content_filter.safety_settings.save_guardrail_to_file", return_value=False)
    @patch("root_agent.content_filter.safety_settings.read_guardrail_from_gcs", return_value={"config": True})
    def test_save_failure(self, mock_read, mock_save):
        ctx = MagicMock()
        result = safety_settings_download_callback(ctx)
        assert result is not None


# ---------------------------------------------------------------------------
# safety_settings_model_callback
# ---------------------------------------------------------------------------

class TestSafetySettingsModelCallback:
    @patch.dict(os.environ, {"GUARDRAILS_ENABLED": "false"}, clear=False)
    def test_disabled_returns_none(self):
        ctx = MagicMock()
        req = MagicMock()
        result = safety_settings_model_callback(ctx, req)
        assert result is None

    @patch.dict(os.environ, {"GUARDRAILS_ENABLED": "true", "GUARDRAIL_FILE": "guardrail.json"})
    @patch("os.path.exists", return_value=False)
    def test_file_not_found_returns_none(self, mock_exists):
        ctx = MagicMock()
        req = MagicMock()
        result = safety_settings_model_callback(ctx, req)
        assert result is None

    @patch.dict(os.environ, {"GUARDRAILS_ENABLED": "true", "GUARDRAIL_FILE": "guardrail.json"})
    @patch("os.path.exists", return_value=True)
    @patch("root_agent.content_filter.safety_settings.get_safety_settings_from_file", return_value=[])
    def test_no_settings_loaded(self, mock_get, mock_exists):
        ctx = MagicMock()
        req = MagicMock()
        result = safety_settings_model_callback(ctx, req)
        assert result is None

    @patch.dict(os.environ, {"GUARDRAILS_ENABLED": "true", "GUARDRAIL_FILE": "guardrail.json"})
    @patch("os.path.exists", return_value=True)
    @patch("root_agent.content_filter.safety_settings.get_safety_settings_from_file")
    def test_settings_applied_to_request(self, mock_get, mock_exists):
        mock_settings = [MagicMock(), MagicMock()]
        mock_get.return_value = mock_settings
        ctx = MagicMock()
        req = MagicMock()
        result = safety_settings_model_callback(ctx, req)
        assert result is None
        assert req.config.safety_settings == mock_settings

    @patch.dict(os.environ, {"GUARDRAILS_ENABLED": "true", "GUARDRAIL_FILE": "guardrail.json"})
    @patch("os.path.exists", side_effect=Exception("boom"))
    def test_exception_returns_none(self, mock_exists):
        ctx = MagicMock()
        req = MagicMock()
        result = safety_settings_model_callback(ctx, req)
        assert result is None
