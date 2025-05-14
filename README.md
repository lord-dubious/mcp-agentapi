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

### Development Setup

```bash
# Clone the repo
git clone https://github.com/lord-dubious/mcp-agentapi.git

# Change to the directory
cd mcp-agentapi

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
uv pip install -e ".[dev]"

# Run tests
pytest
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
      "args": ["/absolute/path/to/agent/mcp-server-agentapi/mcp_server.py", "--agent", "goose", "--auto-start"],
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
      "args": ["/absolute/path/to/agent/mcp-server-agentapi/mcp_server.py", "--agent", "aider", "--auto-start"],
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
      "args": ["/absolute/path/to/agent/mcp-server-agentapi/mcp_server.py", "--agent", "claude", "--auto-start"],
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
      "args": ["/absolute/path/to/agent/mcp-server-agentapi/mcp_server.py", "--transport", "stdio"],
      "env": {
        "TRANSPORT": "stdio"
      }
    }
  }
}
```

#### Running Directly from Repository

To run the MCP server directly from the repository without installing it, use this configuration:

```json
{
  "mcpServers": {
    "agent-controller": {
      "command": "python",
      "args": ["/absolute/path/to/agent/mcp-server-agentapi/mcp_server.py", "--transport", "stdio"],
      "cwd": "/absolute/path/to/agent/mcp-server-agentapi",
      "env": {
        "TRANSPORT": "stdio"
      }
    }
  }
}
```

Replace `/absolute/path/to/agent/mcp-server-agentapi` with the actual absolute path to the repository on your system.

If the script has trouble finding its dependencies, you can add the repository path to `PYTHONPATH`:

```json
{
  "mcpServers": {
    "agent-controller": {
      "command": "python",
      "args": ["/absolute/path/to/agent/mcp-server-agentapi/mcp_server.py", "--transport", "stdio"],
      "cwd": "/absolute/path/to/agent/mcp-server-agentapi",
      "env": {
        "TRANSPORT": "stdio",
        "PYTHONPATH": "/absolute/path/to/agent/mcp-server-agentapi"
      }
    }
  }
}
```

Using `cwd` (current working directory) is often simpler than setting `PYTHONPATH`.

With these configurations, you can use MCP tools to detect available agents, start/stop them, and switch between them without modifying the JSON configuration.

### Using SSE Transport

If you prefer to run the server separately and connect to it via SSE:

1. Start the server:
   ```bash
   agentapi-mcp start-server --transport sse --port 8080 --agent goose --auto-start
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

More configuration examples can be found in the `mcp-config-examples` directory.

## 🔍 Troubleshooting

### "Command not found" error
If you get a "command not found" error when running `agentapi-mcp` or `mcp-server-agentapi`, make sure the package is installed correctly:

```bash
# Check if the package is installed
pip list | grep mcp-server-agentapi

# If not, install it
pip install mcp-server-agentapi
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

### Connection issues
If you're having trouble connecting, try running the Agent API server manually:

```bash
# For Goose
export GOOGLE_API_KEY=your_google_api_key
agentapi server -- goose
```

Then run the MCP server without auto-start:
```bash
agentapi-mcp start-server --agent goose --agent-api-url http://localhost:3284 --no-auto-start
```

## 🛠️ Advanced Options

### Unified Agent Management CLI

The MCP server includes a comprehensive command-line interface for managing agents. You can use this CLI to list available agents, start and stop them, switch between them, and start the MCP server.

```bash
# List available agents
agentapi-mcp list

# Show status of all agents
agentapi-mcp status

# Start a specific agent
agentapi-mcp start goose

# Stop a specific agent
agentapi-mcp stop aider

# Switch to a different agent
agentapi-mcp switch claude

# Switch to a different agent and restart it
agentapi-mcp switch claude --restart

# Install a specific agent
agentapi-mcp install aider

# Start the MCP server with the current agent
agentapi-mcp start-server

# Start the MCP server with a specific agent
agentapi-mcp start-server --agent goose

# Start the MCP server with SSE transport
agentapi-mcp start-server --transport sse --port 8080

# Start the MCP server with auto-start enabled
agentapi-mcp start-server --auto-start

# Start the MCP server without auto-starting the agent
agentapi-mcp start-server --no-auto-start
```

For more information, run `agentapi-mcp --help` or `agentapi-mcp <command> --help`.

### Configuration

The MCP server can be configured in three ways, in order of precedence:

1. **Environment Variables** (highest priority)
2. **Configuration File** (`mcp-server-agentapi.json`)
3. **Default Values**

