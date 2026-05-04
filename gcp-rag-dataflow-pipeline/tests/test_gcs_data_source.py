"""Unit tests for data_sources/gcs_data_source.py."""

import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data_sources.gcs_data_source import get_source_path, validate_config


class TestGetSourcePath:
    """Test get_source_path function."""

    def test_with_filename(self):
        result = get_source_path("my-bucket", "data.csv")
        assert result == "gs://my-bucket/data.csv"

    def test_without_filename(self):
        result = get_source_path("my-bucket")
        assert result == "gs://my-bucket"

    def test_none_filename(self):
        result = get_source_path("my-bucket", None)
        assert result == "gs://my-bucket"

    def test_empty_filename(self):
        result = get_source_path("my-bucket", "")
        assert result == "gs://my-bucket"


class TestGcsValidateConfig:
    """Test GCS validate_config function."""

    def test_valid_config(self):
        assert validate_config({"staging_bucket": "my-bucket"}) is True

    def test_missing_staging_bucket(self):
        assert validate_config({}) is False

    def test_empty_staging_bucket(self):
        assert validate_config({"staging_bucket": ""}) is False

    def test_none_staging_bucket(self):
        assert validate_config({"staging_bucket": None}) is False
