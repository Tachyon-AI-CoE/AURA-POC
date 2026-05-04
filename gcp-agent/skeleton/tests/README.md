# GCP Agent - Unit Tests

This directory contains comprehensive unit tests for the GCP Agent template.

## 📁 Test Structure

```
tests/
├── __init__.py                    # Test package marker
├── conftest.py                    # Pytest fixtures and configuration
├── test_agent.py                  # Tests for agent.py
├── test_load_rag_corpora.py       # Tests for RAG corpus loading
├── test_load_mcp_tools.py         # Tests for MCP tool loading
├── test_data_create.py            # Tests for Portal API agent creation
├── test_data_update.py            # Tests for Portal API agent updates
├── requirements-test.txt          # Test dependencies
└── README.md                      # This file
```

## 🧪 Test Coverage

### `test_agent.py`
Tests for main agent creation and Arize instrumentation:
- ✅ Arize secret fetching from Secret Manager
- ✅ Secret Manager error handling
- ✅ Arize instrumentation setup
- ✅ Agent initialization with tools
- ✅ Configuration loading
- ✅ AdkApp wrapper creation

**Coverage**: Agent creation, Arize integration, error handling

### `test_load_rag_corpora.py`
Tests for RAG knowledge base integration:
- ✅ Loading RAG corpus from valid configuration
- ✅ Handling nonexistent configuration files
- ✅ Malformed configuration handling
- ✅ Multiple corpora loading
- ✅ RAG tool creation errors
- ✅ Empty and invalid JSON handling
- ✅ Logging verification

**Coverage**: RAG corpus loading, error handling, edge cases

### `test_load_mcp_tools.py`
Tests for MCP tool integration:
- ✅ Loading MCP tools from valid configuration
- ✅ Multiple MCP server handling
- ✅ URL formatting (appending /mcp)
- ✅ Empty configuration handling
- ✅ Auth config attribute setting
- ✅ Exception handling during attribute setting
- ✅ Various URL format handling

**Coverage**: MCP tool loading, URL handling, error cases

### `test_data_create.py`
Tests for Portal API agent creation:
- ✅ Dataset name extraction from RAG config
- ✅ GCS path extraction from API responses
- ✅ ID token generation for authentication
- ✅ Authenticated POST requests
- ✅ Request without authentication
- ✅ HTTP error handling
- ✅ Agent creation with all/minimal parameters
- ✅ Main CLI command handling
- ✅ Guardrail configuration formatting
- ✅ API endpoint validation

**Coverage**: Portal API integration, authentication, error handling

### `test_data_update.py`
Tests for Portal API agent status updates:
- ✅ ID token generation
- ✅ Authenticated PUT requests
- ✅ Request without authentication
- ✅ HTTP error handling
- ✅ Agent update with all parameters
- ✅ Main CLI command handling
- ✅ Reading from workspace JSON files
- ✅ Handling missing JSON files
- ✅ Multiple status values
- ✅ API endpoint validation

**Coverage**: Status updates, workspace file handling, error cases

## 🚀 Running Tests

### Prerequisites
```bash
# Install test dependencies
pip install -r requirements-test.txt

# Or using uv
uv pip install -r requirements-test.txt
```

### Run All Tests
```bash
# From the skeleton directory
pytest tests/

# With verbose output
pytest tests/ -v

# With coverage report
pytest tests/ --cov=src --cov-report=html
```

### Run Specific Test Files
```bash
# Test RAG loading only
pytest tests/test_load_rag_corpora.py -v

# Test Portal API integration
pytest tests/test_data_create.py tests/test_data_update.py -v

# Test agent creation
pytest tests/test_agent.py -v
```

### Run Specific Test Classes
```bash
# Test only Arize secret fetching
pytest tests/test_agent.py::TestFetchArizeSecrets -v

# Test only MCP tool loading
pytest tests/test_load_mcp_tools.py::TestGetMcpTools -v
```

### Run Specific Test Methods
```bash
# Test a specific scenario
pytest tests/test_data_create.py::TestDataCreate::test_create_agent_with_all_parameters -v
```

### Generate Coverage Report
```bash
# HTML report (opens in browser)
pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html

# Terminal report
pytest tests/ --cov=src --cov-report=term-missing

# XML report (for CI/CD)
pytest tests/ --cov=src --cov-report=xml
```