#### Environment Variables

- `TRANSPORT`: Transport mode (`stdio` or `sse`, default: `stdio`)
- `HOST`: Host to bind to for SSE mode (default: `0.0.0.0`)
- `PORT`: Port to listen on for SSE mode (default: `8080`)
- `AGENT_API_URL`: Agent API URL (default: `http://localhost:3284`)
- `AGENT_TYPE`: Agent type (`claude`, `goose`, `aider`, `codex`, or `custom`)
- `AUTO_START_AGENT`: Automatically start the Agent API server (`true`, `1`, or `yes`)
- `DEBUG`: Enable debug logging (`true`, `1`, or `yes`)

Agent-specific API keys:
- `GOOGLE_API_KEY`: API key for Goose
- `OPENAI_API_KEY`: API key for Aider and Codex
- `ANTHROPIC_API_KEY`: API key for Claude
- `AIDER_MODEL`: Model to use with Aider (default: `deepseek`)

#### Configuration File

Create a file named `mcp-server-agentapi.json` in the current directory:

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

### Command-line Options

```bash
# Run with SSE transport
agentapi-mcp start-server --transport sse --port 8080 --agent goose --auto-start

# Run with stdio transport
agentapi-mcp start-server --agent aider --auto-start

# Run with debug logging
agentapi-mcp start-server --agent claude --auto-start --debug

# Legacy command-line options (still supported)
mcp-server-agentapi --transport sse --port 8080 --agent-type goose --auto-start-agent
```

## 📚 What's Included

This MCP server provides:

- **Message Sending/Receiving**: Send messages to agents and get responses
- **Status Monitoring**: Check if the agent is ready or busy
- **Conversation History**: Access the full chat history
- **Real-time Updates**: Get notified when new messages arrive
- **Auto-start**: Automatically start the Agent API server
- **Agent Management**: Detect, install, and manage different agent types
- **Configuration Management**: Flexible configuration system with environment variables and config files
- **CLI Tools**: Command-line interface for managing agents
- **Improved Architecture**: Following the mcp-mem0 pattern for better maintainability

## 🔒 Reliability and Robustness

The MCP server includes several features to ensure reliability and robustness:

### Enhanced Agent Detection

- **Multi-method Detection**: Uses multiple methods to detect running agents, including status checks, message content analysis, and API type detection
- **Agent-specific Patterns**: Recognizes agent-specific patterns in message content to improve detection accuracy
- **Graceful Fallbacks**: Provides graceful fallbacks when detection methods fail
- **Detailed Logging**: Logs detailed information about detection steps for easier debugging

### Robust Event Streaming

- **Ordered Event Processing**: Ensures events are processed in the correct order using a buffer and sorting mechanism
- **Automatic Reconnection**: Automatically reconnects to the event stream if the connection is lost
- **Exponential Backoff**: Uses exponential backoff with jitter for reconnection attempts
- **Event Monitoring**: Monitors event stream health and detects stale connections
- **Concurrent Processing**: Processes events concurrently for better performance

### Reliable Process Management

- **Graceful Termination**: Attempts graceful termination before force killing processes
- **Resource Cleanup**: Ensures proper cleanup of process resources
- **Deadlock Prevention**: Avoids deadlocks by performing long operations outside locks
- **Signal Handling**: Uses appropriate signals (SIGINT, SIGTERM, SIGKILL) for process termination
- **Error Recovery**: Recovers from process termination errors

### Comprehensive Error Handling

- **Detailed Error Context**: Provides detailed context information with exceptions
- **Error Categorization**: Categorizes errors for easier handling and reporting
- **Stack Trace Capture**: Captures stack traces for debugging
- **Serializable Errors**: Makes errors serializable for logging and reporting
- **Graceful Degradation**: Continues operation when possible, even when errors occur

## 🚀 Running Directly from Repository

If you want to run the MCP server directly from the repository without installing it, you can do so with the following commands:

```bash
# Clone the repository
git clone https://github.com/mcp-server-team/mcp-server-agentapi.git

# Change to the directory
cd mcp-server-agentapi

# Run the MCP server directly
python mcp_server.py --transport stdio

# Or run with a specific agent
python mcp_server.py --agent goose --auto-start

# Run with debug logging
python mcp_server.py --agent claude --auto-start --debug
```

## 📁 Package Structure

The MCP server follows MCP SDK best practices for project structure:

