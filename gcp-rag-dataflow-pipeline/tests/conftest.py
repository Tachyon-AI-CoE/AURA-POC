"""
Pytest configuration and shared fixtures for gcp-rag-dataflow-pipeline tests.

This module provides:
- sys.path manipulation for proper module imports
- Mock modules for external dependencies not available in test environment
- Common test fixtures for pipeline configuration and GCS mocking
"""

import sys
import os
import types
from unittest.mock import MagicMock, Mock

# ---------------------------------------------------------------------------
# Mock external modules that are not installed in the test environment.
# These mocks must be registered BEFORE any source module is imported,
# because the source files do top-level imports of these libraries.
# ---------------------------------------------------------------------------

def _create_mock_module(name, attrs=None):
    """Create a mock module and register it in sys.modules."""
    mod = types.ModuleType(name)
    if attrs:
        for k, v in attrs.items():
            setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


def _ensure_mock_modules():
    """Register mock modules for all missing external dependencies."""

    # ---- apache_beam and submodules ----
    if "apache_beam" not in sys.modules:
        # Create a real DoFn base class so source DoFn subclasses work properly
        class _DoFn:
            pass

        # Create a PipelineOptions that supports _add_argparse_args and view_as
        import argparse

        class _PipelineOptions:
            _known_subclasses = {}

            def __init__(self, args=None):
                self._args = args or []
                self._parsed = {}
                # Parse args through all registered subclasses
                for cls in _PipelineOptions._known_subclasses.values():
                    parser = argparse.ArgumentParser(add_help=False)
                    if hasattr(cls, '_add_argparse_args'):
                        cls._add_argparse_args(parser)
                    parsed, _ = parser.parse_known_args(self._args)
                    self._parsed[cls] = parsed

            def __init_subclass__(cls, **kwargs):
                super().__init_subclass__(**kwargs)
                _PipelineOptions._known_subclasses[cls.__name__] = cls

            def view_as(self, cls):
                if cls not in self._parsed:
                    parser = argparse.ArgumentParser(add_help=False)
                    if hasattr(cls, '_add_argparse_args'):
                        cls._add_argparse_args(parser)
                    parsed, _ = parser.parse_known_args(self._args)
                    self._parsed[cls] = parsed
                return self._parsed[cls]

            def get_all_options(self):
                return {}

            @classmethod
            def _add_argparse_args(cls, parser):
                pass

        beam = _create_mock_module("apache_beam")
        beam.DoFn = _DoFn
        beam.ParDo = MagicMock()
        beam.Pipeline = MagicMock()
        beam.Create = MagicMock()
        beam.Filter = MagicMock()
        _create_mock_module("apache_beam.io", {"filesystems": MagicMock()})
        fs_mod = _create_mock_module("apache_beam.io.filesystems")
        fs_mod.FileSystems = MagicMock()
        _create_mock_module("apache_beam.options", {"pipeline_options": MagicMock()})
        po_mod = _create_mock_module("apache_beam.options.pipeline_options")
        po_mod.PipelineOptions = _PipelineOptions
        po_mod._BeamArgumentParser = MagicMock
        _create_mock_module("apache_beam.testing", {"test_pipeline": MagicMock(), "util": MagicMock()})
        _create_mock_module("apache_beam.testing.test_pipeline", {"TestPipeline": MagicMock()})
        _create_mock_module("apache_beam.testing.util", {"assert_that": MagicMock(), "equal_to": MagicMock()})

    # ---- vertexai.rag ----
    if "vertexai.rag" not in sys.modules:
        import vertexai
        rag_mod = _create_mock_module("vertexai.rag")
        rag_mod.JiraQuery = MagicMock()
        rag_mod.JiraSource = MagicMock()
        rag_mod.RagManagedDb = MagicMock()
        rag_mod.KNN = MagicMock()
        rag_mod.ANN = MagicMock()
        rag_mod.VertexVectorSearch = MagicMock()
        rag_mod.RagVectorDbConfig = MagicMock()
        rag_mod.list_corpora = MagicMock(return_value=[])
        rag_mod.create_corpus = MagicMock()
        rag_mod.import_files = MagicMock()
        rag_mod.TransformationConfig = MagicMock()
        rag_mod.ChunkingConfig = MagicMock()
        vertexai.rag = rag_mod

    # ---- google.cloud.eventarc_v1 ----
    if "google.cloud.eventarc_v1" not in sys.modules:
        ev_mod = _create_mock_module("google.cloud.eventarc_v1")
        ev_mod.EventarcClient = MagicMock()
        ev_mod.Trigger = MagicMock()
        ev_mod.EventFilter = MagicMock()
        ev_mod.Destination = MagicMock()
        ev_mod.CloudRun = MagicMock()

    # ---- functions_framework ----
    if "functions_framework" not in sys.modules:
        ff_mod = _create_mock_module("functions_framework")
        ff_mod.cloud_event = lambda f: f  # decorator passthrough

    # ---- cloudevents ----
    if "cloudevents" not in sys.modules:
        _create_mock_module("cloudevents")
    if "cloudevents.http" not in sys.modules:
        ce_mod = _create_mock_module("cloudevents.http")
        ce_mod.CloudEvent = MagicMock

    # ---- flask ----
    if "flask" not in sys.modules:
        flask_mod = _create_mock_module("flask")
        flask_mod.make_response = MagicMock()

    # ---- google.adk and submodules ----
    for mod_name in [
        "google.adk",
        "google.adk.agents",
        "google.adk.agents.callback_context",
        "google.adk.models",
        "google.adk.runners",
        "google.adk.sessions",
    ]:
        if mod_name not in sys.modules:
            m = _create_mock_module(mod_name)
            if mod_name == "google.adk.agents":
                m.LlmAgent = MagicMock()
            elif mod_name == "google.adk.agents.callback_context":
                m.CallbackContext = MagicMock
            elif mod_name == "google.adk.models":
                m.LlmResponse = MagicMock
            elif mod_name == "google.adk.runners":
                m.Runner = MagicMock()
            elif mod_name == "google.adk.sessions":
                m.InMemorySessionService = MagicMock()

    # ---- google.genai ----
    for mod_name in ["google.genai", "google.genai.types"]:
        if mod_name not in sys.modules:
            m = _create_mock_module(mod_name)
            if mod_name == "google.genai.types":
                m.Content = MagicMock()
                m.Part = MagicMock()

    # ---- PyPDF2 ----
    if "PyPDF2" not in sys.modules:
        pdf_mod = _create_mock_module("PyPDF2")
        pdf_mod.PdfReader = MagicMock()

    # ---- python-docx ----
    if "docx" not in sys.modules:
        docx_mod = _create_mock_module("docx")
        docx_mod.Document = MagicMock()

    # ---- google.auth / google.oauth2 (may be missing) ----
    for mod_name in ["google.auth", "google.auth.transport", "google.auth.transport.requests",
                      "google.oauth2", "google.oauth2.id_token"]:
        if mod_name not in sys.modules:
            m = _create_mock_module(mod_name)
            if "requests" in mod_name:
                m.Request = MagicMock()
            if "id_token" in mod_name:
                m.fetch_id_token = MagicMock(return_value="mock-token")

    # ---- google.api_core.exceptions (for eventarc tests) ----
    if "google.api_core" not in sys.modules:
        _create_mock_module("google.api_core")
    if "google.api_core.exceptions" not in sys.modules:
        exc_mod = _create_mock_module("google.api_core.exceptions")

        class _AlreadyExists(Exception):
            pass

        exc_mod.AlreadyExists = _AlreadyExists


