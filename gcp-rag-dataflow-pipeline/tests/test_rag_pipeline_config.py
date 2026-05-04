"""Unit tests for config/rag_pipeline_config.py — config flattening."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config.rag_pipeline_config import get_flattened_rag_pipeline_config


class TestGetFlattenedRagPipelineConfig:
    """Test the config flattening function."""

    def _make_config(self, **overrides):
        base = {
            "rag_corpus": {
                "corpus_name": "test-corpus",
                "description": "A test corpus",
                "sync_through_rag_pipeline": True,
                "data_source": {
                    "type": "gcs",
                    "staging_bucket": "my-bucket",
                    "jira_data_source_config": {
                        "jira_projects": ["PROJ1"],
                        "custom_query": ["q1"],
                        "email": "a@b.com",
                        "server_uri": "https://jira.example.com",
                        "api_secret_key": "secret",
                        "sync_through_rag_pipeline": True,
                    },
                    "sharepoint_data_source_config": {
                        "client_id": "cid",
                        "tenant_id": "tid",
                        "site_name": "site",
                        "folder_path": "/docs",
                        "drive_name": "drv",
                        "api_secret_key": "sp-secret",
                        "sync_through_rag_pipeline": False,
                    },
                },
                "embedding_config": {
                    "embedding_model": "textembedding-gecko",
                    "chunk_size": 512,
                    "chunk_overlap": 100,
                    "max_embedding_requests_per_min": 500,
                    "parser_type": "layout",
                    "llm_parser": {
                        "model": "gemini-pro",
                        "custom_prompt": "summarise",
                    },
                },
                "vector_db": {
                    "type": "vertexvectorsearch",
                    "vector_search_config": {
                        "dimensions": 256,
                        "approximate_neighbours_count": 20,
                        "distance_measure_type": "DOT_PRODUCT_DISTANCE",
                    },
                    "rag_managed_db_config": {
                        "retrieval_strategy": "ANN",
                    },
                },
                "summarization": {
                    "corpus_summarization": True,
                    "summarization_instructions": "Be brief",
                },
                "metadata": {
                    "metadata_extractor": "custom",
                    "metadata_fields": ["title", "author"],
                },
            }
        }
        base["rag_corpus"].update(overrides)
        return base

    def test_corpus_name_extracted(self):
        result = get_flattened_rag_pipeline_config(self._make_config())
        assert result["corpus_name"] == "test-corpus"

    def test_description_alias(self):
        result = get_flattened_rag_pipeline_config(self._make_config())
        assert result["description"] == "A test corpus"
        assert result["corpus_description"] == "A test corpus"

    def test_data_source_type(self):
        result = get_flattened_rag_pipeline_config(self._make_config())
        assert result["data_source_type"] == "gcs"

    def test_staging_bucket(self):
        result = get_flattened_rag_pipeline_config(self._make_config())
        assert result["data_staging_bucket"] == "my-bucket"

    def test_jira_fields_extracted(self):
        result = get_flattened_rag_pipeline_config(self._make_config())
        assert result["jira_projects"] == ["PROJ1"]
        assert result["jira_email"] == "a@b.com"
        assert result["jira_server_uri"] == "https://jira.example.com"
        assert result["jira_api_secret_key"] == "secret"

    def test_sharepoint_fields_extracted(self):
        result = get_flattened_rag_pipeline_config(self._make_config())
        assert result["sharepoint_client_id"] == "cid"
        assert result["sharepoint_tenant_id"] == "tid"
        assert result["sharepoint_site_name"] == "site"

    def test_embedding_config_extracted(self):
        result = get_flattened_rag_pipeline_config(self._make_config())
        assert result["embedding_model"] == "textembedding-gecko"
        assert result["chunk_size"] == 512
        assert result["chunk_overlap"] == 100
        assert result["parser_type"] == "layout"

    def test_llm_parser_fields(self):
        result = get_flattened_rag_pipeline_config(self._make_config())
        assert result["llm_parser_model"] == "gemini-pro"
        assert result["llm_custom_prompt"] == "summarise"

    def test_vector_db_fields(self):
        result = get_flattened_rag_pipeline_config(self._make_config())
        assert result["vector_db_type"] == "vertexvectorsearch"
        assert result["vector_db_dimensions"] == 256
        assert result["approximate_neighbours_count"] == 20
        assert result["distance_measure_type"] == "DOT_PRODUCT_DISTANCE"

    def test_retrieval_strategy(self):
        result = get_flattened_rag_pipeline_config(self._make_config())
        assert result["retrieval_strategy"] == "ANN"

    def test_summarization_fields(self):
        result = get_flattened_rag_pipeline_config(self._make_config())
        assert result["pre_corpus_summarization"] is True
        assert result["custom_summarization_prompt_instructions"] == "Be brief"

    def test_metadata_fields(self):
        result = get_flattened_rag_pipeline_config(self._make_config())
        assert result["metadata_extractor"] == "custom"
        assert result["metadata_fields"] == ["title", "author"]

    def test_empty_config_uses_defaults(self):
        result = get_flattened_rag_pipeline_config({"rag_corpus": {}})
        assert result["corpus_name"] == ""
        assert result["chunk_size"] == 1000
        assert result["chunk_overlap"] == 200
        assert result["vector_db_dimensions"] == 768
        assert result["pre_corpus_summarization"] is False

    def test_missing_rag_corpus_key(self):
        result = get_flattened_rag_pipeline_config({})
        assert result["corpus_name"] == ""
        assert result["data_source_type"] is None