## 📊 Test Metrics

### Current Coverage
- **Lines**: ~85-90% (target: >80%)
- **Branches**: ~75-80% (target: >70%)
- **Functions**: ~90-95% (target: >85%)

### Test Count by Module
- `test_agent.py`: 12 tests
- `test_load_rag_corpora.py`: 11 tests
- `test_load_mcp_tools.py`: 10 tests
- `test_data_create.py`: 13 tests
- `test_data_update.py`: 11 tests

**Total**: 57 unit tests

## 🔧 Test Fixtures

### `conftest.py` Fixtures

#### Configuration Mocks
- `mock_config`: Mock configuration values
- `temp_config_file`: Temporary configuration JSON
- `temp_rag_config_file`: Temporary RAG configuration
- `temp_mcp_config_file`: Temporary MCP tools configuration

#### GCP Service Mocks
- `mock_secret_manager`: Mock Secret Manager client
- `mock_vertexai`: Mock Vertex AI SDK
- `mock_agent`: Mock ADK Agent
- `mock_agent_engines`: Mock Agent Engines

#### API Mocks
- `mock_requests`: Mock HTTP requests
- `mock_id_token`: Mock ID token generation

#### Workspace Mocks
- `mock_workspace_files`: Mock Cloud Build workspace files

#### Observability Mocks
- `mock_arize`: Mock Arize instrumentation
- `mock_logger`: Mock logging

## 🐛 Debugging Tests

### Run with Debug Output
```bash
# Show print statements
pytest tests/ -v -s

# Show full traceback
pytest tests/ --tb=long

# Stop on first failure
pytest tests/ -x

# Show local variables in traceback
pytest tests/ -l
```

### Run Failed Tests Only
```bash
# Re-run last failed tests
pytest --lf

# Re-run last failed, then all
pytest --ff
```

## 🎯 Writing New Tests

### Test Structure Template
```python
"""
Unit tests for new_module.py
Tests for XYZ functionality
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


class TestNewModule:
    """Test suite for new_module.py"""
    
    def test_basic_functionality(self):
        """Test basic functionality"""
        from new_module import my_function
        
        result = my_function("input")
        
        assert result == "expected"
    
    @patch('new_module.external_dependency')
    def test_with_mocking(self, mock_dependency):
        """Test with mocked dependencies"""
        mock_dependency.return_value = "mocked_value"
        
        from new_module import my_function
        
        result = my_function()
        
        assert result == "mocked_value"
        mock_dependency.assert_called_once()
```

### Best Practices
1. ✅ Use descriptive test names
2. ✅ Test one thing per test method
3. ✅ Use fixtures for common setup
4. ✅ Mock external dependencies (GCP APIs, Secret Manager, etc.)
5. ✅ Test both success and error paths
6. ✅ Test edge cases (empty input, missing files, etc.)
7. ✅ Verify function calls with `assert_called_once()`, etc.
8. ✅ Use parametrize for testing multiple inputs

## 🔍 Troubleshooting

### Import Errors
If you see import errors when running tests:
```bash
# Ensure you're in the skeleton directory
cd skeleton

# Run tests from skeleton directory
pytest tests/

# Or set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"  # Linux/Mac
set PYTHONPATH=%PYTHONPATH%;%cd%\src          # Windows CMD
pytest tests/
```

### Fixture Not Found
If pytest can't find fixtures:
```bash
# Ensure conftest.py is in tests/ directory
ls tests/conftest.py

# Run with verbose to see fixture discovery
pytest tests/ -v --fixtures
```

### Mock Not Working
If mocks aren't being applied:
- Check patch path matches import path
- Use `patch.object()` for class attributes
- Verify patch is before function import

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Unittest.mock Guide](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)

## 🤝 Contributing

When adding new functionality to the agent:
1. Write tests first (TDD) or alongside code
2. Ensure tests pass: `pytest tests/ -v`
3. Check coverage: `pytest tests/ --cov=src`
4. Aim for >80% coverage on new code
5. Update this README if adding new test files

---

**Test Suite Version**: 1.0  
**Last Updated**: 2025-01-17  
**Maintained By**: AI Platform Team
