"""Unit tests for validators/config_validation.py."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from validators.config_validation import validate_config, validate_gcs_eventfile_pattern


class TestValidateConfig:
    """Test the validate_config function."""

    def _valid_config(self):
        return {
            "data_source_type": "gcs",
            "corpus_name": "test-corpus",
            "vector_db_type": "ragmanageddb",
            "chunk_size": 512,
            "chunk_overlap": 100,
            "embedding_model": "textembedding-gecko",
        }

    def test_valid_config_returns_true(self):
        assert validate_config(self._valid_config()) is True

    def test_missing_data_source_type(self):
        cfg = self._valid_config()
        cfg["data_source_type"] = ""
        assert validate_config(cfg) is False

    def test_missing_corpus_name(self):
        cfg = self._valid_config()
        del cfg["corpus_name"]
        assert validate_config(cfg) is False

    def test_missing_vector_db_type(self):
        cfg = self._valid_config()
        cfg["vector_db_type"] = ""
        assert validate_config(cfg) is False

    def test_missing_chunk_size(self):
        cfg = self._valid_config()
        cfg["chunk_size"] = 0
        assert validate_config(cfg) is False

    def test_missing_embedding_model(self):
        cfg = self._valid_config()
        cfg["embedding_model"] = ""
        assert validate_config(cfg) is False

    def test_all_fields_missing(self):
        assert validate_config({}) is False

    def test_none_values_treated_as_missing(self):
        cfg = self._valid_config()
        cfg["corpus_name"] = None
        assert validate_config(cfg) is False


class TestValidateGcsEventfilePattern:
    """Test the validate_gcs_eventfile_pattern function."""

    def test_valid_json_pattern(self):
        config_data = {"rag_corpus": {"corpus_name": "my-corpus"}}
        result = validate_gcs_eventfile_pattern("rag_my-corpus_config.json", config_data)
        assert result is True

    def test_valid_yaml_pattern(self):
        config_data = {"rag_corpus": {"corpus_name": "test-corpus"}}
        assert validate_gcs_eventfile_pattern("rag_test-corpus_config.yaml", config_data) is True

    def test_valid_yml_pattern(self):
        config_data = {"rag_corpus": {"corpus_name": "test-corpus"}}
        assert validate_gcs_eventfile_pattern("rag_test-corpus_config.yml", config_data) is True

    def test_valid_txt_pattern(self):
        config_data = {"rag_corpus": {"corpus_name": "test-corpus"}}
        assert validate_gcs_eventfile_pattern("rag_test-corpus_config.txt", config_data) is True

    def test_invalid_pattern_raises(self):
        with pytest.raises(ValueError, match="Invalid config file pattern"):
            validate_gcs_eventfile_pattern("bad_file.json", {})

    def test_missing_corpus_name_in_config_raises(self):
        with pytest.raises(ValueError, match="Corpus name not found"):
            validate_gcs_eventfile_pattern("rag_test_config.json", {"rag_corpus": {}})

    def test_corpus_name_mismatch_raises(self):
        config_data = {"rag_corpus": {"corpus_name": "other-corpus"}}
        with pytest.raises(ValueError, match="Corpus name mismatch"):
            validate_gcs_eventfile_pattern("rag_my-corpus_config.json", config_data)

    def test_top_level_corpus_name_fallback(self):
        config_data = {"corpus_name": "my-corpus"}
        assert validate_gcs_eventfile_pattern("rag_my-corpus_config.json", config_data) is True

    def test_underscores_normalized_to_hyphens(self):
        config_data = {"rag_corpus": {"corpus_name": "my-corpus"}}
        assert validate_gcs_eventfile_pattern("rag_my_corpus_config.json", config_data) is True

    def test_no_extension_raises(self):
        with pytest.raises(ValueError, match="Invalid config file pattern"):
            validate_gcs_eventfile_pattern("rag_test_config", {})