```
mcp-agentapi/
├── .github/
│   └── workflows/
│       └── python-package.yml  # GitHub Actions workflow for CI/CD
├── bin/
│   ├── agent-cli               # Executable script for agent CLI
│   ├── agentapi-mcp            # Executable script for unified CLI
│   └── mcp-agentapi            # Executable script for MCP server
├── mcp_agentapi/               # Main package directory
│   ├── __init__.py             # Package initialization
│   ├── agent_cli.py            # Agent CLI entry point
│   ├── bin/                    # Bin directory for executable scripts
│   │   └── __init__.py
│   ├── cli.py                  # Unified CLI entry point
│   ├── main.py                 # Main entry point
│   ├── py.typed                # Marker file for type hints
│   ├── server.py               # Server implementation
│   └── src/                    # Source code
│       ├── __init__.py
│       ├── utils/              # Utility functions
│       │   ├── __init__.py
│       │   └── error_handler.py
├── .gitattributes              # Git attributes
├── .gitignore                  # Git ignore
├── build.sh                    # Build script for uv
├── CONTRIBUTING.md             # Contributing guidelines
├── LICENSE                     # License file
├── MANIFEST.in                 # Package manifest
├── pyproject.toml              # Project configuration
├── README.md                   # Project documentation
├── setup.py                    # Setup script for backward compatibility
└── tests/                      # Tests
    ├── conftest.py             # Test fixtures
    ├── test_integration.py     # Integration tests
    └── ...                     # Other test files
```

For a detailed explanation of the file structure, see [FILE_STRUCTURE.md](FILE_STRUCTURE.md).

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

### Agent Detection and Auto-Configuration

The server includes automatic agent detection capabilities that:

1. Detect all available agents on the system
2. Automatically configure API keys and settings for each agent
3. Allow seamless switching between agents

### JSON Configuration for Different MCP Clients

#### Basic Multi-Agent Configuration (Claude Desktop)

```json
{
  "mcpServers": {
    "multi-agent-controller": {
      "name": "Multi-Agent Controller",
      "description": "MCP server for controlling multiple AI agents",
      "command": "python",
      "args": ["-m", "mcp-server-agentapi"],
      "env": {
        "TRANSPORT": "stdio",
        "GOOGLE_API_KEY": "${GOOGLE_API_KEY}",
        "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}",
        "OPENAI_API_KEY": "${OPENAI_API_KEY}",
        "AIDER_MODEL": "deepseek",
        "AGENT_API_URL": "http://localhost:3284"
      }
    }
  }
}
```

#### Windsurf Configuration

```json
{
  "mcpServers": {
    "multi-agent-controller": {
      "name": "Multi-Agent Controller",
      "description": "MCP server for controlling multiple AI agents",
      "command": "python",
      "args": ["-m", "mcp-server-agentapi"],
      "env": {
        "TRANSPORT": "stdio",
        "GOOGLE_API_KEY": "${GOOGLE_API_KEY}",
        "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}",
        "OPENAI_API_KEY": "${OPENAI_API_KEY}"
      },
      "capabilities": {
        "tools": true,
        "resources": true
      }
    }
  }
}
```

#### Augment Configuration

```json
{
  "mcpServers": {
    "multi-agent-controller": {
      "name": "Multi-Agent Controller",
      "description": "MCP server for controlling multiple AI agents",
      "command": "python",
      "args": ["-m", "mcp-server-agentapi"],
      "cwd": "/path/to/agent/mcp-server-agentapi",
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

#### Web Client Configuration (SSE Transport)

```json
{
  "mcpServers": {
    "multi-agent-controller-sse": {
      "name": "Multi-Agent Controller (SSE)",
      "description": "MCP server for controlling multiple AI agents using SSE transport",
      "command": "python",
      "args": ["-m", "mcp-server-agentapi", "--transport", "sse", "--host", "127.0.0.1", "--port", "8080"],
      "env": {
        "GOOGLE_API_KEY": "${GOOGLE_API_KEY}",
        "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}",
        "OPENAI_API_KEY": "${OPENAI_API_KEY}"
      }
    }
  }
}
```

### Using the Unified CLI for Multi-Agent Management

The `agentapi-mcp` CLI provides a unified interface for managing multiple agents:

```bash
# List all available agents
./bin/agentapi-mcp list

# Switch to a different agent
./bin/agentapi-mcp switch goose

# Start an agent
./bin/agentapi-mcp start aider