# Run mock registration immediately when conftest is loaded
_ensure_mock_modules()


# ---------------------------------------------------------------------------
# Add src directory to Python path
# ---------------------------------------------------------------------------
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Also add the summariser_agent directory for direct agent imports
agent_path = os.path.join(src_path, "agents", "summariser_agent")
if agent_path not in sys.path:
    sys.path.insert(0, agent_path)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------
import pytest


@pytest.fixture
def mock_storage_client():
    """Mock Google Cloud Storage client."""
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    return mock_client


@pytest.fixture
def sample_pipeline_config():
    """Sample RAG pipeline configuration for testing."""
    return {
        "corpus_name": "test-corpus",
        "corpus_description": "Test corpus description",
        "project_id": "test-project",
        "region": "us-east4",
        "vector_db_type": "RagManagedDb",
        "retrieval_strategy": "KNN",
        "data_source_type": "gcs",
        "staging_bucket": "test-staging-bucket",
        "result_bucket": "test-result-bucket",
        "audit_bucket": "test-audit-bucket",
        "chunk_size": 512,
        "chunk_overlap": 100,
        "embedding_model": "text-embedding-004",
        "status_webhook_url": "https://test.webhook.com",
    }


@pytest.fixture
def sample_rag_config():
    """Sample nested RAG config as it arrives from GCS config file."""
    return {
        "rag_corpus": {
            "corpus_name": "test-corpus",
            "description": "Test corpus",
            "data_source": {
                "type": "gcs",
                "staging_bucket": "test-staging-bucket",
            },
            "embedding_config": {
                "embedding_model": "text-embedding-004",
                "chunk_size": 512,
                "chunk_overlap": 100,
            },
            "vector_db": {
                "type": "RagManagedDb",
                "rag_managed_db_config": {"retrieval_strategy": "KNN"},
            },
        }
    }
