# GCP Agent API - Test Suite

## Overview

Comprehensive unit test suite for the GCP Agent API FastAPI application. Tests cover all major components including API endpoints, agent invocation, session management, memory operations, and utility functions.

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Shared fixtures and configuration
├── pytest.ini                  # Pytest configuration
├── requirements-test.txt       # Test dependencies
├── test_main_fastapi.py        # FastAPI app tests (14 tests)
├── test_agent_router.py        # Agent router tests (30+ tests)
└── test_log_helper.py          # Logging utility tests (13 tests)
```

## Test Coverage

### test_main_fastapi.py (14 tests)
- ✅ FastAPI app initialization
- ✅ Health check endpoint
- ✅ Root endpoint with API info
- ✅ CORS middleware configuration
- ✅ OpenAPI documentation
- ✅ Swagger UI and ReDoc
- ✅ Router inclusion
- ✅ Error handling (404s)

### test_agent_router.py (30+ tests)
**Helper Functions (6 tests)**
- ✅ Environment variable retrieval
- ✅ Environment variable validation
- ✅ Default values and error handling

**Arize Integration (4 tests)**
- ✅ Secret Manager integration
- ✅ Tracing initialization
- ✅ Error handling for missing credentials
- ✅ Trace flushing

**Agent Invocation (5 tests)**
- ✅ Successful agent invocation
- ✅ Empty input validation
- ✅ Whitespace input handling
- ✅ Session ID support
- ✅ Error responses

**Session Management (7 tests)**
- ✅ Create session
- ✅ List sessions
- ✅ Get session
- ✅ Delete session
- ✅ Input validation for all operations

**Memory Management (5 tests)**
- ✅ Add session to memory
- ✅ Search memory
- ✅ Input validation
- ✅ Empty query handling

### test_log_helper.py (13 tests)
- ✅ Default log level (INFO)
- ✅ Custom log levels (DEBUG, WARNING, ERROR)
- ✅ Logger instance creation
- ✅ Log format configuration
- ✅ Message logging capability
- ✅ Multiple calls behavior
- ✅ Invalid level handling
- ✅ Environment variable integration

## Running Tests

### Prerequisites

```cmd
# Install test dependencies
pip install -r tests/requirements-test.txt
```

### Run All Tests

```cmd
cd C:\Users\2406556\OneDrive - Cognizant\Desktop\scaffolder-templates\gcp\gcp-agent-api\skeleton
python -m pytest tests/ -v
```

### Run Specific Test Files

```cmd
# Test FastAPI app
python -m pytest tests/test_main_fastapi.py -v

# Test agent router
python -m pytest tests/test_agent_router.py -v

# Test log helper
python -m pytest tests/test_log_helper.py -v
```

### Run Specific Test Classes

```cmd
python -m pytest tests/test_agent_router.py::TestInvokeAgentEndpoints -v
python -m pytest tests/test_agent_router.py::TestSessionManagementEndpoints -v
python -m pytest tests/test_agent_router.py::TestMemoryManagementEndpoints -v
```

### Run with Coverage

```cmd
python -m pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
```

## Test Features

### Environment Variable Mocking
All tests properly mock required environment variables:
- `PROJECT_ID`
- `LOCATION`
- `PROJECT_NUMBER`
- `ARIZE_API_KEY`
- `ARIZE_SPACE_ID`
- `LOG_LEVEL`

### External Dependency Mocking
Tests mock external dependencies to avoid real API calls:
- ✅ Vertex AI SDK (`vertexai`, `vertexai.agent_engines`)
- ✅ Arize Phoenix (`arize.otel`)
- ✅ OpenTelemetry (`opentelemetry`)
- ✅ Google Cloud Secret Manager (`google.cloud.secretmanager`)

### Async Testing
Proper async/await support using `pytest-asyncio`:
- ✅ Async agent invocation
- ✅ Async session operations
- ✅ Async memory operations

### FastAPI TestClient
Uses FastAPI's `TestClient` for realistic endpoint testing:
- ✅ HTTP request simulation
- ✅ JSON payload validation
- ✅ Response status checking
- ✅ Error handling verification

## Fixtures

### Shared Fixtures (conftest.py)

**Environment Fixtures:**
- `mock_env_vars` - Mock all environment variables

**Request Fixtures:**
- `sample_invoke_request` - Agent invocation payload
- `sample_create_session_request` - Session creation payload
- `sample_list_sessions_request` - List sessions payload
- `sample_get_session_request` - Get session payload
- `sample_delete_session_request` - Delete session payload
- `sample_search_memory_request` - Search memory payload

**Mock Fixtures:**
- `mock_agent_response` - Successful agent response
- `mock_vertexai` - Mock Vertex AI module
- `mock_arize_modules` - Mock Arize modules
- `mock_secret_manager` - Mock Secret Manager
- `async_mock_agent_engine` - Async agent engine mock

## Test Patterns

### Module-Level Imports
Tests use module-level imports after environment variable setup:

```python
# Set environment variables FIRST
os.environ.setdefault('PROJECT_ID', 'test-project')
os.environ.setdefault('LOCATION', 'us-central1')

