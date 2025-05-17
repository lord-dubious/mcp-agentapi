# MCP Agent API - File Structure

This document explains the file structure and entry points for the MCP Agent API.

## Main Entry Points

### MCP Server

The main entry point for the MCP server is the `mcp-agentapi` command-line tool.

```bash
# Start the MCP server
mcp-agentapi server start --transport stdio

# Start with specific options
mcp-agentapi server start --transport sse --host 0.0.0.0 --port 8080 --agent goose
```

### Agent Commands

The CLI provides commands for managing agents:

```bash
# List available agents
mcp-agentapi agent list

# Start an agent
mcp-agentapi agent start goose

# Send a message
mcp-agentapi agent send --content "Hello, agent!" --type user
```

## Project Structure

```
mcp-agentapi/
├── bin/
│   └── mcp-agentapi            # CLI executable
├── mcp_agentapi/               # Main package
│   ├── __init__.py             # Package initialization
│   ├── server.py               # Server implementation
│   ├── cli.py                  # CLI implementation
│   └── src/                    # Source code
│       ├── agent_manager.py    # Agent lifecycle management
│       ├── api_client.py       # Agent API client
│       ├── config.py           # Configuration management
│       ├── context.py          # Context management
│       ├── models.py           # Data models
│       └── utils/              # Utility functions
│           └── error_handler.py # Error handling
├── docs/                       # Documentation
│   ├── README.md               # Documentation index
│   ├── mcp_server_architecture.md # Architecture overview
│   └── technical_design.md     # Technical design details
└── tests/                      # Test suite
```

### Core Components

- **server.py**: MCP server implementation with tools, resources, and prompts
- **cli.py**: Command-line interface implementation
- **agent_manager.py**: Agent detection, installation, and lifecycle management
- **api_client.py**: Agent API client for communicating with agents
- **config.py**: Configuration management
- **context.py**: Application context and lifespan management

## Usage Examples

### Running the MCP Server

```bash
# Run with default settings
mcp-agentapi server start

# Run with SSE transport
mcp-agentapi server start --transport sse --host 0.0.0.0 --port 8080

# Run with specific agent type
mcp-agentapi server start --agent goose --auto-start
```

### Using Agent Commands

```bash
# List available agents
mcp-agentapi agent list

# Install an agent
mcp-agentapi agent install goose

# Start an agent
mcp-agentapi agent start goose

# Send a message
mcp-agentapi agent send --content "Hello, agent!" --type user

# Get messages
mcp-agentapi agent messages

# Get screen content
mcp-agentapi agent screen
```

## Development

When developing the MCP server, focus on these key files:

- **server.py**: MCP tools, resources, and prompts
- **agent_manager.py**: Agent detection, installation, and lifecycle management
- **api_client.py**: Agent API communication

## Testing

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=mcp_agentapi
```
