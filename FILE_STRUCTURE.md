# MCP Server for Agent API - File Structure

This document explains the file structure and entry points for the MCP Server for Agent API.

## Main Entry Points

### MCP Server

The main entry point for the MCP server is `mcp_server.py`. This script imports and runs the `main()` function from `server.py`.

```bash
# Run the MCP server
python mcp_server.py

# Run with specific options
python mcp_server.py --transport sse --host 0.0.0.0 --port 8080
```

### Agent Controller Tools

The `agent_controller_tools.py` script provides a command-line interface for the agent controller tools. It can be used to interact with the Agent API without running the full MCP server.

```bash
# List available agents
python agent_controller_tools.py list_available_agents

# Start an agent
python agent_controller_tools.py start_agent --agent_type goose

# Send a message
python agent_controller_tools.py send_message --content "Hello, agent!" --type user
```

## File Structure

### Core Files

- **mcp_server.py**: Main entry point for the MCP server
- **server.py**: MCP server implementation with tools, resources, and prompts
- **agent_controller_tools.py**: Command-line interface for agent controller tools

### Bin Directory

The `bin` directory contains executable scripts for the main entry points:

- **bin/mcp-server-agentapi**: Executable script for the MCP server
- **bin/agent-cli**: Executable script for the agent controller CLI
- **bin/agentapi-mcp**: Executable script for the unified CLI

You can run these scripts directly from the bin directory:

```bash
# Run the MCP server
./bin/mcp-server-agentapi --transport stdio

# Run the agent controller CLI
./bin/agent-cli list_available_agents

# Run the unified CLI
./bin/agentapi-mcp list
```

### Source Files

- **src/agent_manager.py**: Agent detection, installation, and lifecycle management
- **src/api_client.py**: Agent API client
- **src/config.py**: Configuration management
- **src/agent_controller.py**: Agent controller tools with fallback behavior
- **src/context.py**: Application context and lifespan management
- **src/health_check.py**: Health monitoring
- **src/models.py**: Data models
- **src/resource_manager.py**: Resource management

## Removed Files

The following files have been removed to clean up the codebase:

- **server_new.py**: Renamed to server.py
- **src/wrappers/**: Redundant wrapper directory
- **src/main.py**: Redundant implementation, now using server.py directly

If you see imports from these files in other parts of the codebase, they should be updated to use the new files instead.

## Usage Examples

### Running the MCP Server

```bash
# Run with default settings
python mcp_server.py

# Run with SSE transport
python mcp_server.py --transport sse --host 0.0.0.0 --port 8080

# Run with specific agent type
python mcp_server.py --agent goose
```

### Using Agent Controller Tools

```bash
# List available agents
python agent_controller_tools.py list_available_agents

# Install an agent
python agent_controller_tools.py install_agent --agent_type goose

# Start an agent
python agent_controller_tools.py start_agent --agent_type goose

# Send a message
python agent_controller_tools.py send_message --content "Hello, agent!" --type user

# Get messages
python agent_controller_tools.py get_messages

# Get screen content
python agent_controller_tools.py get_screen
```

## Development

When developing the MCP server, you should focus on the following files:

- **server.py**: For adding or modifying MCP tools, resources, and prompts
- **src/agent_controller.py**: For implementing agent controller tools
- **src/agent_manager.py**: For agent detection, installation, and lifecycle management
- **src/api_client.py**: For interacting with the Agent API

## Testing

The test suite is located in the `tests/` directory. You can run the tests using the `run_tests.py` script:

```bash
# Run all tests
./run_tests.py

# Run tests in verbose mode
./run_tests.py -v

# Run tests with coverage report
./run_tests.py -c
```
