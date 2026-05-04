"""Unit tests for utils/rag_pipeline_utils.py."""

import sys
import os
import json
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.rag_pipeline_utils import convert_blob_to_json, convert_string_to_json


class TestConvertBlobToJson:
    """Test convert_blob_to_json function."""

    def test_valid_blob(self):
        blob = MagicMock()
        blob.download_as_text.return_value = '{"key": "value"}'
        result = convert_blob_to_json(blob)
        assert result == {"key": "value"}

    def test_blob_with_nested_json(self):
        blob = MagicMock()
        blob.download_as_text.return_value = '{"a": {"b": 1}}'
        result = convert_blob_to_json(blob)
        assert result["a"]["b"] == 1

    def test_blob_with_list(self):
        blob = MagicMock()
        blob.download_as_text.return_value = '[1, 2, 3]'
        result = convert_blob_to_json(blob)
        assert result == [1, 2, 3]

    def test_invalid_json_blob_raises(self):
        blob = MagicMock()
        blob.download_as_text.return_value = 'not json'
        with pytest.raises(json.JSONDecodeError):
            convert_blob_to_json(blob)


class TestConvertStringToJson:
    """Test convert_string_to_json function."""

    def test_valid_json_string(self):
        result = convert_string_to_json('{"name": "test"}')
        assert result == {"name": "test"}

    def test_json_array_string(self):
        result = convert_string_to_json('[1, 2]')
        assert result == [1, 2]

    def test_invalid_string_raises(self):
        with pytest.raises(json.JSONDecodeError):
            convert_string_to_json("{bad")

    def test_empty_object(self):
        result = convert_string_to_json('{}')
        assert result == {}
