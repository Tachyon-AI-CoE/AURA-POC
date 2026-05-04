"""Shared fixtures and configuration for GCP Multi-Agent Orchestrator tests."""

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, Mock
import pytest

# Add src directory to Python path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Import real exceptions before mocking
from google.api_core import exceptions as real_gcp_exceptions

# Mock external dependencies before any imports
# Create proper nested mock structure for google.adk
mock_vertex_ai_rag_retrieval = MagicMock()
mock_retrieval = MagicMock()
mock_retrieval.vertex_ai_rag_retrieval = mock_vertex_ai_rag_retrieval

# Create callback_context as a proper module mock
mock_callback_context = type(sys)('callback_context')
mock_callback_context.__dict__['__path__'] = []

# Create agents module as a proper package mock
mock_agents_module = type(sys)('agents')
mock_agents_module.__dict__['__path__'] = []
mock_agents_module.__dict__['callback_context'] = mock_callback_context
mock_agents_module.__dict__['LlmAgent'] = MagicMock()
mock_agents_module.__dict__['SequentialAgent'] = MagicMock()

# Create tools module
mock_tools_module = type(sys)('tools')
mock_tools_module.__dict__['__path__'] = []
mock_tools_module.__dict__['Tool'] = MagicMock()
mock_tools_module.__dict__['retrieval'] = mock_retrieval

# Create main adk module
mock_adk = type(sys)('adk')
mock_adk.__dict__['__path__'] = []
mock_adk.__dict__['tools'] = mock_tools_module
mock_adk.__dict__['agents'] = mock_agents_module
mock_adk.__dict__['callbacks'] = MagicMock()
mock_adk.__dict__['models'] = MagicMock()

# Mock google.cloud modules
mock_cloud = type(sys)('cloud')
mock_cloud.__dict__['__path__'] = []
mock_cloud.__dict__['storage'] = MagicMock()
mock_cloud.__dict__['secretmanager'] = MagicMock()

mock_google = type(sys)('google')
mock_google.__dict__['__path__'] = []
mock_google.__dict__['cloud'] = mock_cloud
mock_google.__dict__['adk'] = mock_adk
mock_google.__dict__['api_core'] = MagicMock()
mock_google.__dict__['auth'] = MagicMock()
mock_google.__dict__['oauth2'] = MagicMock()

# Set up sys.modules mocks
sys.modules['google'] = mock_google
sys.modules['google.cloud'] = mock_cloud
sys.modules['google.cloud.storage'] = mock_cloud.storage
sys.modules['google.cloud.secretmanager'] = mock_cloud.secretmanager
sys.modules['google.adk'] = mock_adk
sys.modules['google.adk.agents'] = mock_agents_module
sys.modules['google.adk.agents.callback_context'] = mock_callback_context
sys.modules['google.adk.callbacks'] = mock_adk.callbacks
sys.modules['google.adk.tools'] = mock_tools_module
sys.modules['google.adk.tools.retrieval'] = mock_retrieval
sys.modules['google.adk.tools.retrieval.vertex_ai_rag_retrieval'] = mock_vertex_ai_rag_retrieval
sys.modules['google.adk.models'] = mock_adk.models

sys.modules['vertexai'] = MagicMock()
sys.modules['vertexai.agent_engines'] = MagicMock()

# Mock google.api_core but keep real exceptions
mock_api_core = MagicMock()
mock_api_core.exceptions = real_gcp_exceptions
sys.modules['google.api_core'] = mock_api_core
sys.modules['google.api_core.exceptions'] = real_gcp_exceptions

sys.modules['google.auth'] = MagicMock()
sys.modules['google.auth.transport'] = MagicMock()
sys.modules['google.auth.transport.requests'] = MagicMock()
sys.modules['google.oauth2'] = MagicMock()
sys.modules['google.oauth2.id_token'] = MagicMock()
sys.modules['requests'] = MagicMock()

# Mock Arize and OpenInference
mock_arize = MagicMock()
mock_arize.otel = MagicMock()
mock_arize.otel.register = MagicMock()
sys.modules['arize'] = mock_arize
sys.modules['arize.otel'] = mock_arize.otel