# Stop an agent
./bin/agentapi-mcp stop claude
```

### Example Usage Flow

1. Start the MCP server with the multi-agent configuration
2. Use the `list_available_agents` tool to see all available agents
3. Use the `switch_agent` tool to switch to your desired agent
4. Interact with the current agent
5. Switch to another agent when needed without restarting the server

### Using MCP Tools for Multi-Agent Control

When using the MCP server through an MCP client (like Claude Desktop, Windsurf, etc.), you can use the following tools to control multiple agents:

```
Tool: list_available_agents
Arguments: {}
```

```
Tool: get_agent_type
Arguments: {}
```

```
Tool: switch_agent
Arguments: {"agent_type": "goose"}
```

```
Tool: start_agent
Arguments: {"agent_type": "aider"}
```

```
Tool: stop_agent
Arguments: {"agent_type": "claude"}
```

```
Tool: restart_agent
Arguments: {"agent_type": "codex"}
```

These tools allow you to manage multiple agents directly from within your MCP client interface.

### Supported Agents

The MCP server supports the following agents:

- **Goose**: Google's AI agent
- **Aider**: AI pair programming assistant
- **Claude**: Anthropic's AI assistant
- **Codex**: OpenAI's code-focused model
- **Custom**: Support for custom agents

Each agent can be configured with its own API keys and settings, and you can switch between them seamlessly.

### Installation and Setup for Multi-Agent Control

To set up the MCP server for multi-agent control:

1. **Install the MCP server**:
   ```bash
   pip install mcp-server-agentapi
   ```

2. **Install the agents you want to use**:
   ```bash
   # Install Goose
   curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh | CONFIGURE=false bash

   # Install Aider
   pip install aider-chat

   # Install Claude
   npm install -g @anthropic-ai/claude-code

   # Install Codex
   npm install -g @openai/codex
   ```

3. **Set up API keys**:
   - For Goose: Set `GOOGLE_API_KEY` environment variable
   - For Aider: Set `OPENAI_API_KEY` environment variable
   - For Claude: Set `ANTHROPIC_API_KEY` environment variable
   - For Codex: Set `OPENAI_API_KEY` environment variable

4. **Create a configuration file** (optional):
   Create a file named `mcp-server-agentapi.json` with your configuration:
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

5. **Add the MCP server to your MCP client**:
   Use one of the JSON configurations provided above to add the MCP server to your MCP client (Claude Desktop, Windsurf, Augment, etc.).

Once set up, you can use the MCP tools or CLI commands to switch between agents as needed.

### Troubleshooting Multi-Agent Control

If you encounter issues with multi-agent control:

1. **Agent not detected**:
   - Ensure the agent is installed correctly
   - Check if the agent is in your PATH
   - Run `./bin/agentapi-mcp list` to see if the agent is detected

2. **Cannot switch agents**:
   - Check if the Agent API is running (`http://localhost:3284` by default)
   - Ensure you have the necessary API keys set
   - Try stopping the current agent first: `./bin/agentapi-mcp stop <current_agent>`

3. **API key issues**:
   - Verify that the API keys are set correctly in your environment
   - For Goose: `GOOGLE_API_KEY`
   - For Aider: `OPENAI_API_KEY`
   - For Claude: `ANTHROPIC_API_KEY`
   - For Codex: `OPENAI_API_KEY`

4. **Agent API not starting**:
   - Check if the Agent API is already running on port 3284
   - Try starting it manually: `agentapi server`
   - Check for error messages in the logs

5. **MCP client not connecting**:
   - Verify the JSON configuration is correct
   - Ensure the paths to the MCP server are correct
   - Check if the transport type (stdio/SSE) is supported by your client

## 🛠️ MCP SDK Best Practices

This project follows the MCP SDK best practices for Python projects:

### Entry Points

The project provides executable scripts in the `bin` directory:

- **bin/mcp-server-agentapi**: Main entry point for the MCP server
- **bin/agent-cli**: Command-line interface for the agent controller
- **bin/agentapi-mcp**: Unified CLI for agent management

### Context Handling

The project uses proper context handling with the MCP SDK:

- **AgentAPIContext**: Type-safe context class for the MCP server
- **MockContext**: Mock context for CLI usage that implements the MCP SDK Context interface
- **agent_api_lifespan**: Lifespan context manager for resource management

### Error Handling

The project uses standardized error handling:

- **handle_exception**: Utility function for handling exceptions
- **create_error_response**: Utility function for creating error responses
- **MCPServerError**: Base exception class for all MCP server errors

### Documentation

The project includes comprehensive documentation:

