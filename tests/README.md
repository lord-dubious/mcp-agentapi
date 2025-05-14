# MCP Server for Agent API Tests

This directory contains tests for the MCP server for Agent API.

## Test Structure

The tests are organized by module:

- `test_config.py`: Tests for the configuration management functionality
- `test_api_client.py`: Tests for the Agent API client
- `test_agent_manager.py`: Tests for the agent detection, installation, and lifecycle management
- `test_resource_manager.py`: Tests for the resource management functionality
- `test_health_check.py`: Tests for the health check functionality
- `test_server.py`: Tests for the MCP server functionality
- `test_models.py`: Tests for the data models
- `test_exceptions.py`: Tests for the custom exceptions
- `test_integration.py`: Integration tests for the MCP server using MCP SDK's testing utilities

## Running Tests

You can run the tests using the `run_tests.py` script in the project root:

```bash
# Run all tests
./run_tests.py

# Run tests in verbose mode
./run_tests.py -v

# Run tests with coverage report
./run_tests.py -c

# Run only unit tests
./run_tests.py --unit

# Run only integration tests
./run_tests.py --integration

# Run a specific test module
./run_tests.py tests/test_config.py
```

Alternatively, you can run the tests directly with pytest:

```bash
# Run all tests
python -m pytest

# Run tests in verbose mode
python -m pytest -v

# Run tests with coverage report
python -m pytest --cov=src --cov-report=term --cov-report=html

# Run only unit tests
python -m pytest -m unit

# Run only integration tests
python -m pytest -m integration

# Run a specific test module
python -m pytest tests/test_config.py
```

## Test Markers

The tests are marked with the following markers:

- `unit`: Unit tests that don't require external dependencies
- `integration`: Integration tests that require external dependencies
- `slow`: Tests that take a long time to run

You can run tests with specific markers using the `-m` option:

```bash
# Run only unit tests
python -m pytest -m unit

# Run only integration tests
python -m pytest -m integration

# Run all tests except slow tests
python -m pytest -m "not slow"
```

## Test Fixtures

Common test fixtures are defined in `conftest.py`. These include:

- `config`: A test configuration
- `http_client`: A mock HTTP client
- `resource_manager`: A test resource manager
- `agent_manager`: A test agent manager
- `health_check`: A test health check
- `app_context`: A test application context
- `mock_http_response`: A mock HTTP response
- `mock_process`: A mock subprocess.Popen instance
- `mock_task`: A mock asyncio.Task instance

## Writing Tests

When writing tests, follow these guidelines:

1. Use the appropriate test markers (`unit`, `integration`, `slow`)
2. Use the provided fixtures when possible
3. Mock external dependencies
4. Test both success and error cases
5. Test edge cases and boundary conditions
6. Keep tests independent and isolated
7. Use descriptive test names that explain what is being tested

For example:

```python
@pytest.mark.unit
def test_config_validation_success(config):
    """Test successful configuration validation."""
    # Test code here

@pytest.mark.unit
def test_config_validation_error(config):
    """Test configuration validation with errors."""
    # Test code here
```
