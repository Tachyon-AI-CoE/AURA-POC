"""
Pytest configuration and shared fixtures for gcp-agent-api tests
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
import pytest

# Mock environment variables BEFORE importing any modules
os.environ.setdefault('PROJECT_ID', 'test-project')
os.environ.setdefault('LOCATION', 'us-central1')
os.environ.setdefault('PROJECT_NUMBER', '123456789')
os.environ.setdefault('ARIZE_API_KEY', 'test-arize-key')
os.environ.setdefault('ARIZE_SPACE_ID', 'test-arize-space')
os.environ.setdefault('ARIZE_API_KEY_VALUE', 'test-api-key-value')
os.environ.setdefault('ARIZE_SPACE_ID_VALUE', 'test-space-id-value')
os.environ.setdefault('LOG_LEVEL', 'INFO')

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock all required environment variables"""
    env_vars = {
        'PROJECT_ID': 'test-project-123',
        'LOCATION': 'us-central1',
        'PROJECT_NUMBER': '987654321',
        'ARIZE_API_KEY': 'mock-api-key',
        'ARIZE_SPACE_ID': 'mock-space-id',
        'LOG_LEVEL': 'DEBUG',
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def sample_invoke_request():
    """Sample request payload for invoke-agent endpoint"""
    return {
        "userInput": "What is the weather today?",
        "agentId": "agent-123",
        "userId": "user-456",
        "agentDisplayName": "WeatherAgent",
        "agentVersion": "1",
        "sessionId": "session-789"
    }


@pytest.fixture
def sample_create_session_request():
    """Sample request payload for create-session endpoint"""
    return {
        "userId": "user-123",
        "agentId": "agent-456"
    }


@pytest.fixture
def sample_list_sessions_request():
    """Sample request payload for list-sessions endpoint"""
    return {
        "userId": "user-123",
        "agentId": "agent-456"
    }


@pytest.fixture
def sample_get_session_request():
    """Sample request payload for get-session endpoint"""
    return {
        "userId": "user-123",
        "sessionId": "session-456",
        "agentId": "agent-789"
    }


@pytest.fixture
def sample_delete_session_request():
    """Sample request payload for delete-session endpoint"""
    return {
        "userId": "user-123",
        "sessionId": "session-456",
        "agentId": "agent-789"
    }


@pytest.fixture
def sample_search_memory_request():
    """Sample request payload for search-memory endpoint"""
    return {
        "userId": "user-123",
        "query": "previous conversations about weather",
        "agentId": "agent-456"
    }


@pytest.fixture
def mock_agent_response():
    """Mock successful agent response"""
    return {
        "response": "The weather is sunny today!",
        "status": "completed",
        "sessionId": "session-789"
    }


@pytest.fixture
def mock_vertexai(monkeypatch):
    """Mock vertexai module"""
    mock_vertex = MagicMock()
    sys.modules['vertexai'] = mock_vertex
    sys.modules['vertexai.agent_engines'] = MagicMock()
    return mock_vertex


@pytest.fixture
def mock_arize_modules(monkeypatch):
    """Mock Arize and OpenTelemetry modules"""
    sys.modules['arize'] = MagicMock()
    sys.modules['arize.otel'] = MagicMock()
    sys.modules['opentelemetry'] = MagicMock()
    sys.modules['opentelemetry.trace'] = MagicMock()
    sys.modules['openinference'] = MagicMock()
    sys.modules['openinference.instrumentation'] = MagicMock()
    sys.modules['openinference.instrumentation.vertexai'] = MagicMock()


@pytest.fixture
def mock_secret_manager():
    """Mock Google Cloud Secret Manager"""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.payload.data.decode.return_value = "mock-secret-value"
    mock_client.access_secret_version.return_value = mock_response
    return mock_client


@pytest.fixture
async def async_mock_agent_engine():
    """Mock async agent engine"""
    mock_engine = AsyncMock()
    
    async def mock_stream():
        yield {"response": "test response", "status": "success"}
    
    mock_engine.async_stream_query = AsyncMock(return_value=mock_stream())
    mock_engine.async_create_session = AsyncMock(return_value=mock_stream())
    mock_engine.async_list_sessions = AsyncMock(return_value=mock_stream())
    mock_engine.async_get_session = AsyncMock(return_value=mock_stream())
    mock_engine.async_delete_session = AsyncMock(return_value=mock_stream())
    mock_engine.async_search_memory = AsyncMock(return_value=mock_stream())
    
    return mock_engine
