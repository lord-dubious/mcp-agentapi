# Agent Manager

The Agent Manager is responsible for detecting, installing, starting, stopping, and monitoring agents. It provides a unified interface for managing different types of agents.

## Overview

The Agent Manager is implemented in the `src/agent_manager.py` module. It provides functionality for:

- Detecting available agents
- Installing agents
- Starting and stopping agents
- Monitoring agent health
- Managing agent processes

## Agent Types

The Agent Manager supports the following agent types:

- **Goose**: Google's AI assistant
- **Aider**: A coding assistant that works with multiple AI providers
- **Claude**: Anthropic's AI assistant
- **Codex**: OpenAI's coding assistant
- **Custom**: Custom agents

## Usage

### Creating an Agent Manager

```python
from src.agent_manager import AgentManager
from src.config import Config
from src.resource_manager import ResourceManager

# Create a configuration
config = Config()

# Create a resource manager
resource_manager = ResourceManager()

# Create an agent manager
agent_manager = AgentManager(config, resource_manager)
```

### Detecting Agents

```python
# Detect all available agents
agents = await agent_manager.detect_agents()
for agent_type, agent_info in agents.items():
    print(f"Agent: {agent_type.value}")
    print(f"  Installed: {agent_info.install_status.value}")
    print(f"  Running: {agent_info.running_status.value}")
    print(f"  Command: {agent_info.command}")
    print(f"  Version: {agent_info.version}")
    print(f"  API Key Set: {agent_info.api_key_set}")
    print(f"  API Key Valid: {agent_info.api_key_valid}")
```

### Installing Agents

```python
# Install the Agent API
success = await agent_manager.install_agent_api()
print(f"Agent API installed: {success}")

# Install a specific agent
success = await agent_manager.install_agent(AgentType.GOOSE)
print(f"Goose agent installed: {success}")
```

### Starting and Stopping Agents

```python
# Start an agent
process = await agent_manager.start_agent(AgentType.GOOSE)
print(f"Goose agent started with PID: {process.pid}")

# Stop an agent
success = await agent_manager.stop_agent(AgentType.GOOSE)
print(f"Goose agent stopped: {success}")

# Restart an agent
process = await agent_manager.restart_agent(AgentType.GOOSE)
print(f"Goose agent restarted with PID: {process.pid}")
```

### Monitoring Agents

```python
# Monitor an agent with auto-reconnect
await agent_manager.monitor_agent(AgentType.GOOSE, auto_reconnect=True)
```

### Switching Agents

```python
# Switch to a different agent
process = await agent_manager.switch_agent(AgentType.AIDER)
print(f"Switched to Aider agent with PID: {process.pid}")
```

## Agent Information

The Agent Manager tracks information about each agent using the `AgentInfo` class:

```python
@dataclass
class AgentInfo:
    """
    Information about an agent.

    Attributes:
        agent_type: Type of the agent
        install_status: Installation status of the agent
        running_status: Running status of the agent
        process: Process object for the running agent
        command: Command used to start the agent
        version: Version of the agent
        api_key_set: Whether an API key is set for the agent
        api_key_valid: Whether the API key is valid
    """
    agent_type: AgentType
    install_status: AgentInstallStatus = AgentInstallStatus.UNKNOWN
    running_status: AgentRunningStatus = AgentRunningStatus.UNKNOWN
    process: Optional[subprocess.Popen] = None
    command: Optional[str] = None
    version: Optional[str] = None
    api_key_set: bool = False
    api_key_valid: bool = False
```

## Agent Status

The Agent Manager tracks the installation and running status of each agent using enums:

```python
class AgentInstallStatus(str, Enum):
    """Installation status of an agent."""
    UNKNOWN = "unknown"
    INSTALLED = "installed"
    NOT_INSTALLED = "not_installed"
    INSTALLING = "installing"
    INSTALL_FAILED = "install_failed"

class AgentRunningStatus(str, Enum):
    """Running status of an agent."""
    UNKNOWN = "unknown"
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"
    START_FAILED = "start_failed"
    STOP_FAILED = "stop_failed"
```

## Implementation Details

### Agent Detection

The Agent Manager uses multiple methods to detect agents:

1. Checking if the agent command exists
2. Running the agent with a version flag
3. Checking if the agent is already running
4. Validating the agent's API key

```python
async def _detect_agent(self, agent_type: AgentType) -> None:
    """
    Detect if a specific agent is installed and running.

    Args:
        agent_type: The agent type to detect
    """
    # Implementation details...
```

### Agent Installation

The Agent Manager provides methods for installing agents:

```python
async def install_agent(self, agent_type: AgentType) -> bool:
    """
    Install a specific agent.

    Args:
        agent_type: The agent type to install

    Returns:
        True if the agent was installed successfully, False otherwise
    """
    # Implementation details...
```

### Agent Lifecycle Management

The Agent Manager provides methods for starting, stopping, and monitoring agents:

```python
async def start_agent(self, agent_type: AgentType) -> subprocess.Popen:
    """
    Start a specific agent.

    Args:
        agent_type: The agent type to start

    Returns:
        The process object for the running agent

    Raises:
        AgentStartError: If the agent could not be started
    """
    # Implementation details...

async def stop_agent(self, agent_type: AgentType) -> bool:
    """
    Stop a running agent.

    Args:
        agent_type: The agent type to stop

    Returns:
        True if the agent was stopped successfully, False otherwise
    """
    # Implementation details...

async def monitor_agent(self, agent_type: AgentType, auto_reconnect: bool = False) -> None:
    """
    Monitor an agent's status and optionally reconnect it if it crashes.

    Args:
        agent_type: The agent type to monitor
        auto_reconnect: Whether to automatically reconnect the agent if it crashes
    """
    # Implementation details...
```

## Error Handling

The Agent Manager provides detailed error handling with custom exceptions:

```python
class AgentDetectionError(Exception):
    """Error detecting an agent."""
    pass

class AgentStartError(Exception):
    """Error starting an agent."""
    pass

class AgentStopError(Exception):
    """Error stopping an agent."""
    pass
```

## Advanced Features

### Process Management

The Agent Manager uses the Resource Manager to track and clean up agent processes:

```python
async def stop_process(self, process: subprocess.Popen, timeout: float = 5.0) -> None:
    """
    Stop a process and clean up its resources.

    Args:
        process: The process to stop
        timeout: Timeout in seconds for graceful termination
    """
    # Implementation details...
```

### API Key Validation

The Agent Manager validates API keys for agents that require them:

```python
async def _validate_api_key(self, agent_type: AgentType) -> bool:
    """
    Validate the API key for a specific agent.

    Args:
        agent_type: The agent type to validate

    Returns:
        True if the API key is valid, False otherwise
    """
    # Implementation details...
```

### Agent-Specific Configuration

The Agent Manager provides agent-specific configuration for each agent type:

```python
def _get_agent_command(self, agent_type: AgentType) -> List[str]:
    """
    Get the command to start a specific agent.

    Args:
        agent_type: The agent type

    Returns:
        The command to start the agent as a list of strings
    """
    # Implementation details...
```
