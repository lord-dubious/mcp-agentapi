# MCP Tools

The MCP server provides a set of tools for interacting with agents through the Machine Coding Protocol (MCP). These tools allow MCP clients to control agents and interact with the Agent API.

## Overview

The MCP tools are implemented in the `server.py` file. They provide functionality for:

- Getting agent type and status
- Listing available agents
- Installing, starting, stopping, and restarting agents
- Sending messages to agents
- Getting messages from agents
- Getting screen content from agents
- Checking health status

## Tool Categories

### Agent Management

- `get_agent_type`: Get the type of the current agent
- `list_available_agents`: List all available agents
- `install_agent`: Install an agent
- `start_agent`: Start an agent
- `stop_agent`: Stop an agent
- `restart_agent`: Restart an agent

### Agent API Interaction

- `get_status`: Get the current status of the agent
- `check_health`: Check the health of the MCP server and its components
- `get_messages`: Get all messages in the conversation history
- `send_message`: Send a message to the agent
- `get_screen`: Get the current screen content from the agent

## Tool Descriptions

### Agent Management Tools

#### `get_agent_type`

Get the type of the current agent.

```python
async def get_agent_type(context: Context) -> str:
    """
    Get the type of the current agent.

    Args:
        context: MCP context

    Returns:
        The agent type as a string
    """
    # Implementation details...
```

#### `list_available_agents`

List all available agents.

```python
async def list_available_agents(context: Context) -> Dict[str, Any]:
    """
    List all available agents.

    Args:
        context: MCP context

    Returns:
        Dictionary with agent information
    """
    # Implementation details...
```

#### `install_agent`

Install an agent.

```python
async def install_agent(context: Context, agent_type: str) -> str:
    """
    Install an agent.

    Args:
        context: MCP context
        agent_type: Type of the agent to install

    Returns:
        Success or error message
    """
    # Implementation details...
```

#### `start_agent`

Start an agent.

```python
async def start_agent(context: Context, agent_type: str) -> str:
    """
    Start an agent.

    Args:
        context: MCP context
        agent_type: Type of the agent to start

    Returns:
        Success or error message
    """
    # Implementation details...
```

#### `stop_agent`

Stop an agent.

```python
async def stop_agent(context: Context, agent_type: str) -> str:
    """
    Stop an agent.

    Args:
        context: MCP context
        agent_type: Type of the agent to stop

    Returns:
        Success or error message
    """
    # Implementation details...
```

#### `restart_agent`

Restart an agent.

```python
async def restart_agent(context: Context, agent_type: str) -> str:
    """
    Restart an agent.

    Args:
        context: MCP context
        agent_type: Type of the agent to restart

    Returns:
        Success or error message
    """
    # Implementation details...
```

### Agent API Interaction Tools

#### `get_status`

Get the current status of the agent.

```python
async def get_status(context: Context) -> str:
    """
    Get the current status of the agent.

    Args:
        context: MCP context

    Returns:
        The agent status as a string
    """
    # Implementation details...
```

#### `check_health`

Check the health of the MCP server and its components.

```python
async def check_health(context: Context) -> Dict[str, Any]:
    """
    Check the health of the MCP server and its components.

    Args:
        context: MCP context

    Returns:
        Dictionary with health status information
    """
    # Implementation details...
```

#### `get_messages`

Get all messages in the conversation history.

```python
async def get_messages(context: Context) -> Dict[str, Any]:
    """
    Get all messages in the conversation history.

    Args:
        context: MCP context

    Returns:
        Dictionary with messages
    """
    # Implementation details...
```

#### `send_message`

Send a message to the agent.

```python
async def send_message(context: Context, content: str, type: str = "user") -> Dict[str, Any]:
    """
    Send a message to the agent.

    Args:
        context: MCP context
        content: Message content
        type: Message type (user or raw)

    Returns:
        Dictionary with result
    """
    # Implementation details...
```

#### `get_screen`

Get the current screen content from the agent.

```python
async def get_screen(context: Context) -> Dict[str, Any]:
    """
    Get the current screen content from the agent.

    Args:
        context: MCP context

    Returns:
        Dictionary with screen content
    """
    # Implementation details...
```

## Resources

### `get_agent_info`

Get information about the agent.

```python
async def get_agent_info(context: Context) -> str:
    """
    Get information about the agent.

    Args:
        context: MCP context

    Returns:
        JSON string with agent information
    """
    # Implementation details...
```

### `get_openapi_schema`

Get the OpenAPI schema for the Agent API.

```python
async def get_openapi_schema(context: Context) -> str:
    """
    Get the OpenAPI schema for the Agent API.

    Args:
        context: MCP context

    Returns:
        JSON string with OpenAPI schema
    """
    # Implementation details...
```

## Prompts

### `agent_prompt`

Prompt for the agent.

```python
def agent_prompt(message: str) -> str:
    """
    Prompt for the agent.

    Args:
        message: Message to include in the prompt

    Returns:
        Prompt string
    """
    # Implementation details...
```

### `debug_error`

Prompt for debugging errors.

```python
def debug_error(error_message: str) -> List[Dict[str, str]]:
    """
    Prompt for debugging errors.

    Args:
        error_message: Error message to debug

    Returns:
        List of messages for the conversation
    """
    # Implementation details...
```

## Usage Examples

### Agent Management

```python
# Get the agent type
agent_type = await client.call("get_agent_type")
print(f"Agent type: {agent_type}")

# List available agents
agents = await client.call("list_available_agents")
print(f"Available agents: {agents}")

# Install an agent
result = await client.call("install_agent", {"agent_type": "goose"})
print(f"Installation result: {result}")

# Start an agent
result = await client.call("start_agent", {"agent_type": "goose"})
print(f"Start result: {result}")

# Stop an agent
result = await client.call("stop_agent", {"agent_type": "goose"})
print(f"Stop result: {result}")

# Restart an agent
result = await client.call("restart_agent", {"agent_type": "goose"})
print(f"Restart result: {result}")
```

### Agent API Interaction

```python
# Get the agent status
status = await client.call("get_status")
print(f"Agent status: {status}")

# Check health
health = await client.call("check_health")
print(f"Health status: {health}")

# Get messages
messages = await client.call("get_messages")
print(f"Messages: {messages}")

# Send a message
result = await client.call("send_message", {"content": "Hello, agent!", "type": "user"})
print(f"Send result: {result}")

# Get screen content
screen = await client.call("get_screen")
print(f"Screen content: {screen}")
```
