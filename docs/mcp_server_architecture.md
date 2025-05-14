# MCP Server Architecture

This document describes the architecture of the MCP Agent API server, which provides a Model Context Protocol (MCP) interface for interacting with AI agents through the Agent API.

## 1. Overview

The MCP Agent API server acts as a bridge between MCP clients (like Windsurf, Augment, Claude Desktop) and AI agents (like Goose, Aider, Claude, Codex) through the Agent API. It follows the Model Context Protocol specification and uses the Python MCP SDK to provide a standardized interface for interacting with AI agents.

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│ MCP Client      │     │ MCP Server   │     │ Agent API   │
│ (Windsurf,      │◄───►│ (This tool)  │◄───►│ (AI Agent)  │
│  Augment, etc.) │     │              │     │             │
└─────────────────┘     └──────────────┘     └─────────────┘
```

## 2. Core Components

### 2.1 MCP Server

The MCP server is built using the FastMCP framework from the MCP SDK. It provides the following functionality:

- **Tools**: Functions that can be called by MCP clients to interact with agents
- **Resources**: Data that can be accessed by MCP clients
- **Prompts**: Templates for generating text
- **Context**: Shared state between tools and resources

### 2.2 Agent Manager

The Agent Manager is responsible for:

- **Agent Detection**: Automatically detecting installed agents
- **Agent Installation**: Installing agents when needed
- **Agent Lifecycle Management**: Starting, stopping, and restarting agents
- **Agent Configuration**: Managing agent-specific configuration

### 2.3 Agent API Client

The Agent API Client communicates with the Agent API to:

- **Send Messages**: Send messages to agents
- **Receive Messages**: Receive messages from agents
- **Get Screen Content**: Get the current screen content from agents
- **Check Health**: Monitor the health of agents and the Agent API

### 2.4 Context Management

The context management system provides:

- **Lifespan Management**: Managing the lifecycle of resources
- **Shared State**: Sharing state between tools and resources
- **Configuration**: Managing configuration for the MCP server and agents

## 3. Data Flow

### 3.1 Client to Agent

1. MCP client calls a tool (e.g., `send_message`)
2. MCP server processes the tool call
3. Agent Manager ensures the agent is running
4. Agent API Client sends the message to the Agent API
5. Agent API forwards the message to the agent
6. Agent processes the message

### 3.2 Agent to Client

1. Agent sends a message to the Agent API
2. Agent API Client receives the message from the Agent API
3. MCP server processes the message
4. MCP server sends the message to the MCP client

## 4. Multi-Agent Support

The MCP server supports multiple agents through a single interface:

### 4.1 Agent Switching

The MCP server provides tools for switching between agents:

- **list_available_agents**: Lists all available agents
- **get_agent_type**: Gets the current active agent
- **switch_agent**: Switches to a different agent

### 4.2 Agent Detection

The Agent Manager automatically detects installed agents and their configurations:

1. Scans the system for installed agents
2. Determines the capabilities of each agent
3. Configures the MCP server to use the detected agents

### 4.3 Agent Configuration

Each agent can be configured with its own settings:

- **API Keys**: Agent-specific API keys
- **Models**: Agent-specific model configurations
- **Settings**: Agent-specific settings

## 5. Implementation Details

### 5.1 Package Structure

```
mcp-agentapi/
├── mcp_agentapi/               # Main package directory
│   ├── __init__.py             # Package initialization
│   ├── agent_cli.py            # Agent CLI entry point
│   ├── bin/                    # Bin directory for executable scripts
│   ├── cli.py                  # Unified CLI entry point
│   ├── main.py                 # Main entry point
│   ├── server.py               # Server implementation
│   └── src/                    # Source code
│       ├── agent_manager.py    # Agent detection and lifecycle management
│       ├── api_client.py       # Agent API client
│       ├── config.py           # Configuration management
│       ├── context.py          # Context management
│       ├── models.py           # Data models
│       └── utils/              # Utility functions
```

### 5.2 Key Classes

- **FastMCP**: The main MCP server class from the MCP SDK
- **AgentAPIContext**: The context class for the MCP server
- **AgentManager**: The class responsible for agent detection and lifecycle management
- **AgentAPIClient**: The class responsible for communicating with the Agent API
- **Config**: The configuration class for the MCP server

### 5.3 Error Handling

The MCP server uses standardized error handling:

- **MCPServerError**: Base exception class for all MCP server errors
- **handle_exception**: Utility function for handling exceptions
- **create_error_response**: Utility function for creating error responses

## 6. Configuration

### 6.1 Server Configuration

The MCP server can be configured with the following settings:

- **Transport**: The transport mode (stdio or SSE)
- **Host**: The host to bind to (for SSE mode)
- **Port**: The port to listen on (for SSE mode)
- **Debug**: Whether to enable debug logging

### 6.2 Agent Configuration

Each agent can be configured with the following settings:

- **Agent Type**: The type of agent to use
- **Auto Start**: Whether to automatically start the agent
- **Agent API URL**: The URL of the Agent API

### 6.3 Configuration File

The MCP server uses a JSON configuration file:

```json
{
  "agent_api_url": "http://localhost:3284",
  "auto_start_agent": true,
  "agent_type": "goose",
  "server": {
    "transport": "stdio",
    "host": "0.0.0.0",
    "port": 8080
  },
  "debug": false
}
```

## 7. Integration with MCP Clients

### 7.1 JSON Configuration

MCP clients can be configured to use the MCP server with the following JSON configuration:

```json
{
  "mcpServers": {
    "multi-agent-controller": {
      "name": "Multi-Agent Controller",
      "description": "MCP server for controlling multiple AI agents",
      "command": "python",
      "args": ["-m", "mcp-agentapi"],
      "env": {
        "TRANSPORT": "stdio",
        "GOOGLE_API_KEY": "${GOOGLE_API_KEY}",
        "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}",
        "OPENAI_API_KEY": "${OPENAI_API_KEY}"
      }
    }
  }
}
```

### 7.2 Tool Usage

MCP clients can use the following tools to interact with agents:

- **send_message**: Send a message to the agent
- **get_screen_content**: Get the current screen content from the agent
- **check_health**: Check the health of the agent and the Agent API
- **list_available_agents**: List all available agents
- **switch_agent**: Switch to a different agent

## 8. Future Enhancements

- **Agent Installation**: Automatically install agents when needed
- **Agent Discovery**: Discover agents on the network
- **Agent Authentication**: Authenticate with agents
- **Agent Authorization**: Authorize agents to perform actions
- **Agent Capabilities**: Discover agent capabilities
- **Agent Events**: Subscribe to agent events
