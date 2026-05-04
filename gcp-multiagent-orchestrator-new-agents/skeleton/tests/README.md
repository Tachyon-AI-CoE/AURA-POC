# Test Suite for GCP Multi-Agent Orchestrator

This directory contains comprehensive unit tests for the GCP Multi-Agent Orchestrator project.

## Overview

The test suite provides thorough coverage of all core modules with proper mocking of external dependencies (Google Cloud, VertexAI, etc.). **No changes are made to core source files** - all tests are isolated and self-contained.

## Structure

```
tests/
├── __init__.py                          # Test package initialization
├── conftest.py                          # Shared fixtures and mocks
├── pytest.ini                           # Pytest configuration
├── requirements-test.txt                # Test dependencies
├── test_log_helper.py                   # Tests for logging utilities
├── test_config_reader.py                # Tests for configuration reader
├── test_agent_config_generator.py       # Tests for agent config generation
└── README.md                            # This file
```

## Installation

Install test dependencies:

```bash
pip install -r tests/requirements-test.txt
```

## Running Tests

### Run all tests:
```bash
pytest tests/
```

### Run with coverage:
```bash
pytest tests/ --cov=src --cov-report=html
```

### Run specific test file:
```bash
pytest tests/test_log_helper.py -v
```

### Run specific test class:
```bash
pytest tests/test_config_reader.py::TestConfigReader -v
```

### Run specific test method:
```bash
pytest tests/test_log_helper.py::TestLogHelper::test_setup_logging_default_level -v
```

### Run with markers:
```bash
pytest tests/ -m unit         # Run only unit tests
pytest tests/ -m "not slow"   # Skip slow tests
```

## Test Coverage

The test suite covers:

### 1. **utils/log_helper.py**
- Logging setup and configuration
- Log level handling (INFO, DEBUG, ERROR, WARNING)
- UTC timestamp formatting
- Handler creation and management
- Environment variable integration

### 2. **config/config_reader.py**
- JSON and YAML file loading
- Configuration value retrieval
- Error handling (FileNotFoundError, JSONDecodeError, YAMLError)
- Default value handling
- Nested structure support
- Class-level state management

### 3. **config/agent_config_generator.py**
- Agent configuration loading from JSON
- Root agent configuration loading from YAML
- RAG configuration transformation
- MCP configuration transformation
- Tools configuration merging
- Agent configuration merging
- Complete config generation workflow

## Fixtures

The test suite provides several shared fixtures in `conftest.py`:

- **`mock_env_vars`**: Mock environment variables for testing
- **`sample_root_agent_config`**: Sample root agent configuration data
- **`sample_agents_json`**: Sample agents JSON data
- **`mock_config_file`**: Temporary config file for testing
- **`mock_agents_json_file`**: Temporary agents JSON file for testing
- **`reset_config_reader`**: Auto-reset ConfigReader state between tests
- **`mock_vertexai`**: Mock VertexAI client
- **`mock_storage_client`**: Mock Google Cloud Storage client
- **`mock_llm_agent`**: Mock LlmAgent

## Mocking Strategy

All external dependencies are properly mocked in `conftest.py`:

- **Google Cloud Services**: `google.cloud`, `google.cloud.storage`
- **VertexAI**: `vertexai`, `vertexai.agent_engines`
- **Google ADK**: `google.adk.agents`, `google.adk.tools`, `google.adk.models`
- **Authentication**: `google.auth`, `google.oauth2`
- **Observability**: `arize_otel`, `openinference`

This ensures tests run without requiring actual GCP credentials or internet connectivity.

## Configuration Files

### pytest.ini
Configures pytest behavior:
- Test discovery patterns
- Coverage options
- Test markers
- Warning filters

### .coveragerc
Configures coverage reporting:
- Source directories
- Files to omit
- Report precision
- HTML report directory

## Best Practices

1. **Isolation**: Each test is independent and doesn't affect others
2. **Mocking**: All external dependencies are mocked
3. **No Side Effects**: Tests don't modify core source files
4. **Clear Naming**: Test names clearly describe what they test
5. **Comprehensive**: Tests cover both success and failure scenarios
6. **Fast**: Tests run quickly without external dependencies

## Writing New Tests

When adding new tests:

1. Create a new test file with prefix `test_`
2. Use existing fixtures from `conftest.py`
3. Mock external dependencies properly
4. Follow the naming convention: `test_<functionality>_<scenario>`
5. Add docstrings explaining what the test validates
6. Group related tests in test classes

Example:

```python
class TestNewModule:
    """Test suite for new module."""
    
    def test_function_success(self, mock_env_vars):
        """Test that function works with valid input."""
        from module import function
        
        result = function("valid_input")
        
        assert result == "expected_output"
    
    def test_function_failure(self):
        """Test that function raises error with invalid input."""
        from module import function
        
        with pytest.raises(ValueError):
            function("invalid_input")
```

## Continuous Integration

The test suite is designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install -r tests/requirements-test.txt
    pytest tests/ --cov=src --cov-report=xml
```

## Troubleshooting

### Import Errors
If you see import errors, ensure the `src` directory is in the Python path:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
```

### Mock Issues
If mocks aren't working, check that they're defined in `conftest.py` before any imports that use them.

### Coverage Not Working
Ensure `.coveragerc` is in the project root and pytest-cov is installed.

## Contributing

When contributing tests:
1. Follow existing patterns and conventions
2. Ensure all tests pass before submitting
3. Maintain or improve code coverage
4. Add documentation for new test fixtures
5. Never modify core source files

## License

Same as parent project.
