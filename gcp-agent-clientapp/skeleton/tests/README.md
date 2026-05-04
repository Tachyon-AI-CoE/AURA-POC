# GCP Agent ClientApp - Test Suite

## Overview
Comprehensive test suite for the GCP Agent ClientApp project with 40 unit tests covering all core functionality.

## Test Structure

```
tests/
├── __init__.py              # Package marker
├── conftest.py              # Shared fixtures and configuration
├── pytest.ini               # Pytest configuration
├── requirements-test.txt    # Test dependencies
├── test_log_helper.py       # Logging utility tests (9 tests)
├── test_config_reader.py    # Configuration reader tests (16 tests)
└── test_agent_client.py     # Agent client tests (15 tests)
```

## Quick Start

### Install Test Dependencies
```cmd
cd c:\Users\2406556\OneDrive - Cognizant\Desktop\scaffolder-templates\gcp\gcp-agent-clientapp\skeleton\tests
pip install -r requirements-test.txt
```

### Run All Tests
```cmd
python -m pytest . -v
```

### Run Specific Test File
```cmd
python -m pytest test_agent_client.py -v
python -m pytest test_config_reader.py -v
python -m pytest test_log_helper.py -v
```

### Run with Coverage
```cmd
python -m pytest . --cov=../src --cov-report=html
```

## Test Coverage

### 1. Log Helper Tests (9 tests)
**File**: `test_log_helper.py`

Tests the logging utility module (`utils/log_helper.py`):
- ✅ Default log level (INFO)
- ✅ Custom log levels (DEBUG, WARNING, ERROR)
- ✅ Logger instance creation
- ✅ Log format configuration
- ✅ Environment variable handling
- ✅ Message logging capabilities
- ✅ load_dotenv() integration

### 2. Config Reader Tests (16 tests)
**File**: `test_config_reader.py`

Tests the configuration reader (`config/config_reader.py`):
- ✅ JSON file loading
- ✅ YAML file loading
- ✅ Get value for existing keys
- ✅ Get value for missing keys (returns None)
- ✅ Default values for missing keys
- ✅ Error handling (FileNotFoundError, JSONDecodeError, YAMLError)
- ✅ RuntimeError when not initialized
- ✅ File extension detection
- ✅ Multiple data types (string, int, float, bool, list, dict)
- ✅ Empty files
- ✅ Edge cases (empty string, zero values)

### 3. Agent Client Tests (15 tests)
**File**: `test_agent_client.py`

Tests the agent invocation module (`agent_client.py`):
- ✅ AsyncStreamQueryable with summary response
- ✅ AsyncStreamQueryable with output response
- ✅ AsyncStreamQueryable with response field
- ✅ AsyncStreamQueryable with content/parts structure
- ✅ Sync Queryable with summary
- ✅ Sync Queryable with output
- ✅ Sync Queryable with response
- ✅ Sync Queryable with content/parts
- ✅ Custom user_id and session_id
- ✅ Default user_id behavior
- ✅ AsyncQueryable engine support
- ✅ AsyncAdkApp engine support
- ✅ Error handling for incorrect response format
- ✅ Error handling for non-queryable engines
- ✅ Parameter passing validation

## Test Features

### Proper Mocking
- ✅ All external dependencies mocked (Vertex AI, Streamlit)
- ✅ Environment variables isolated
- ✅ No network calls or real API interactions
- ✅ File system operations use temporary directories

### Best Practices
- ✅ Module-level imports with path setup
- ✅ Comprehensive fixtures in conftest.py
- ✅ Clear test class organization
- ✅ Descriptive test names and docstrings
- ✅ Async test support with pytest-asyncio
- ✅ Type ignore comments for IDE compatibility

### Test Isolation
- ✅ Each test is independent
- ✅ Mocks properly reset between tests
- ✅ Temporary files cleaned up automatically
- ✅ No shared state between tests

## Fixtures

