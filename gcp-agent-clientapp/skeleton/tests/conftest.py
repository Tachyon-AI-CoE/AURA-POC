"""
Pytest configuration and shared fixtures for gcp-agent-clientapp tests
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
import pytest

# Mock environment variables BEFORE importing any modules
os.environ.setdefault('LOG_LEVEL', 'INFO')
os.environ.setdefault('PROJECT_ID', 'test-project-123')
os.environ.setdefault('REGION', 'us-central1')
os.environ.setdefault('AGENT_ID', 'test-agent-456')
os.environ.setdefault('PROJECT_NUMBER', '123456789')

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Mock external dependencies before any imports
sys.modules['vertexai'] = MagicMock()
sys.modules['vertexai.agent_engines'] = MagicMock()
sys.modules['streamlit'] = MagicMock()
sys.modules['streamlit.web'] = MagicMock()
sys.modules['streamlit.web.bootstrap'] = MagicMock()


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock all required environment variables"""
    env_vars = {
        'LOG_LEVEL': 'DEBUG',
        'PROJECT_ID': 'test-project-123',
        'REGION': 'us-central1',
        'AGENT_ID': 'test-agent-456',
        'PROJECT_NUMBER': '123456789',
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def mock_config_file(tmp_path):
    """Create a mock configuration JSON file"""
    import json
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "configuration.json"
    
    config_data = {
        "PROJECT_ID": "test-project",
        "REGION": "us-central1",
        "AGENT_ID": "agent-123",
        "PROJECT_NUMBER": "987654321",
        "NAME": "Test Agent",
        "DESCRIPTION": "Test agent description"
    }
    
    config_file.write_text(json.dumps(config_data))
    return str(config_file)


@pytest.fixture
def mock_yaml_config_file(tmp_path):
    """Create a mock configuration YAML file"""
    import yaml
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "configuration.yaml"
    
    config_data = {
        "PROJECT_ID": "test-project-yaml",
        "REGION": "europe-west1",
        "AGENT_ID": "agent-yaml-123",
        "PROJECT_NUMBER": "111222333",
        "NAME": "YAML Test Agent",
        "DESCRIPTION": "YAML test agent description"
    }
    
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    return str(config_file)


@pytest.fixture
def sample_agent_response():
    """Sample successful agent response with summary"""
    return {
        "summary": "The capital of France is Paris.",
        "status": "completed"
    }


@pytest.fixture
def sample_agent_response_output():
    """Sample agent response with output field"""
    return {
        "output": "The weather is sunny today.",
        "status": "completed"
    }


@pytest.fixture
def sample_agent_response_content():
    """Sample agent response with content/parts structure"""
    return {
        "content": {
            "parts": [
                {"text": "This is the response text from the agent."}
            ]
        },
        "status": "completed"
    }


@pytest.fixture
def sample_agent_response_plain():
    """Sample agent response with response field"""
    return {
        "response": "This is a plain response.",
        "status": "completed"
    }


@pytest.fixture
async def mock_async_agent_engine():
    """Mock async agent engine for AsyncStreamQueryable"""
    mock_engine = AsyncMock()
    
    async def mock_stream(*args, **kwargs):
        yield {"summary": "Mocked response", "status": "success"}
    
    mock_engine.async_stream_query = mock_stream
    return mock_engine


@pytest.fixture
def mock_sync_agent_engine():
    """Mock sync agent engine for Queryable"""
    mock_engine = MagicMock()
    mock_engine.query.return_value = {
        "summary": "Sync mocked response",
        "status": "success"
    }
    return mock_engine


@pytest.fixture
def mock_vertexai_init(monkeypatch):
    """Mock vertexai.init function"""
    mock_init = MagicMock()
    monkeypatch.setattr('vertexai.init', mock_init)
    return mock_init


@pytest.fixture
def mock_agent_engines_get():
    """Mock agent_engines.get function"""
    return MagicMock()