- **README.md**: Main documentation with usage examples
- **FILE_STRUCTURE.md**: Detailed explanation of the file structure
- **Docstrings**: All modules, classes, and functions have detailed docstrings

## 🔍 Using MCP Inspector

You can use the MCP Inspector to test and interact with the MCP server's agent controller tools. The MCP Inspector is a tool provided by the Model Context Protocol (MCP) that allows you to inspect and interact with MCP servers.

### Using MCP Inspector with the MCP Server

You can use the MCP Inspector to test and interact with the MCP server:

```bash
# Start the MCP server in one terminal
python mcp_server.py --transport sse --port 8080 --agent goose --auto-start

# In another terminal, use the MCP Inspector to connect to the server
npx @modelcontextprotocol/inspector http://localhost:8080/sse
```

This will open the MCP Inspector UI in your browser, allowing you to:

1. View available tools, resources, and prompts
2. Call tools to manage agents
3. Send messages to agents
4. View agent responses
5. Test the server's functionality

### Using MCP Inspector with Direct Tool Testing

You can also use the MCP Inspector to test individual tools directly:

```bash
# Run the MCP server with the inspector
npx @modelcontextprotocol/inspector uv --directory /path/to/mcp-server-agentapi run mcp_server.py
```

This will start the MCP server and open the MCP Inspector UI, allowing you to test the server's functionality directly.

For more examples and detailed instructions, see the `examples/mcp_inspector_example.md` file.

### JSON Configuration for MCP Clients

To use the MCP server with an MCP client (like Claude Desktop, Windsurf, or Augment), add this to your client configuration:

```json
{
  "mcpServers": {
    "agent-controller": {
      "command": "python",
      "args": ["/absolute/path/to/agent/mcp-server-agentapi/mcp_server.py", "--transport", "stdio"],
      "cwd": "/absolute/path/to/agent/mcp-server-agentapi",
      "env": {
        "TRANSPORT": "stdio"
      }
    }
  }
}
```

Replace `/absolute/path/to/agent/mcp-server-agentapi` with the actual absolute path to the repository on your system.

For SSE transport, you can use:

```json
{
  "mcpServers": {
    "agent-controller": {
      "transport": "sse",
      "serverUrl": "http://localhost:8080/sse"
    }
  }
}
```

Make sure to start the MCP server separately with:

```bash
python mcp_server.py --transport sse --port 8080 --agent goose --auto-start
```

## 🧰 Available Methods

The MCP server provides a comprehensive set of methods for agent management:

### Agent Detection and Status

- **`detect_agents()`**: Detects all available agents on the system
- **`get_agent_status(agent_type)`**: Gets the installation and running status of an agent
- **`_check_agent_api_installed()`**: Checks if the Agent API is installed
- **`_detect_agent(agent_type)`**: Detects if a specific agent is installed

### Agent Installation

- **`install_agent_api()`**: Installs the Agent API
- **`install_agent(agent_type)`**: Installs a specific agent
- **`_install_goose()`**: Installs the Goose agent using the official installation script (`curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh | CONFIGURE=false bash`)
- **`_install_aider()`**: Installs the Aider agent using pip (`pip install aider-chat`)
- **`_install_claude()`**: Installs the Claude agent using npm (`npm install -g @anthropic-ai/claude-code`)
- **`_install_codex()`**: Installs the Codex agent using npm (`npm install -g @openai/codex`)

### Agent Lifecycle Management

- **`start_agent(agent_type)`**: Starts a specific agent
- **`stop_agent(agent_type)`**: Stops a running agent
- **`restart_agent(agent_type)`**: Restarts an agent
- **`switch_agent(agent_type)`**: Switches to a different agent
- **`monitor_agent(agent_type, auto_reconnect)`**: Monitors an agent's status and optionally reconnects it if it crashes

### Agent Communication

- **`send_message(agent_type, message)`**: Sends a message to an agent
- **`get_conversation_history(agent_type)`**: Gets the conversation history with an agent
- **`get_agent_events(agent_type)`**: Gets events from an agent

### Configuration Management

- **`get_agent_config(agent_type)`**: Gets the configuration for a specific agent
- **`validate_api_key(agent_type)`**: Validates the API key for a specific agent
- **`load_config()`**: Loads the configuration from environment variables, configuration file, and default values

#### Agent-Specific Configuration

Each agent has specific configuration requirements:

##### Goose
- **API Key**: `GOOGLE_API_KEY` environment variable
- **Model Selection**: Set via `GOOSE_MODEL` environment variable or command-line arguments
- **Configuration File**: Optional, set via `GOOSE_CONFIG_FILE` environment variable

