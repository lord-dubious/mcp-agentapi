# Integration Guide

This document provides instructions for integrating the MCP Agent API server with various MCP clients and AI agents.

## 1. Integrating with MCP Clients

### 1.1 Claude Desktop

1. Open Claude Desktop
2. Go to Settings > MCP Servers
3. Click "Add Server"
4. Copy and paste the following JSON configuration:

```json
{
  "mcpServers": {
    "agent-controller": {
      "name": "Agent API Controller",
      "description": "MCP server for interacting with AI agents through the Agent API",
      "command": "python",
      "args": ["-m", "mcp-agentapi"],
      "env": {
        "TRANSPORT": "stdio"
      }
    }
  }
}
```

5. Click "Save"
6. Select the server from the dropdown in the chat interface

### 1.2 Windsurf

1. Open Windsurf
2. Go to Settings > Integrations > MCP Servers
3. Click "Add New Server"
4. Copy and paste the following JSON configuration:

```json
{
  "mcpServers": {
    "agent-controller": {
      "name": "Agent API Controller",
      "description": "MCP server for interacting with AI agents through the Agent API",
      "command": "python",
      "args": ["-m", "mcp-agentapi"],
      "env": {
        "TRANSPORT": "stdio"
      },
      "capabilities": {
        "tools": true,
        "resources": true
      }
    }
  }
}
```

5. Click "Save"
6. Select the server when creating a new chat

### 1.3 Augment

1. Open Augment
2. Go to Settings > Integrations > MCP
3. Click "Add MCP Server"
4. Copy and paste the following JSON configuration:

```json
{
  "mcpServers": {
    "agent-controller": {
      "name": "Agent API Controller",
      "description": "MCP server for interacting with AI agents through the Agent API",
      "command": "python",
      "args": ["-m", "mcp-agentapi"],
      "cwd": "/path/to/agent/mcp-agentapi",
      "env": {
        "TRANSPORT": "stdio"
      }
    }
  }
}
```

5. Click "Save"
6. Select the server from the model selection dropdown

### 1.4 Web Clients (SSE Transport)

For web clients that support SSE transport, use the following configuration:

```json
{
  "mcpServers": {
    "agent-controller-sse": {
      "name": "Agent API Controller (SSE)",
      "description": "MCP server for interacting with AI agents through the Agent API using SSE transport",
      "command": "python",
      "args": ["-m", "mcp-agentapi", "--transport", "sse", "--host", "127.0.0.1", "--port", "8080"],
      "env": {}
    }
  }
}
```

## 2. Integrating with AI Agents

### 2.1 Goose

1. Install Goose:

```bash
curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh | CONFIGURE=false bash
```

2. Set up your Google API key:

```bash
export GOOGLE_API_KEY="your-google-api-key"
```

3. Configure the MCP server to use Goose:

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

### 2.2 Aider

1. Install Aider:

```bash
pip install aider-chat
```

2. Set up your OpenAI API key:

```bash
export OPENAI_API_KEY="your-openai-api-key"
```

3. Configure the MCP server to use Aider:

```json
{
  "agent_api_url": "http://localhost:3284",
  "auto_start_agent": true,
  "agent_type": "aider",
  "server": {
    "transport": "stdio",
    "host": "0.0.0.0",
    "port": 8080
  },
  "debug": false
}
```

### 2.3 Claude

1. Install Claude:

```bash
npm install -g @anthropic-ai/claude-code
```

2. Set up your Anthropic API key:

```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

3. Configure the MCP server to use Claude:

```json
{
  "agent_api_url": "http://localhost:3284",
  "auto_start_agent": true,
  "agent_type": "claude",
  "server": {
    "transport": "stdio",
    "host": "0.0.0.0",
    "port": 8080
  },
  "debug": false
}
```

### 2.4 Codex

1. Install Codex:

```bash
npm install -g @openai/codex
```

2. Set up your OpenAI API key:

```bash
export OPENAI_API_KEY="your-openai-api-key"
```

3. Configure the MCP server to use Codex:

```json
{
  "agent_api_url": "http://localhost:3284",
  "auto_start_agent": true,
  "agent_type": "codex",
  "server": {
    "transport": "stdio",
    "host": "0.0.0.0",
    "port": 8080
  },
  "debug": false
}
```

## 3. Using Multiple Agents

### 3.1 Configuration for Multiple Agents

To use multiple agents with a single MCP server, use the following configuration:

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

### 3.2 Switching Between Agents

To switch between agents, use the `switch_agent` tool:

```
Tool: switch_agent
Arguments: {"agent_type": "goose"}
```

### 3.3 Listing Available Agents

To list all available agents, use the `list_available_agents` tool:

```
Tool: list_available_agents
Arguments: {}
```

### 3.4 Getting the Current Agent

To get the current active agent, use the `get_agent_type` tool:

```
Tool: get_agent_type
Arguments: {}
```

## 4. Troubleshooting

### 4.1 Agent Not Detected

If an agent is not detected:

1. Ensure the agent is installed correctly
2. Check if the agent is in your PATH
3. Run `./bin/agentapi-mcp list` to see if the agent is detected

### 4.2 Cannot Switch Agents

If you cannot switch agents:

1. Check if the Agent API is running (`http://localhost:3284` by default)
2. Ensure you have the necessary API keys set
3. Try stopping the current agent first: `./bin/agentapi-mcp stop <current_agent>`

### 4.3 API Key Issues

If you have API key issues:

1. Verify that the API keys are set correctly in your environment
2. For Goose: `GOOGLE_API_KEY`
3. For Aider: `OPENAI_API_KEY`
4. For Claude: `ANTHROPIC_API_KEY`
5. For Codex: `OPENAI_API_KEY`

### 4.4 Agent API Not Starting

If the Agent API is not starting:

1. Check if the Agent API is already running on port 3284
2. Try starting it manually: `agentapi server`
3. Check for error messages in the logs

### 4.5 MCP Client Not Connecting

If the MCP client is not connecting:

1. Verify the JSON configuration is correct
2. Ensure the paths to the MCP server are correct
3. Check if the transport type (stdio/SSE) is supported by your client