mock_openinference = MagicMock()
mock_openinference.instrumentation = MagicMock()
mock_openinference.instrumentation.google_adk = MagicMock()
mock_openinference.instrumentation.google_adk.GoogleADKInstrumentor = MagicMock()
mock_openinference.instrumentation.vertexai = MagicMock()
sys.modules['openinference'] = mock_openinference
sys.modules['openinference.instrumentation'] = mock_openinference.instrumentation
sys.modules['openinference.instrumentation.google_adk'] = mock_openinference.instrumentation.google_adk
sys.modules['openinference.instrumentation.vertexai'] = mock_openinference.instrumentation.vertexai

# Keep real yaml
sys.modules['yaml'] = __import__('yaml')


# Sample agent configuration data
SAMPLE_ROOT_AGENT_CONFIG = {
    "root_agent": {
        "project_id": "test-project-123",
        "region": "us-central1",
        "agent_display_name": "Test Root Agent",
        "agent_class": "LlmAgent",
        "multiagent": True,
        "model_id": "gemini-1.5-pro",
        "description": "Test agent description",
        "guardrail_enabled": True,
        "guardrail_name": "test-guardrail",
        "guardrail_url": "https://storage.cloud.google.com/test-bucket/folder1/folder2/guardrail.json",
        "arize_space_id_name": "test-space-id",
        "arize_api_key_name": "test-api-key",
        "arize_endpoint": "https://otlp.arize.com:443",
        "tools": {
            "rag": [
                {
                    "resource_id": "projects/test-project/locations/us-central1/ragCorpora/test-corpus",
                    "rag_details": {
                        "value": {
                            "datasetname": "test-dataset",
                            "vectorizeddatasetbaseid": "test-corpus-id",
                            "description": "Test RAG dataset"
                        }
                    }
                }
            ]
        },
        "sub_agents": [
            {
                "agent_name": "sub_agent_1",
                "agent_class": "LlmAgent",
                "model_id": "gemini-1.0-pro",
                "description": "First sub agent"
            }
        ]
    }
}

SAMPLE_AGENTS_JSON = [
    {
        "name": "test_agent_1",
        "agent_class": "LlmAgent",
        "model_id": "gemini-1.5-pro",
        "description": "Test agent 1"
    },
    {
        "name": "test_agent_2",
        "agent_class": "SequentialAgent",
        "description": "Test sequential agent",
        "sub_agents": [
            {
                "name": "test_agent_1",
                "agent_class": "LlmAgent"
            }
        ]
    }
]


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables for testing."""
    env_vars = {
        "ENVIRONMENT": "test",
        "LOG_LEVEL": "INFO",
        "SERVICE_ACCOUNT_NAME": "test-sa@test-project.iam.gserviceaccount.com",
        "STAGING_BUCKET_NAME": "test-staging-bucket",
        "DATA_APP_API_URL": "https://api.example.com",
        "CLOUDRUN_SERVICE_URL": "https://test-service.run.app",
        "PROJECT_ID": "test-project-123",
        "LOCATION": "us-central1"
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    return env_vars


@pytest.fixture
def sample_root_agent_config():
    """Provide sample root agent configuration."""
    return SAMPLE_ROOT_AGENT_CONFIG.copy()


@pytest.fixture
def sample_agents_json():
    """Provide sample agents JSON data."""
    return SAMPLE_AGENTS_JSON.copy()


@pytest.fixture
def mock_config_file(tmp_path, sample_root_agent_config):
    """Create a temporary config file for testing."""
    import yaml
    config_file = tmp_path / "root-agent-config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(sample_root_agent_config, f)
    return config_file


@pytest.fixture
def mock_agents_json_file(tmp_path, sample_agents_json):
    """Create a temporary agents JSON file for testing."""
    import json
    json_file = tmp_path / "agents.json"
    with open(json_file, "w") as f:
        json.dump(sample_agents_json, f)
    return json_file


@pytest.fixture(autouse=True)
def reset_config_reader():
    """Reset ConfigReader state before each test."""
    from config.config_reader import ConfigReader  # type: ignore
    ConfigReader._data = None
    yield
    ConfigReader._data = None


@pytest.fixture
def mock_vertexai():
    """Mock VertexAI client."""
    mock = MagicMock()
    mock.init = MagicMock()
    return mock


@pytest.fixture
def mock_storage_client():
    """Mock Google Cloud Storage client."""
    mock = MagicMock()
    mock.bucket = MagicMock(return_value=MagicMock())
    return mock


@pytest.fixture
def mock_llm_agent():
    """Mock LlmAgent."""
    mock = MagicMock()
    mock.build = MagicMock(return_value=mock)
    return mock
