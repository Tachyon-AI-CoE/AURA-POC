"""Tests for root_agent/tools/rag_tool.py — all functions."""

import sys
import os
import types
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
class DummyRagResource:
    def __init__(self, *args, **kwargs):
        self.rag_corpus = kwargs.get('rag_corpus', 'dummy_corpus')
sys.modules['vertexai.rag'] = types.SimpleNamespace(RagResource=DummyRagResource)

import pytest
from unittest.mock import patch, MagicMock
from root_agent.tools.rag_tool import (
    create_rag_resource_from_corpus_id,
    create_rag_resource_from_path,
    build_rag_resources_from_config,
    create_vertex_ai_rag_retrieval,
    create_rag_tool_from_yaml_config,
)


# ---------------------------------------------------------------------------
# Original tests
# ---------------------------------------------------------------------------

def test_create_rag_resource_from_corpus_id():
    resource = create_rag_resource_from_corpus_id("corpus1", "proj", "loc")
    assert hasattr(resource, "rag_corpus")
    assert "corpus1" in resource.rag_corpus

def test_create_rag_resource_from_path():
    resource = create_rag_resource_from_path("projects/proj/locations/loc/ragCorpora/corpus1")
    assert hasattr(resource, "rag_corpus")
    assert resource.rag_corpus.startswith("projects/")

def test_build_rag_resources_from_config_str():
    resources = build_rag_resources_from_config("projects/proj/locations/loc/ragCorpora/corpus1")
    assert isinstance(resources, list)
    assert resources[0].rag_corpus.startswith("projects/")

def test_build_rag_resources_from_config_list():
    resources = build_rag_resources_from_config(["projects/proj/locations/loc/ragCorpora/corpus1", "projects/proj/locations/loc/ragCorpora/corpus2"])
    assert len(resources) == 2
    assert all(r.rag_corpus.startswith("projects/") for r in resources)

def test_build_rag_resources_from_config_empty():
    assert build_rag_resources_from_config([]) == []
    assert build_rag_resources_from_config("") == []


# ---------------------------------------------------------------------------
# create_vertex_ai_rag_retrieval
# ---------------------------------------------------------------------------

class TestCreateVertexAiRagRetrieval:
    def test_success(self):
        resource = create_rag_resource_from_path("projects/p/locations/l/ragCorpora/c")
        tool = create_vertex_ai_rag_retrieval(
            name="rag",
            description="desc",
            rag_resources=[resource],
        )
        assert tool.name == "rag"

    def test_custom_params(self):
        resource = create_rag_resource_from_path("projects/p/locations/l/ragCorpora/c")
        tool = create_vertex_ai_rag_retrieval(
            name="rag",
            description="desc",
            rag_resources=[resource],
            similarity_top_k=5,
            vector_distance_threshold=0.9,
        )
        assert tool is not None

    def test_missing_name_raises(self):
        resource = create_rag_resource_from_path("projects/p/locations/l/ragCorpora/c")
        with pytest.raises(ValueError, match="name"):
            create_vertex_ai_rag_retrieval("", "desc", [resource])

    def test_missing_description_raises(self):
        resource = create_rag_resource_from_path("projects/p/locations/l/ragCorpora/c")
        with pytest.raises(ValueError, match="description"):
            create_vertex_ai_rag_retrieval("rag", "", [resource])

    def test_missing_resources_raises(self):
        with pytest.raises(ValueError, match="RAG resource"):
            create_vertex_ai_rag_retrieval("rag", "desc", [])


# ---------------------------------------------------------------------------
# build_rag_resources_from_config (extended)
# ---------------------------------------------------------------------------

