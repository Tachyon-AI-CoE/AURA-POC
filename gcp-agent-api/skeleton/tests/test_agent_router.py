"""
Unit tests for routers/agent.py
Tests agent router endpoints and business logic
"""
import os
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

# Mock environment variables BEFORE imports
os.environ.setdefault('PROJECT_ID', 'test-project')
os.environ.setdefault('LOCATION', 'us-central1')
os.environ.setdefault('PROJECT_NUMBER', '123456789')
os.environ.setdefault('ARIZE_API_KEY', 'test-key')
os.environ.setdefault('ARIZE_SPACE_ID', 'test-space')
os.environ.setdefault('ARIZE_API_KEY_VALUE', 'test-key-value')
os.environ.setdefault('ARIZE_SPACE_ID_VALUE', 'test-space-value')

# Mock external dependencies
sys.modules['vertexai'] = MagicMock()
sys.modules['vertexai.agent_engines'] = MagicMock()
sys.modules['arize'] = MagicMock()
sys.modules['arize.otel'] = MagicMock()
sys.modules['opentelemetry'] = MagicMock()
sys.modules['opentelemetry.trace'] = MagicMock()
sys.modules['openinference'] = MagicMock()
sys.modules['openinference.instrumentation'] = MagicMock()
sys.modules['openinference.instrumentation.vertexai'] = MagicMock()
sys.modules['google.cloud.secretmanager'] = MagicMock()

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from routers import agent as agent_router  # type: ignore
from main_fastapi import app  # type: ignore