# Mock external dependencies
sys.modules['vertexai'] = MagicMock()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import modules (after env vars and mocks)
from routers import agent as agent_router
```

### Async Test Pattern
```python
@pytest.mark.asyncio
@patch('routers.agent.agent_engines.get')
async def test_async_operation(mock_agent_get):
    mock_engine = AsyncMock()
    
    async def mock_stream():
        yield {"response": "test"}
    
    mock_engine.async_stream_query = mock_stream
    mock_agent_get.return_value = mock_engine
    
    # Test async operation
    result = await invoke_agent(...)
    assert result is not None
```

### Endpoint Test Pattern
```python
def test_endpoint(client):
    request_data = {
        "userInput": "test query",
        "agentId": "agent-123"
    }
    
    response = client.post("/invoke-agent", json=request_data)
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
```

## Expected Results

```
tests/test_main_fastapi.py::TestMainFastAPI - 14 tests PASSED
tests/test_agent_router.py::TestAgentRouterHelpers - 6 tests PASSED
tests/test_agent_router.py::TestArizeIntegration - 4 tests PASSED
tests/test_agent_router.py::TestInvokeAgentEndpoints - 5 tests PASSED
tests/test_agent_router.py::TestSessionManagementEndpoints - 7 tests PASSED
tests/test_agent_router.py::TestMemoryManagementEndpoints - 5 tests PASSED
tests/test_agent_router.py::TestFlushArizeTraces - 2 tests PASSED
tests/test_log_helper.py::TestLogHelper - 13 tests PASSED

Total: 56+ tests PASSED ✅
```

## Troubleshooting

### Import Errors
If you see import errors, ensure:
1. Environment variables are set before imports
2. External modules are mocked before imports
3. `src/` is added to `sys.path`

### Async Test Failures
If async tests fail:
1. Ensure `pytest-asyncio` is installed
2. Use `@pytest.mark.asyncio` decorator
3. Use `AsyncMock` for async functions
4. Check `asyncio_mode = auto` in pytest.ini

### Missing Dependencies
```cmd
pip install -r tests/requirements-test.txt
```

## Contributing

When adding new tests:
1. ✅ Follow existing test patterns
2. ✅ Use descriptive test names
3. ✅ Mock external dependencies
4. ✅ Add fixtures to conftest.py for reuse
5. ✅ Document complex test scenarios
6. ✅ Ensure tests are isolated and idempotent

## CI/CD Integration

Tests can be integrated into CI/CD pipelines:

```yaml
# Example cloudbuild.yaml step
- name: 'python:3.11'
  entrypoint: 'sh'
  args:
    - '-c'
    - |
      pip install -r tests/requirements-test.txt
      pytest tests/ -v --junitxml=test-results.xml
```

## Status

✅ **All tests passing**  
✅ **56+ tests implemented**  
✅ **Comprehensive coverage**  
✅ **Ready for production use**

## Contact

For questions or issues with tests, please refer to the main project documentation or contact the development team.
