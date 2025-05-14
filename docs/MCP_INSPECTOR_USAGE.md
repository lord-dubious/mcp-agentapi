# Using the MCP Inspector with MCP Server

This document provides instructions for using the MCP Inspector with our MCP server implementation.

## Prerequisites

1. Node.js and npm installed
2. MCP server installed
3. Agent(s) installed (Goose, Aider, Claude, Codex, or custom)

## Running the MCP Inspector

We've provided two scripts to make it easy to run the MCP Inspector with our MCP server:

1. `run_mcp_inspector.sh` - Basic script for running the MCP Inspector
2. `run_mcp_inspector_advanced.sh` - Advanced script with more options

### Basic Usage

```bash
./run_mcp_inspector.sh --agent goose --env GOOGLE_API_KEY=your_key
```

### Advanced Usage

```bash
./run_mcp_inspector_advanced.sh --agent goose --env GOOGLE_API_KEY=your_key --env ANOTHER_VAR=value
```

### Options

Both scripts support the following options:

- `--directory PATH` - Set the server directory (default: current directory)
- `--agent TYPE` - Set the agent type (default: goose)
- `--env KEY=VALUE` - Set an environment variable (can be used multiple times)

The advanced script also supports:

- `--port PORT` - Set the server port (default: 8000)
- `--inspector-arg ARG` - Pass an argument to the MCP Inspector (can be used multiple times)
- `--help` - Display help message

## Setting Environment Variables for Different Agents

You can set any environment variable for any agent type. Here are some common examples:

### Goose Agent

```bash
./run_mcp_inspector_advanced.sh --agent goose --env GOOGLE_API_KEY=your_key
```

### Aider Agent

```bash
./run_mcp_inspector_advanced.sh --agent aider --env OPENAI_API_KEY=your_key
```

### Claude Agent

```bash
./run_mcp_inspector_advanced.sh --agent claude --env ANTHROPIC_API_KEY=your_key
```

### Codex Agent

```bash
./run_mcp_inspector_advanced.sh --agent codex --env OPENAI_API_KEY=your_key
```

### Custom Agent

```bash
./run_mcp_inspector_advanced.sh --agent custom --env CUSTOM_API_KEY=your_key
```

## Manual Setup

If you prefer to run the MCP Inspector manually, you can follow these steps:

1. Start the MCP server:

```bash
cd /path/to/mcp-server-agentapi
python agentapi_mcp.py start-server
```

2. In a separate terminal, run the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector \
  --directory /path/to/mcp-server-agentapi \
  run \
  agent-controller \
  --agent-type goose
```

## Troubleshooting

If you encounter issues:

1. **Check API Keys**: Ensure you're using valid API keys for the agents.

2. **Check Agent Installation**: Make sure the agent is properly installed.

3. **Check Server Status**: Verify that the MCP server is running.

4. **Check Logs**: Look for error messages in the logs.

5. **Restart the Server**: If the server is unresponsive, try stopping and restarting it.

## Advanced Configuration

For advanced configuration, you can modify the scripts or run the MCP Inspector manually with additional options.

### Example: Running with a Different Port

```bash
./run_mcp_inspector_advanced.sh --agent goose --env GOOGLE_API_KEY=your_key --port 8080
```

### Example: Passing Additional Arguments to the MCP Inspector

```bash
./run_mcp_inspector_advanced.sh --agent goose --env GOOGLE_API_KEY=your_key --inspector-arg "--verbose" --inspector-arg "--timeout 60"
```

## Using the Agent Controller Tools Directly

You can also use the agent controller tools directly:

```bash
python agent_controller_tools.py get_agent_type
python agent_controller_tools.py list_available_agents
python agent_controller_tools.py install_agent --agent_type goose
python agent_controller_tools.py start_agent --agent_type goose
python agent_controller_tools.py send_message --content "Hello, agent!" --type user
python agent_controller_tools.py get_messages
python agent_controller_tools.py get_screen
python agent_controller_tools.py stop_agent --agent_type goose
```

This provides a more programmatic way to interact with the agent controller.