### Environment Fixtures
- `mock_env_vars` - Mock all environment variables
- `mock_vertexai_init` - Mock vertexai initialization
- `mock_agent_engines_get` - Mock agent_engines.get()

### Configuration Fixtures
- `mock_config_file` - Create temporary JSON config file
- `mock_yaml_config_file` - Create temporary YAML config file

### Agent Response Fixtures
- `sample_agent_response` - Response with summary
- `sample_agent_response_output` - Response with output
- `sample_agent_response_content` - Response with content/parts
- `sample_agent_response_plain` - Response with response field
- `mock_async_agent_engine` - Mock async agent engine
- `mock_sync_agent_engine` - Mock sync agent engine

## Running Tests in Different Modes

### Verbose Mode
```cmd
python -m pytest . -v
```

### Show Print Statements
```cmd
python -m pytest . -v -s
```

### Run Only Async Tests
```cmd
python -m pytest . -v -m asyncio
```

### Run Specific Test Class
```cmd
python -m pytest test_agent_client.py::TestInvokeAgent -v
```

### Run Specific Test Method
```cmd
python -m pytest test_agent_client.py::TestInvokeAgent::test_invoke_agent_with_async_stream_summary -v
```

### Stop on First Failure
```cmd
python -m pytest . -v -x
```

### Run Last Failed Tests
```cmd
python -m pytest . --lf
```

## Expected Output

```
======================= test session starts ========================
collected 40 items

test_agent_client.py::TestInvokeAgent::test_invoke_agent_with_async_stream_summary PASSED [ 2%]
test_agent_client.py::TestInvokeAgent::test_invoke_agent_with_async_stream_output PASSED [ 5%]
...
test_config_reader.py::TestConfigReader::test_load_json_configuration PASSED [67%]
test_config_reader.py::TestConfigReader::test_load_yaml_configuration PASSED [70%]
...
test_log_helper.py::TestLogHelper::test_setup_logging_default_level PASSED [92%]
test_log_helper.py::TestLogHelper::test_setup_logging_debug_level PASSED [95%]
...

===================== 40 passed in X.XXs =======================
```

## Troubleshooting

### Import Errors
If you see import errors, make sure:
1. You're running from the `tests/` directory
2. `sys.path` setup is working in conftest.py
3. All required dependencies are installed

### Yellow Underlines in IDE
The `# type: ignore[import-not-found]` comments suppress IDE warnings for dynamic imports. Tests run correctly despite these warnings.

### Async Test Issues
Make sure `pytest-asyncio` is installed:
```cmd
pip install pytest-asyncio
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Run Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r tests/requirements-test.txt
      - name: Run tests
        run: |
          cd tests
          pytest . -v --cov=../src
```

## Coverage Report

To generate an HTML coverage report:
```cmd
python -m pytest . --cov=../src --cov-report=html
```

Open `htmlcov/index.html` in your browser to view detailed coverage.

## Maintenance

### Adding New Tests
1. Create test methods in appropriate test class
2. Use existing fixtures from conftest.py
3. Follow naming convention: `test_<feature>_<scenario>`
4. Add docstrings explaining the test

### Adding New Fixtures
Add to `conftest.py`:
```python
@pytest.fixture
def my_new_fixture():
    """Description"""
    return {"data": "value"}
```

## Test Statistics

| Category | Count |
|----------|-------|
| Total Tests | 40 |
| Log Helper Tests | 9 |
| Config Reader Tests | 16 |
| Agent Client Tests | 15 |
| Async Tests | 15 |
| Sync Tests | 25 |

## Success Criteria

✅ All tests pass  
✅ No external dependencies called  
✅ Comprehensive error handling coverage  
✅ Both success and failure paths tested  
✅ Edge cases covered  
✅ Clear documentation  

---

**Last Updated**: March 9, 2026  
**Test Suite Version**: 1.0  
**Status**: Production Ready
