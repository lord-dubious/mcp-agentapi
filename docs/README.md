# MCP Agent API Documentation

Welcome to the MCP Agent API documentation. This project provides a Model Context Protocol (MCP) server that bridges MCP clients with AI agents through the Agent API.

## Documentation Index

### Architecture & Design
- [MCP Server Architecture](mcp_server_architecture.md)
- [Technical Design](technical_design.md)

### Integration & Usage
- [Integration Guide](integration_guide.md)
- [MCP Inspector Usage](MCP_INSPECTOR_USAGE.md)

### Development
- [Contributing Guide](../CONTRIBUTING.md)
- [File Structure](../FILE_STRUCTURE.md)

## Quick Start

### Installation

```bash
# Using uv (recommended)
pip install uv
uv pip install mcp-agentapi

# Using pip
pip install mcp-agentapi
```

### Running the Server

```bash
# With stdio transport (default)
mcp-agentapi server start --agent goose --auto-start

# With SSE transport
mcp-agentapi server start --transport sse --port 8080
```

### Using the CLI

```bash
# List available agents
mcp-agentapi agent list

# Start an agent
mcp-agentapi agent start goose

# Send a message
mcp-agentapi agent send --content "Hello, agent!" --type user
```

## Key Features

- **Multi-Agent Support**: Control Goose, Aider, Claude, and other agents through a unified interface
- **Agent Lifecycle Management**: Detect, install, start, stop, and restart agents
- **Message Handling**: Seamlessly send and receive messages between clients and agents
- **Health Monitoring**: Monitor agent and API health status
- **Flexible Transport**: Support for both stdio and SSE transport protocols
- **Command-Line Interface**: Comprehensive CLI for all operations

## Architecture Overview

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│ MCP Client      │     │ MCP Server   │     │ Agent API   │
│ (Windsurf,      │◄───►│ (This tool)  │◄───►│ (AI Agent)  │
│  Augment, etc.) │     │              │     │             │
└─────────────────┘     └──────────────┘     └─────────────┘
```

The MCP Agent API server bridges MCP clients with AI agents through the Agent API, following the Model Context Protocol specification to provide a standardized interface.

## Supported Agents

- **Goose**: Google's AI agent
- **Aider**: AI pair programming assistant
- **Claude**: Anthropic's AI assistant
- **Codex**: OpenAI's code-focused model

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.