class TestBuildRagResourcesFromConfigExtra:
    def test_full_paths_list(self):
        result = build_rag_resources_from_config(
            ["projects/p/locations/l/ragCorpora/c1", "projects/p/locations/l/ragCorpora/c2"]
        )
        assert len(result) == 2

    def test_corpus_ids_with_project_and_location(self):
        result = build_rag_resources_from_config(["c1", "c2"], project_id="p", location="l")
        assert len(result) == 2
        assert "projects/p/locations/l/ragCorpora/c1" in result[0].rag_corpus

    def test_corpus_ids_without_project_falls_back_to_path(self):
        result = build_rag_resources_from_config(["c1"])
        assert len(result) == 1
        assert result[0].rag_corpus == "c1"

    def test_filters_empty_strings(self):
        result = build_rag_resources_from_config(["", "", "c1"])
        assert len(result) == 1


# ---------------------------------------------------------------------------
# create_rag_tool_from_yaml_config
# ---------------------------------------------------------------------------

class TestCreateRagToolFromYamlConfig:
    def test_basic_config_with_rag_resources_list_of_strings(self):
        config = {
            "name": "rag1",
            "description": "my rag",
            "config": {
                "rag_resources": ["projects/p/locations/l/ragCorpora/c1"],
                "similarity_top_k": 5,
                "vector_distance_threshold": 0.85,
            },
        }
        tool = create_rag_tool_from_yaml_config(config)
        assert tool is not None
        assert tool.name == "rag1"

    def test_rag_resources_as_dict_objects(self):
        config = {
            "name": "rag1",
            "config": {
                "rag_resources": [
                    {"rag_resource": "projects/p/locations/l/ragCorpora/c1"},
                    {"rag_resource": "projects/p/locations/l/ragCorpora/c2"},
                ],
            },
        }
        tool = create_rag_tool_from_yaml_config(config)
        assert tool is not None

    def test_rag_resources_as_single_dict(self):
        config = {
            "name": "rag1",
            "config": {
                "rag_resources": {"rag_resource": "projects/p/locations/l/ragCorpora/c1"},
            },
        }
        tool = create_rag_tool_from_yaml_config(config)
        assert tool is not None

    def test_no_rag_resources_returns_none(self):
        config = {"name": "rag1", "config": {}}
        tool = create_rag_tool_from_yaml_config(config)
        assert tool is None

    def test_empty_rag_resources_list_returns_none(self):
        config = {"name": "rag1", "config": {"rag_resources": []}}
        tool = create_rag_tool_from_yaml_config(config)
        assert tool is None

    def test_global_config_fallback_for_project_id(self):
        config = {
            "name": "rag1",
            "config": {
                "rag_resources": [{"rag_resource": "corpus1"}],
            },
        }
        global_config = {"project_id": "gp", "location": "us-central1"}
        tool = create_rag_tool_from_yaml_config(config, global_config=global_config)
        assert tool is not None

    def test_local_project_id_overrides_global(self):
        config = {
            "name": "rag1",
            "config": {
                "rag_resources": [{"rag_resource": "corpus1"}],
                "project_id": "local_p",
                "location": "local_l",
            },
        }
        global_config = {"project_id": "global_p"}
        tool = create_rag_tool_from_yaml_config(config, global_config=global_config)
        assert tool is not None

    def test_defaults_applied(self):
        config = {
            "config": {
                "rag_resources": ["projects/p/locations/l/ragCorpora/c1"],
            },
        }
        tool = create_rag_tool_from_yaml_config(config)
        assert tool.name == "VertexAI_RAG_Tool"

    def test_exception_returns_none(self):
        with patch("root_agent.tools.rag_tool.build_rag_resources_from_config", side_effect=Exception("boom")):
            tool = create_rag_tool_from_yaml_config(
                {"name": "r", "config": {"rag_resources": ["c1"]}}
            )
            assert tool is None

    def test_mixed_rag_resources_strings_and_dicts(self):
        config = {
            "name": "rag1",
            "config": {
                "rag_resources": [
                    "projects/p/locations/l/ragCorpora/c1",
                    {"rag_resource": "projects/p/locations/l/ragCorpora/c2"},
                ],
            },
        }
        tool = create_rag_tool_from_yaml_config(config)
        assert tool is not None
