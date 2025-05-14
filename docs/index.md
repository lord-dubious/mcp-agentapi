# MCP Server for Agent API Documentation

Welcome to the documentation for the MCP Server for Agent API. This documentation provides detailed information about the MCP server, its components, and how to use it.

## Overview

The MCP Server for Agent API is a bridge between the Agent API and the Machine Coding Protocol (MCP). It allows MCP clients to interact with various AI coding agents through a standardized interface.

## Components

The MCP server consists of several components:

- [Configuration](config.md): Loading, validating, and managing configuration settings
- [Agent Manager](agent_manager.md): Detecting, installing, starting, stopping, and monitoring agents
- [API Client](api_client.md): Making requests to the Agent API
- [Resource Manager](resource_manager.md): Tracking and cleaning up resources
- [Health Check](health_check.md): Monitoring the health of the MCP server and its components
- [MCP Tools](mcp_tools.md): Tools for interacting with agents through the MCP

## Getting Started

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/mcp-agentapi.git
cd mcp-agentapi

# Install dependencies
pip install -r requirements.txt
```

### Running the MCP Server

```bash
# Run with default settings
python mcp_server.py

# Run with custom configuration
python mcp_server.py --config path/to/config.json

# Run with specific agent type
python mcp_server.py --agent-type goose

# Run with SSE transport
python mcp_server.py --transport sse --host 0.0.0.0 --port 8080
```

### Configuration

The MCP server can be configured using environment variables, a configuration file, or command-line arguments. See the [Configuration](config.md) documentation for details.

## Usage Examples

### Agent Management

```python
from mcp.client import MCPClient

# Connect to the MCP server
client = MCPClient("http://localhost:8080")

# List available agents
agents = client.call("list_available_agents")
print(f"Available agents: {agents}")

# Start an agent
result = client.call("start_agent", {"agent_type": "goose"})
print(f"Agent started: {result}")
```

### Agent API Interaction

```python
# Send a message to the agent
result = client.call("send_message", {"content": "Hello, agent!", "type": "user"})
print(f"Message sent: {result}")

# Get messages
messages = client.call("get_messages")
print(f"Messages: {messages}")
```

## Development

### Project Structure

```
mcp-agentapi/
├── mcp_server.py          # Main entry point
├── server_new.py          # MCP server implementation
├── src/
│   ├── __init__.py
│   ├── agent_manager.py   # Agent detection, installation, and lifecycle management
│   ├── api_client.py      # Agent API client
│   ├── config.py          # Configuration management
│   ├── constants.py       # Constants and defaults
│   ├── context.py         # Application context
│   ├── exceptions.py      # Custom exceptions
│   ├── health_check.py    # Health monitoring
│   ├── models.py          # Data models
│   └── resource_manager.py # Resource management
├── tests/                 # Test suite
│   ├── conftest.py        # Test fixtures
│   ├── test_agent_manager.py
│   ├── test_api_client.py
│   ├── test_config.py
│   ├── test_exceptions.py
│   ├── test_health_check.py
│   ├── test_models.py
│   ├── test_resource_manager.py
│   └── test_server.py
├── docs/                  # Documentation
│   ├── index.md           # This file
│   ├── config.md          # Configuration documentation
│   ├── agent_manager.md   # Agent Manager documentation
│   ├── api_client.md      # API Client documentation
│   ├── resource_manager.md # Resource Manager documentation
│   ├── health_check.md    # Health Check documentation
│   └── mcp_tools.md       # MCP Tools documentation
├── requirements.txt       # Production dependencies
└── requirements-dev.txt   # Development dependencies
```

### Running Tests

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

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/mcp-agentapi.git
   cd mcp-agentapi
   ```

2. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

3. Run the tests to ensure everything is working:
   ```bash
   ./run_tests.py
   ```

4. Make your changes and add tests for new functionality.

5. Run the tests again to ensure your changes don't break existing functionality:
   ```bash
   ./run_tests.py
   ```

6. Submit a pull request with your changes.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Need More Help?

If you're still having trouble, please open an issue on GitHub or contact the maintainers.
