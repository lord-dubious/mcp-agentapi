# MCP Agent API

A Model Context Protocol (MCP) server that bridges MCP clients with AI agents through the [Agent API](https://github.com/coder/agentapi) by [Coder](https://github.com/coder).

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│ MCP Client      │     │ MCP Server   │     │ Agent API   │
│ (Windsurf,      │◄───►│ (This tool)  │◄───►│ (AI Agent)  │
│  Augment, etc.) │     │              │     │             │
└─────────────────┘     └──────────────┘     └─────────────┘
```

This package enables you to use AI agents like Goose, Aider, and Claude through any MCP-compatible client. It implements the [Model Context Protocol](https://github.com/modelcontextprotocol/protocol) specification to provide a standardized interface for controlling multiple AI agents.

## 🚀 Key Features

- **Multi-Agent Support**: Control Goose, Aider, Claude, and other agents through a unified interface
- **Agent Lifecycle Management**: Detect, install, start, stop, and restart agents
- **Message Handling**: Seamlessly send and receive messages between clients and agents
- **Health Monitoring**: Monitor agent and API health status
- **Flexible Transport**: Support for both stdio and SSE transport protocols
- **Command-Line Interface**: Comprehensive CLI for all operations

## 📦 Installation

```bash
# Using uv (Recommended)
pip install uv
uv pip install mcp-agentapi

# Using pip
pip install mcp-agentapi

# From source
git clone https://github.com/lord-dubious/mcp-agentapi.git
cd mcp-agentapi
./build.sh
uv pip install dist/*.whl
```

For development installation:
```bash
uv pip install -e ".[dev]"
```

## 🔌 Client Configuration

### Quick Setup

Add to your MCP client configuration (Claude Desktop, Windsurf, Augment, etc.):

```json
{
  "mcpServers": {
    "agent-controller": {
      "command": "python",
      "args": ["-m", "mcp_agentapi", "--transport", "stdio"],
      "env": {
        "TRANSPORT": "stdio"
      }
    }
  }
}
```

### Agent-Specific Configuration

For Goose:
```json
{
  "mcpServers": {
    "goose-agent": {
      "command": "python",
      "args": ["-m", "mcp_agentapi", "--agent", "goose", "--auto-start"],
      "env": {
        "GOOGLE_API_KEY": "YOUR-GOOGLE-API-KEY"
      }
    }
  }
}
```

For Aider:
```json
{
  "mcpServers": {
    "aider-agent": {
      "command": "python",
      "args": ["-m", "mcp_agentapi", "--agent", "aider", "--auto-start"],
      "env": {
        "OPENAI_API_KEY": "YOUR-OPENAI-API-KEY",
        "AIDER_MODEL": "deepseek"
      }
    }
  }
}
```

For Claude:
```json
{
  "mcpServers": {
    "claude-agent": {
      "command": "python",
      "args": ["-m", "mcp_agentapi", "--agent", "claude", "--auto-start"],
      "env": {
        "ANTHROPIC_API_KEY": "YOUR-ANTHROPIC-API-KEY"
      }
    }
  }
}
```

### SSE Transport

1. Start the server:
   ```bash
   mcp-agentapi server start --transport sse --port 8080 --agent goose --auto-start
   ```

2. Configure your client:
   ```json
   {
     "mcpServers": {
       "agent-api-server": {
         "transport": "sse",
         "serverUrl": "http://localhost:8080/sse"
       }
     }
   }
   ```

## 🔍 Troubleshooting

### Command Not Found
```bash
# Verify installation
pip list | grep mcp-agentapi

# Reinstall if needed
pip install mcp-agentapi
```

### Manual Agent Installation

```bash
# Goose
curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh | bash

# Aider
pip install aider-chat

# Claude
npm install -g @anthropic-ai/claude-code
```

### API Keys
- Goose: `GOOGLE_API_KEY`
- Aider: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `DEEPSEEK_API_KEY` (depending on model)
- Claude: `ANTHROPIC_API_KEY`

## 📁 Project Structure

```
mcp-agentapi/
├── bin/
│   └── mcp-agentapi            # CLI executable
├── mcp_agentapi/               # Main package
│   ├── server.py               # Server implementation
│   └── src/                    # Core modules
│       ├── agent_manager.py    # Agent lifecycle management
│       ├── api_client.py       # Agent API client
│       ├── config.py           # Configuration management
│       └── utils/              # Utility functions
```

See [FILE_STRUCTURE.md](FILE_STRUCTURE.md) for more details.

## 🔄 Command-Line Interface

```
mcp-agentapi <command-group> <command> [options]
```

### Server Commands
```bash
# Start the server
mcp-agentapi server start --transport stdio --agent goose --auto-start

# Check server status
mcp-agentapi server status
```

### Agent Commands
```bash
# List available agents
mcp-agentapi agent list

# Start an agent
mcp-agentapi agent start goose --auto-install

# Switch agents
mcp-agentapi agent switch claude --restart

# Send a message
mcp-agentapi agent send --content "Hello, agent!" --type user
```

### Configuration Commands
```bash
# Show configuration
mcp-agentapi config show

# Set configuration
mcp-agentapi config set transport=stdio agent_type=goose
```

### Shortcuts
The CLI provides shortcuts for common commands:
```bash
mcp-agentapi list    # Same as agent list
mcp-agentapi start goose    # Same as agent start goose
```

## 🤖 Multi-Agent Support

### Supported Agents

- **Goose**: Google's AI agent
- **Aider**: AI pair programming assistant
- **Claude**: Anthropic's AI assistant
- **Codex**: OpenAI's code-focused model
- **Custom**: Support for custom agents

### MCP Tools for Agent Control

When using an MCP client (Claude Desktop, Windsurf, etc.), you can use these tools:

```
Tool: list_available_agents
Arguments: {}
```

```
Tool: switch_agent
Arguments: {"agent_type": "goose"}
```

```
Tool: start_agent
Arguments: {"agent_type": "aider", "auto_install": true}
```

## 📚 Documentation

For more detailed documentation, see the `docs/` directory:

- [MCP Server Architecture](docs/mcp_server_architecture.md)
- [Technical Design](docs/technical_design.md)
- [Integration Guide](docs/integration_guide.md)

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.


