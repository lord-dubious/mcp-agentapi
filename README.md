# MCP Agent API

A Model Context Protocol (MCP) server for interacting with AI agents through the [Agent API](https://github.com/coder/agentapi) by [Coder](https://github.com/coder).

This project provides a complete MCP server implementation that serves as a bridge between MCP clients and the [original Agent API](https://github.com/coder/agentapi), allowing you to use AI agents like Goose, Aider, and Claude through any MCP-compatible client.

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│ MCP Client      │     │ MCP Server   │     │ Agent API   │
│ (Windsurf,      │◄───►│ (This tool)  │◄───►│ (AI Agent)  │
│  Augment, etc.) │     │              │     │             │
└─────────────────┘     └──────────────┘     └─────────────┘
```

This package provides a standardized interface for controlling and interacting with multiple AI agents (Goose, Aider, Claude, Codex) through a single MCP server implementation. It follows the [Model Context Protocol](https://github.com/modelcontextprotocol/protocol) specification and uses the Python MCP SDK to provide a consistent interface for MCP clients.

## 🚀 Features

- **Multi-Agent Support**: Control multiple AI agents through a single interface
- **Agent Detection**: Automatically detect installed agents
- **Agent Installation**: Install agents with a single command
- **Agent Lifecycle Management**: Start, stop, and restart agents
- **Message Handling**: Send and receive messages from agents
- **Screen Content**: Get the current screen content from agents
- **Health Monitoring**: Monitor the health of agents and the Agent API
- **Configuration Management**: Configure agents and the MCP server
- **Command-Line Interface**: Interact with agents through a CLI
- **MCP Server**: Expose agent functionality through the Model Context Protocol

## 🚀 Installation

### Using uv (Recommended)

```bash
# Install uv if you don't have it
pip install uv

# Install the package
uv pip install mcp-agentapi

# Or install in development mode
uv pip install -e ".[dev]"
```

### Using pip

```bash
# Install the package globally
pip install mcp-agentapi

# Or install in user mode
pip install --user mcp-agentapi
```

### Install from Source

```bash
# Clone the repo
git clone https://github.com/lord-dubious/mcp-agentapi.git

# Change to the directory
cd mcp-agentapi

# Build the package with uv
./build.sh

# Install the built package
uv pip install dist/*.whl

# Or install in development mode
uv pip install -e ".[dev]"
```

## 🔌 Adding to Your MCP Client

### Using the Standard MCP Configuration

Add this to your MCP client configuration (e.g., in Claude Desktop, Windsurf, or Augment):

#### For Specific Agent Configuration

You can configure the MCP server to start with a specific agent:

#### For Goose:

```json
{
  "mcpServers": {
    "goose-agent": {
      "command": "python",
      "args": ["-m", "mcp_agentapi", "--agent", "goose", "--auto-start"],
      "env": {
        "GOOGLE_API_KEY": "YOUR-GOOGLE-API-KEY",
        "TRANSPORT": "stdio"
      }
    }
  }
}
```

#### For Aider:

```json
{
  "mcpServers": {
    "aider-agent": {
      "command": "python",
      "args": ["-m", "mcp_agentapi", "--agent", "aider", "--auto-start"],
      "env": {
        "OPENAI_API_KEY": "YOUR-OPENAI-API-KEY",
        "AIDER_MODEL": "deepseek",
        "TRANSPORT": "stdio"
      }
    }
  }
}
```

#### For Claude:

```json
{
  "mcpServers": {
    "claude-agent": {
      "command": "python",
      "args": ["-m", "mcp_agentapi", "--agent", "claude", "--auto-start"],
      "env": {
        "ANTHROPIC_API_KEY": "YOUR-ANTHROPIC-API-KEY",
        "TRANSPORT": "stdio"
      }
    }
  }
}
```

#### For Dynamic Agent Control

If you want to control agents dynamically through MCP tools rather than specifying a particular agent in the configuration:

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

### Using SSE Transport

If you prefer to run the server separately and connect to it via SSE:

1. Start the server:
   ```bash
   mcp-agentapi server start --transport sse --port 8080 --agent goose --auto-start
   ```

2. Add this to your MCP client configuration:
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

### "Command not found" error
If you get a "command not found" error when running `mcp-agentapi`, make sure the package is installed correctly:

```bash
# Check if the package is installed
pip list | grep mcp-agentapi

# If not, install it
pip install mcp-agentapi
```


### Agent installation issues
If you're having trouble installing agents, you can install them manually:

#### Goose
```bash
curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh | bash
```

#### Aider
```bash
pip install aider-chat
```

#### Claude
```bash
npm install -g @anthropic-ai/claude-code
```

#### Codex
```bash
npm install -g @openai/codex
```

### API key issues
- For Goose, you need a Google API key (`GOOGLE_API_KEY`)
- For Aider, you need an API key for the model provider you're using:
  - OpenAI models: `OPENAI_API_KEY`
  - Claude models: `ANTHROPIC_API_KEY`
  - DeepSeek models: `DEEPSEEK_API_KEY`
- For Claude, you need an Anthropic API key (`ANTHROPIC_API_KEY`)
- For Codex, you need an API key for the provider you're using (default: `OPENAI_API_KEY`)

## 📁 Package Structure

The MCP server follows MCP SDK best practices for project structure:

```
mcp-agentapi/
├── .github/
│   └── workflows/
│       └── python-package.yml  # GitHub Actions workflow for CI/CD
├── bin/
│   └── mcp-agentapi            # Executable script for unified CLI
├── mcp_agentapi/               # Main package directory
│   ├── __init__.py             # Package initialization
│   ├── bin/                    # Bin directory for executable scripts
│   │   └── __init__.py
│   ├── py.typed                # Marker file for type hints
│   ├── server.py               # Server implementation
│   ├── unified_cli.py          # Unified CLI entry point
│   └── src/                    # Source code
│       ├── __init__.py
│       ├── agent_manager.py    # Agent detection and lifecycle management
│       ├── api_client.py       # Agent API client
│       ├── config.py           # Configuration management
│       ├── context.py          # Context management
│       ├── models.py           # Data models
│       └── utils/              # Utility functions
│           ├── __init__.py
│           └── error_handler.py
```

## 🔄 Command-Line Interface

The MCP Agent API provides a unified command-line interface for managing the MCP server and agents. The CLI is organized into subcommands for better organization and ease of use.

### Command Structure

```
mcp-agentapi <command-group> <command> [options]
```

### Server Commands

- `mcp-agentapi server start`: Start the MCP server
  ```bash
  mcp-agentapi server start --transport stdio --agent goose --auto-start
  ```

- `mcp-agentapi server stop`: Stop the MCP server
  ```bash
  mcp-agentapi server stop
  ```

- `mcp-agentapi server status`: Check the status of the MCP server
  ```bash
  mcp-agentapi server status
  ```

### Agent Commands

- `mcp-agentapi agent list`: List available agents
  ```bash
  mcp-agentapi agent list
  ```

- `mcp-agentapi agent status`: Show status of all agents
  ```bash
  mcp-agentapi agent status
  ```

- `mcp-agentapi agent start`: Start an agent
  ```bash
  mcp-agentapi agent start goose --auto-install
  ```

- `mcp-agentapi agent stop`: Stop an agent
  ```bash
  mcp-agentapi agent stop goose
  ```

- `mcp-agentapi agent switch`: Switch to a different agent
  ```bash
  mcp-agentapi agent switch claude --restart
  ```

- `mcp-agentapi agent install`: Install an agent
  ```bash
  mcp-agentapi agent install aider
  ```

- `mcp-agentapi agent restart`: Restart an agent
  ```bash
  mcp-agentapi agent restart goose
  ```

- `mcp-agentapi agent current`: Show the current agent type
  ```bash
  mcp-agentapi agent current
  ```

- `mcp-agentapi agent messages`: Get all messages in the conversation
  ```bash
  mcp-agentapi agent messages
  ```

- `mcp-agentapi agent send`: Send a message to the agent
  ```bash
  mcp-agentapi agent send --content "Hello, agent!" --type user
  ```

- `mcp-agentapi agent screen`: Get the current screen content
  ```bash
  mcp-agentapi agent screen
  ```

### Configuration Commands

- `mcp-agentapi config show`: Show current configuration
  ```bash
  mcp-agentapi config show
  ```

- `mcp-agentapi config set`: Set configuration values
  ```bash
  mcp-agentapi config set transport=stdio agent_type=goose
  ```

- `mcp-agentapi config reset`: Reset configuration to defaults
  ```bash
  mcp-agentapi config reset
  ```

### Shortcuts

For convenience, the CLI provides shortcuts for common commands:

- `mcp-agentapi list` -> `mcp-agentapi agent list`
- `mcp-agentapi status` -> `mcp-agentapi agent status`
- `mcp-agentapi start <agent>` -> `mcp-agentapi agent start <agent>`
- `mcp-agentapi stop <agent>` -> `mcp-agentapi agent stop <agent>`
- `mcp-agentapi switch <agent>` -> `mcp-agentapi agent switch <agent>`
- `mcp-agentapi install <agent>` -> `mcp-agentapi agent install <agent>`

## 🔄 Multi-Agent Flexibility

One of the key features of this MCP server implementation is the ability to control multiple agents through a single server instance. This provides a unified interface for managing and interacting with different AI agents without needing to restart the server or run multiple instances.

### Multi-Agent Control

The MCP server includes tools for managing multiple agents:

- **`list_available_agents`**: Lists all available agents on the system
- **`get_agent_type`**: Gets the current active agent
- **`switch_agent`**: Switches to a different agent
- **`start_agent`**: Starts a specific agent
- **`stop_agent`**: Stops a specific agent
- **`restart_agent`**: Restarts a specific agent

### Using MCP Tools for Multi-Agent Control

When using the MCP server through an MCP client (like Claude Desktop, Windsurf, etc.), you can use the following tools to control multiple agents:

```
Tool: list_available_agents
Arguments: {}
```

```
Tool: switch_agent
Arguments: {"agent_type": "goose"}
```

### Supported Agents

The MCP server supports the following agents:

- **Goose**: Google's AI agent
- **Aider**: AI pair programming assistant
- **Claude**: Anthropic's AI assistant
- **Codex**: OpenAI's code-focused model
- **Custom**: Support for custom agents

## 🛠️ MCP SDK Best Practices

This project follows the MCP SDK best practices for Python projects:

### Entry Point

The project provides a unified command-line interface through a single entry point:

- **mcp-agentapi**: Unified CLI for all operations with subcommands:
  - `mcp-agentapi server`: Commands for managing the MCP server
  - `mcp-agentapi agent`: Commands for managing agents
  - `mcp-agentapi config`: Commands for managing configuration

### Context Handling

The project uses proper context handling with the MCP SDK:

- **AgentAPIContext**: Type-safe context class for the MCP server
- **MockContext**: Mock context for CLI usage that implements the MCP SDK Context interface
- **agent_api_lifespan**: Lifespan context manager for resource management

## 📚 Documentation

For more detailed documentation, see the `docs/` directory:

- [MCP Server Architecture](docs/mcp_server_architecture.md): Overview of the MCP server architecture
- [Technical Design](docs/technical_design.md): Detailed technical design of the MCP server
- [Integration Guide](docs/integration_guide.md): Instructions for integrating with MCP clients and AI agents

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