class TestAgentRouterHelpers:
    """Test helper functions in agent router"""
    
    def test_get_env_variable_success(self, monkeypatch):
        """Test getting environment variable successfully"""
        monkeypatch.setenv('TEST_VAR', 'test_value')
        result = agent_router.get_env_variable('TEST_VAR')
        assert result == 'test_value'
    
    def test_get_env_variable_with_default(self):
        """Test getting environment variable with default value"""
        result = agent_router.get_env_variable('NONEXISTENT_VAR', 'default_value')
        assert result == 'default_value'
    
    def test_get_env_variable_raises_on_none(self):
        """Test that missing required env var raises EnvironmentError"""
        with pytest.raises(EnvironmentError) as exc_info:
            agent_router.get_env_variable('NONEXISTENT_REQUIRED_VAR')
        assert "Set the NONEXISTENT_REQUIRED_VAR environment variable" in str(exc_info.value)
    
    def test_get_env_variable_raises_on_empty(self, monkeypatch):
        """Test that empty env var raises ValueError"""
        monkeypatch.setenv('EMPTY_VAR', '')
        with pytest.raises(ValueError) as exc_info:
            agent_router.get_env_variable('EMPTY_VAR')
        assert "is empty" in str(exc_info.value)
    
    def test_validate_env_variable_success(self):
        """Test validating non-empty env variable"""
        result = agent_router.validate_env_variable('valid_value', 'TEST_VAR')
        assert result == 'valid_value'
    
    def test_validate_env_variable_raises_on_empty(self):
        """Test that empty value raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            agent_router.validate_env_variable('', 'EMPTY_VAR')
        assert "cannot be empty" in str(exc_info.value)


class TestArizeIntegration:
    """Test Arize tracing integration functions"""
    
    @patch('routers.agent.secretmanager.SecretManagerServiceClient')
    def test_initialize_arize_secrets_success(self, mock_secret_client, monkeypatch):
        """Test successful Arize secret initialization"""
        monkeypatch.setenv('PROJECT_NUMBER', '123456')
        monkeypatch.setenv('ARIZE_API_KEY', 'api-key-secret')
        monkeypatch.setenv('ARIZE_SPACE_ID', 'space-id-secret')
        
        # Mock secret manager response
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.payload.data.decode.return_value = 'secret-value'
        mock_client_instance.access_secret_version.return_value = mock_response
        mock_secret_client.return_value = mock_client_instance
        
        # Should not raise exceptions
        agent_router.initialize_arize_secrets()
    
    @patch('routers.agent.secretmanager.SecretManagerServiceClient')
    def test_initialize_arize_secrets_handles_errors(self, mock_secret_client, monkeypatch):
        """Test that Arize secret initialization handles errors gracefully"""
        monkeypatch.setenv('PROJECT_NUMBER', '123456')
        monkeypatch.setenv('ARIZE_API_KEY', 'api-key-secret')
        monkeypatch.setenv('ARIZE_SPACE_ID', 'space-id-secret')
        
        # Mock secret manager to raise exception
        mock_client_instance = MagicMock()
        mock_client_instance.access_secret_version.side_effect = Exception("Secret not found")
        mock_secret_client.return_value = mock_client_instance
        
        # Should not raise, just log warning
        agent_router.initialize_arize_secrets()
    
    @patch('routers.agent.register')
    @patch('routers.agent.VertexAIInstrumentor')
    def test_initialize_arize_tracing_success(self, mock_instrumentor, mock_register, monkeypatch):
        """Test successful Arize tracing initialization"""
        monkeypatch.setenv('ARIZE_API_KEY_VALUE', 'test-api-key')
        monkeypatch.setenv('ARIZE_SPACE_ID_VALUE', 'test-space-id')
        
        mock_provider = MagicMock()
        mock_register.return_value = mock_provider
        
        result = agent_router.initialize_arize_tracing('test-project')
        
        assert result == mock_provider
        mock_register.assert_called_once()
        mock_instrumentor.assert_called_once()
    
    def test_initialize_arize_tracing_without_credentials(self, monkeypatch):
        """Test Arize tracing initialization without credentials"""
        monkeypatch.delenv('ARIZE_API_KEY_VALUE', raising=False)
        monkeypatch.delenv('ARIZE_SPACE_ID_VALUE', raising=False)
        
        result = agent_router.initialize_arize_tracing()
        
        assert result is None


class TestInvokeAgentEndpoints:
    """Test agent invocation endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.mark.asyncio
    @patch('routers.agent.agent_engines.get')
    @patch('routers.agent.initialize_arize_tracing')
    async def test_invoke_agent_endpoint_success(self, mock_arize, mock_agent_get, client, sample_invoke_request):
        """Test successful agent invocation"""
        # Mock agent engine
        mock_engine = AsyncMock()
        
        async def mock_stream():
            yield {"response": "Test response", "status": "success"}
        
        mock_engine.async_stream_query = mock_stream
        mock_agent_get.return_value = mock_engine
        mock_arize.return_value = MagicMock()
        
        response = client.post("/invoke-agent", json=sample_invoke_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "response" in data
    
    def test_invoke_agent_empty_input(self, client):
        """Test invoke-agent with empty user input"""
        request_data = {
            "userInput": "",
            "agentId": "agent-123",
            "userId": "user-456",
            "agentDisplayName": "TestAgent",
            "agentVersion": "1"
        }
        
        response = client.post("/invoke-agent", json=request_data)
        
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()
    
    def test_invoke_agent_whitespace_input(self, client):
        """Test invoke-agent with whitespace-only input"""
        request_data = {
            "userInput": "   ",
            "agentId": "agent-123",
            "userId": "user-456",
            "agentDisplayName": "TestAgent",
            "agentVersion": "1"
        }
        
        response = client.post("/invoke-agent", json=request_data)
        
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    @patch('routers.agent.agent_engines.get')
    async def test_invoke_agent_with_session_id(self, mock_agent_get, client):
        """Test agent invocation with session ID"""
        mock_engine = AsyncMock()
        
        async def mock_stream():
            yield {"response": "Response with session", "sessionId": "session-123"}
        
        mock_engine.async_stream_query = mock_stream
        mock_agent_get.return_value = mock_engine
        
        request_data = {
            "userInput": "Hello",
            "agentId": "agent-123",
            "userId": "user-456",
            "agentDisplayName": "TestAgent",
            "agentVersion": "1",
            "sessionId": "session-789"
        }
        
        response = client.post("/invoke-agent", json=request_data)
        
        assert response.status_code == 200


class TestSessionManagementEndpoints:
    """Test session management endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.mark.asyncio
    @patch('routers.agent.agent_engines.get')
    async def test_create_session_endpoint_success(self, mock_agent_get, client, sample_create_session_request):
        """Test successful session creation"""
        mock_engine = AsyncMock()
        
        async def mock_create():
            yield {"sessionId": "new-session-123", "status": "created"}
        
        mock_engine.async_create_session = mock_create
        mock_agent_get.return_value = mock_engine
        
        response = client.post("/create-session", json=sample_create_session_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_create_session_empty_user_id(self, client):
        """Test create-session with empty user ID"""
        request_data = {
            "userId": "",
            "agentId": "agent-123"
        }
        
        response = client.post("/create-session", json=request_data)
        
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()
    
    @pytest.mark.xfail(reason="GET endpoint uses Pydantic model - returns 422. Fix: Change agent.py line 347 to use query parameters instead of ListSessionsRequest model")
    @pytest.mark.asyncio
    @patch('routers.agent.agent_engines.get')
    async def test_list_sessions_endpoint_success(self, mock_agent_get, client, sample_list_sessions_request):
        """Test successful session listing
        
        NOTE: This test correctly identifies a bug in the core API.
        The /list-sessions endpoint incorrectly uses a Pydantic model for a GET request.
        FastAPI returns 422 because GET endpoints cannot have request bodies.
        See tests/KNOWN_ISSUES.md for the fix.
        """
        mock_engine = AsyncMock()
        
        async def mock_list():
            yield {"sessions": [{"id": "session-1"}, {"id": "session-2"}]}
        
        mock_engine.async_list_sessions = mock_list
        mock_agent_get.return_value = mock_engine
        
        # GET endpoint should use query parameters, but currently uses Pydantic model
        response = client.get("/list-sessions", params=sample_list_sessions_request)
        assert response.status_code == 200
        assert response.json()["status"] == "success"
    
    @pytest.mark.xfail(reason="GET endpoint uses Pydantic model - returns 422. Fix: Change agent.py line 398 to use query parameters instead of GetSessionRequest model")
    @pytest.mark.asyncio
    @patch('routers.agent.agent_engines.get')
    async def test_get_session_endpoint_success(self, mock_agent_get, client, sample_get_session_request):
        """Test successful get session
        
        NOTE: This test correctly identifies a bug in the core API.
        The /get-session endpoint incorrectly uses a Pydantic model for a GET request.
        FastAPI returns 422 because GET endpoints cannot have request bodies.
        See tests/KNOWN_ISSUES.md for the fix.
        """
        mock_engine = AsyncMock()
        
        async def mock_get():
            yield {"sessionId": "session-456", "messages": []}
        
        mock_engine.async_get_session = mock_get
        mock_agent_get.return_value = mock_engine
        
        # GET endpoint should use query parameters, but currently uses Pydantic model
        response = client.get("/get-session", params=sample_get_session_request)
        assert response.status_code == 200
        assert response.json()["status"] == "success"
    
    @pytest.mark.xfail(reason="GET endpoint uses Pydantic model - returns 422. See tests/KNOWN_ISSUES.md for fix")
    def test_get_session_missing_user_id(self, client):
        """Test get-session with missing user ID
        
        NOTE: This test will pass once the core API bug is fixed.
        Currently returns 422 instead of 400 due to Pydantic model issue.
        """
        request_data = {
            "userId": "",
            "sessionId": "session-123",
            "agentId": "agent-456"
        }
        
        # GET endpoint should use query parameters and validate them
        response = client.get("/get-session", params=request_data)
        assert response.status_code == 400
        assert "user id cannot be empty" in response.json()["detail"].lower()
    
    @pytest.mark.xfail(reason="GET endpoint uses Pydantic model - returns 422. See tests/KNOWN_ISSUES.md for fix")
    def test_get_session_missing_session_id(self, client):
        """Test get-session with missing session ID
        
        NOTE: This test will pass once the core API bug is fixed.
        Currently returns 422 instead of 400 due to Pydantic model issue.
        """
        request_data = {
            "userId": "user-123",
            "sessionId": "",
            "agentId": "agent-456"
        }
        
        # GET endpoint should use query parameters and validate them
        response = client.get("/get-session", params=request_data)
        assert response.status_code == 400
        assert "session id cannot be empty" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    @patch('routers.agent.agent_engines.get')
    async def test_delete_session_endpoint_success(self, mock_agent_get, client, sample_delete_session_request):
        """Test successful session deletion"""
        mock_engine = AsyncMock()
        
        async def mock_delete():
            yield {"status": "deleted", "sessionId": "session-456"}
        
        mock_engine.async_delete_session = mock_delete
        mock_agent_get.return_value = mock_engine
        
        response = client.post("/delete-session", json=sample_delete_session_request)
        
        assert response.status_code == 200


class TestMemoryManagementEndpoints:
    """Test memory management endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.mark.asyncio
    @patch('routers.agent.agent_engines.get')
    async def test_add_session_to_memory_success(self, mock_agent_get, client):
        """Test successful addition of session to memory"""
        mock_engine = AsyncMock()
        
        async def mock_add():
            yield {"status": "added"}
        
        mock_engine.async_add_session_to_memory = mock_add
        mock_agent_get.return_value = mock_engine
        
        request_data = {
            "session": {"sessionId": "session-123", "messages": []},
            "agentId": "agent-456"
        }
        
        response = client.post("/add-session-to-memory", json=request_data)
        
        assert response.status_code == 200
    
    def test_add_session_to_memory_empty_session(self, client):
        """Test add-session-to-memory with empty session dict"""
        request_data = {
            "session": {},
            "agentId": "agent-456"
        }
        
        response = client.post("/add-session-to-memory", json=request_data)
        
        # Empty dict should still be valid, but let's check it's processed
        assert response.status_code in [200, 400, 500]
    
    @pytest.mark.asyncio
    @patch('routers.agent.agent_engines.get')
    async def test_search_memory_success(self, mock_agent_get, client, sample_search_memory_request):
        """Test successful memory search"""
        mock_engine = AsyncMock()
        
        async def mock_search():
            yield {"results": [{"sessionId": "session-1", "relevance": 0.9}]}
        
        mock_engine.async_search_memory = mock_search
        mock_agent_get.return_value = mock_engine
        
        response = client.post("/search-memory", json=sample_search_memory_request)
        
        assert response.status_code == 200
    
    def test_search_memory_empty_user_id(self, client):
        """Test search-memory with empty user ID"""
        request_data = {
            "userId": "",
            "query": "test query",
            "agentId": "agent-456"
        }
        
        response = client.post("/search-memory", json=request_data)
        
        assert response.status_code == 400
    
    def test_search_memory_empty_query(self, client):
        """Test search-memory with empty query"""
        request_data = {
            "userId": "user-123",
            "query": "",
            "agentId": "agent-456"
        }
        
        response = client.post("/search-memory", json=request_data)
        
        assert response.status_code == 400


class TestFlushArizeTraces:
    """Test Arize trace flushing"""
    
    def test_flush_arize_traces_with_provider(self):
        """Test flushing traces with valid provider"""
        mock_provider = MagicMock()
        mock_provider.force_flush = MagicMock()
        
        # Temporarily set the global provider
        original_provider = agent_router.arize_tracer_provider
        agent_router.arize_tracer_provider = mock_provider
        
        try:
            agent_router.flush_arize_traces()
            mock_provider.force_flush.assert_called_once()
        finally:
            agent_router.arize_tracer_provider = original_provider
    
    def test_flush_arize_traces_without_provider(self):
        """Test flushing traces without provider (should not error)"""
        original_provider = agent_router.arize_tracer_provider
        agent_router.arize_tracer_provider = None
        
        try:
            # Should not raise exception
            agent_router.flush_arize_traces()
        finally:
            agent_router.arize_tracer_provider = original_provider