##### Aider
- **API Keys**: Multiple providers supported via environment variables:
  - `OPENAI_API_KEY` for OpenAI models
  - `ANTHROPIC_API_KEY` for Claude models
  - `DEEPSEEK_API_KEY` for DeepSeek models
- **Model Selection**: Set via `AIDER_MODEL` environment variable or command-line arguments
- **Configuration File**: YAML file at `~/.aider.conf.yml` or specified via `AIDER_CONFIG_FILE` environment variable

##### Claude
- **API Key**: `ANTHROPIC_API_KEY` environment variable
- **Model Selection**: Set via `CLAUDE_MODEL` environment variable (default: `claude-3-7-sonnet-20250219`)
- **Configuration File**: Optional, set via `CLAUDE_CONFIG_FILE` environment variable

##### Codex
- **API Keys**: Multiple providers supported via environment variables:
  - `OPENAI_API_KEY` for OpenAI models
  - `ANTHROPIC_API_KEY` for Anthropic models
  - `GEMINI_API_KEY` for Gemini models
  - And many others (see documentation)
- **Provider Selection**: Set via `CODEX_PROVIDER` environment variable (default: `openai`)
- **Model Selection**: Set via `CODEX_MODEL` environment variable (default: `o4-mini`)
- **Configuration File**: JSON file at `~/.codex/config.json` or specified via `CODEX_CONFIG_FILE` environment variable

## 🏗️ Architecture

The MCP server follows the architecture pattern of mcp-mem0:

- **Context Management**: Uses a dataclass for context and asynccontextmanager for lifecycle management
- **Modular Organization**: Separates concerns into different modules
- **Dependency Injection**: Passes context to tools and resources for accessing shared state
- **Error Handling**: Consistent error handling with informative messages
- **Configuration Management**: Robust configuration system with support for environment variables, configuration files, and default values

## 🤖 Multi-Agent Orchestration

The MCP server provides capabilities for managing and orchestrating multiple AI agents. See the [Multi-Agent Orchestration](docs/multi_agent_orchestration.md) documentation for details on:

- Current capabilities for agent management
- Limitations of the current implementation
- Future enhancements for true multi-agent orchestration
- Usage examples for agent switching and multi-agent workflows

### Directory Structure

```
mcp-server-agentapi/
├── src/                     # Core package directory
│   ├── main.py              # MCP server implementation and tools/resources
│   ├── cli.py               # Unified CLI module
│   ├── context.py           # Context management and lifecycle
│   ├── api_client.py        # Agent API communication
│   ├── models.py            # Data models and enums
│   ├── config.py            # Configuration management
│   ├── event_emitter.py     # Event streaming
│   ├── agent_manager.py     # Agent detection, installation, and lifecycle management
│   ├── resource_manager.py  # Resource tracking and cleanup
│   ├── health_check.py      # Health monitoring
│   ├── agent_controller.py  # Agent controller tools implementation
│   └── __init__.py          # Package initialization
├── docs/                    # Documentation
│   └── multi_agent_orchestration.md # Multi-agent orchestration documentation
├── examples/                # Example scripts
│   └── mcp_usage_example.py # Example of using the MCP server
├── tests/                   # Unit tests
├── agentapi_mcp.py          # Single entry point for the MCP server
├── agent_controller_wrapper.py # Wrapper for agent controller tools
├── mcp-config-examples/     # Example MCP client configurations
├── setup.py                 # Package setup and installation
├── pyproject.toml           # Project configuration
└── README.md                # Documentation
```

## 🧪 Testing

The MCP server includes a comprehensive test suite to ensure reliability and correctness. The tests are organized by module and cover all aspects of the server's functionality.

### Running Tests

You can run the tests using the `run_tests.py` script:

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

### Test Structure

The tests are organized by module:

- `test_config.py`: Tests for the configuration management functionality
- `test_api_client.py`: Tests for the Agent API client
- `test_agent_manager.py`: Tests for the agent detection, installation, and lifecycle management
- `test_resource_manager.py`: Tests for the resource management functionality
- `test_health_check.py`: Tests for the health check functionality
- `test_server.py`: Tests for the MCP server functionality
- `test_models.py`: Tests for the data models
- `test_exceptions.py`: Tests for the custom exceptions

### Test Markers

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

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/mcp-server-agentapi.git
   cd mcp-server-agentapi
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

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤔 Need More Help?

If you're still having trouble, please open an issue on GitHub or contact the maintainers.