# MCP Agent API Documentation

Welcome to the MCP Agent API documentation. This documentation provides comprehensive information about the MCP Agent API server, which provides a Model Context Protocol (MCP) interface for interacting with AI agents through the Agent API.

## Documentation Index

### 1. Architecture and Design

- [MCP Server Architecture](mcp_server_architecture.md): Overview of the MCP server architecture
- [Technical Design](technical_design.md): Detailed technical design of the MCP server

### 2. Integration and Usage

- [Integration Guide](integration_guide.md): Instructions for integrating with MCP clients and AI agents

### 3. Development

- [Contributing Guide](../CONTRIBUTING.md): Guidelines for contributing to the project
- [File Structure](../FILE_STRUCTURE.md): Explanation of the file structure

## Quick Start

### Installation

```bash
# Install using uv (recommended)
uv pip install mcp-agentapi

# Or install using pip
pip install mcp-agentapi
```

### Running the MCP Server

```bash
# Run the MCP server with stdio transport
mcp-agentapi

# Run the MCP server with SSE transport
mcp-agentapi --transport sse --host 127.0.0.1 --port 8080
```

### Using the CLI

```bash
# List available agents
agent-cli list_available_agents

# Switch to a different agent
agent-cli switch_agent goose

# Check the health of the agent
agent-cli check_health
```

## Key Features

- **Multi-Agent Support**: Control multiple AI agents through a single interface
- **Agent Detection**: Automatically detect installed agents
- **Agent Lifecycle Management**: Start, stop, and restart agents
- **Message Handling**: Send and receive messages from agents
- **Screen Content**: Get the current screen content from agents
- **Health Monitoring**: Monitor the health of agents and the Agent API

## Architecture Overview

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│ MCP Client      │     │ MCP Server   │     │ Agent API   │
│ (Windsurf,      │◄───►│ (This tool)  │◄───►│ (AI Agent)  │
│  Augment, etc.) │     │              │     │             │
└─────────────────┘     └──────────────┘     └─────────────┘
```

The MCP Agent API server acts as a bridge between MCP clients and AI agents through the Agent API. It follows the Model Context Protocol specification and uses the Python MCP SDK to provide a standardized interface for interacting with AI agents.

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.
