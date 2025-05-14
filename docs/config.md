# Configuration

The Configuration module is responsible for loading, validating, and managing configuration settings for the MCP server. It supports loading configuration from environment variables, files, and command-line arguments.

## Overview

The Configuration module is implemented in the `src/config.py` file. It provides functionality for:

- Loading configuration from environment variables
- Loading configuration from files
- Validating configuration settings
- Managing API keys
- Providing default values

## Configuration Classes

### `Config`

The main configuration class that holds all settings for the MCP server.

```python
class Config:
    """
    Configuration for the MCP server.

    Attributes:
        agent_api_url: URL of the Agent API server
        auto_start_agent: Whether to automatically start the Agent API server
        agent_type: Type of the agent to use
        server: Server configuration
        debug: Whether to enable debug logging
        config_version: Version of the configuration format
        config_sources: List of sources where the configuration was loaded from
        validated: Whether the configuration has been validated
        agent_configs: Dictionary of agent-specific configurations
    """
    # Implementation details...
```

### `ServerConfig`

Configuration for the MCP server transport, host, and port.

```python
class ServerConfig:
    """
    Configuration for the MCP server transport, host, and port.

    Attributes:
        transport: Transport type (stdio, sse)
        host: Host to bind to when using SSE transport
        port: Port to listen on when using SSE transport
    """
    # Implementation details...
```

### `AgentConfig`

Configuration for a specific agent, including API key settings.

```python
class AgentConfig:
    """
    Configuration for a specific agent.

    Attributes:
        api_key_env: Name of the environment variable for the API key
        api_key_provider: Name of the API provider (e.g., openai, anthropic)
        api_key_required: Whether an API key is required for this agent
        api_key: The API key value
        api_key_validated: Whether the API key has been validated
    """
    # Implementation details...
```

## Enums

### `TransportType`

Enum for the transport type.

```python
class TransportType(str, Enum):
    """Transport type for the MCP server."""
    STDIO = "stdio"
    SSE = "sse"
```

### `AgentType`

Enum for the agent type.

```python
class AgentType(str, Enum):
    """Type of agent."""
    GOOSE = "goose"
    AIDER = "aider"
    CLAUDE = "claude"
    CODEX = "codex"
    CUSTOM = "custom"
```

## Usage

### Loading Configuration

```python
from src.config import load_config, load_from_env, load_from_file

# Load configuration from environment variables
config = load_from_env()

# Load configuration from a file
config = load_from_file("/path/to/config.json")

# Load configuration from multiple sources
config = load_config(
    env=True,
    file="/path/to/config.json",
    args={"agent_type": "goose", "debug": True}
)
```

### Saving Configuration

```python
from src.config import save_config

# Save configuration to a file
success = save_config(config, "/path/to/config.json")
```

### Accessing Configuration

```python
# Access configuration properties
print(f"Agent API URL: {config.agent_api_url}")
print(f"Agent type: {config.agent_type}")
print(f"Transport: {config.server.transport}")
print(f"Host: {config.server.host}")
print(f"Port: {config.server.port}")
print(f"Debug: {config.debug}")
```

### Managing API Keys

```python
# Load API keys from environment variables
results = config.load_api_keys(validate=True)
for agent_type, success in results.items():
    print(f"API key for {agent_type}: {'Valid' if success else 'Invalid'}")

# Get agent-specific configuration
agent_config = config.get_agent_config(AgentType.GOOSE)
print(f"API key environment variable: {agent_config.api_key_env}")
print(f"API key provider: {agent_config.api_key_provider}")
print(f"API key required: {agent_config.api_key_required}")
print(f"API key: {agent_config.mask_api_key()}")
print(f"API key validated: {agent_config.api_key_validated}")
```

## Implementation Details

### Loading from Environment Variables

The Configuration module loads settings from environment variables:

```python
async def load_from_env() -> Config:
    """
    Load configuration from environment variables.

    Returns:
        Config object with settings from environment variables
    """
    config = Config()
    
    # Load server configuration
    transport_str = os.environ.get("TRANSPORT", "").lower()
    if transport_str:
        try:
            config.server.transport = TransportType(transport_str)
        except ValueError:
            logger.warning(f"Invalid transport type: {transport_str}")
    
    host = os.environ.get("HOST")
    if host:
        config.server.host = host
    
    port_str = os.environ.get("PORT")
    if port_str:
        try:
            config.server.port = int(port_str)
        except ValueError:
            logger.warning(f"Invalid port: {port_str}")
    
    # Load agent configuration
    agent_api_url = os.environ.get("AGENT_API_URL")
    if agent_api_url:
        config.agent_api_url = agent_api_url
    
    auto_start_agent_str = os.environ.get("AUTO_START_AGENT", "").lower()
    if auto_start_agent_str in ("true", "1", "yes"):
        config.auto_start_agent = True
    elif auto_start_agent_str in ("false", "0", "no"):
        config.auto_start_agent = False
    
    agent_type_str = os.environ.get("AGENT_TYPE", "").lower()
    if agent_type_str:
        try:
            config.agent_type = AgentType(agent_type_str)
        except ValueError:
            logger.warning(f"Invalid agent type: {agent_type_str}")
    
    debug_str = os.environ.get("DEBUG", "").lower()
    if debug_str in ("true", "1", "yes"):
        config.debug = True
    elif debug_str in ("false", "0", "no"):
        config.debug = False
    
    # Add environment as a config source
    config.config_sources.append("environment")
    
    # Load API keys
    await config.load_api_keys(validate=False)
    
    return config
```

### Loading from Files

The Configuration module loads settings from JSON files:

```python
async def load_from_file(file_path: str) -> Config:
    """
    Load configuration from a file.

    Args:
        file_path: Path to the configuration file

    Returns:
        Config object with settings from the file

    Raises:
        ConfigurationError: If the file cannot be loaded or parsed
    """
    config = Config()
    
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        
        # Load server configuration
        server_data = data.get("server", {})
        transport_str = server_data.get("transport", "").lower()
        if transport_str:
            try:
                config.server.transport = TransportType(transport_str)
            except ValueError:
                logger.warning(f"Invalid transport type in file: {transport_str}")
        
        host = server_data.get("host")
        if host:
            config.server.host = host
        
        port = server_data.get("port")
        if port is not None:
            config.server.port = port
        
        # Load agent configuration
        agent_api_url = data.get("agent_api_url")
        if agent_api_url:
            config.agent_api_url = agent_api_url
        
        auto_start_agent = data.get("auto_start_agent")
        if auto_start_agent is not None:
            config.auto_start_agent = bool(auto_start_agent)
        
        agent_type_str = data.get("agent_type", "").lower()
        if agent_type_str:
            try:
                config.agent_type = AgentType(agent_type_str)
            except ValueError:
                logger.warning(f"Invalid agent type in file: {agent_type_str}")
        
        debug = data.get("debug")
        if debug is not None:
            config.debug = bool(debug)
        
        # Add file as a config source
        config.config_sources.append(f"file:{file_path}")
        
        return config
    except (json.JSONDecodeError, IOError) as e:
        raise ConfigurationError(f"Error loading configuration from file: {e}")
```

### Validating API Keys

The Configuration module validates API keys:

```python
def validate_api_key(self) -> bool:
    """
    Validate the API key.

    Returns:
        True if the API key is valid or not required, False otherwise

    Raises:
        APIKeyError: If the API key is required but not set or invalid
    """
    if not self.api_key_required:
        return True
    
    if not self.api_key:
        raise APIKeyError(
            f"API key for {self.api_key_provider} is required but not set. "
            f"Please set the {self.api_key_env} environment variable."
        )
    
    # Validate the API key format
    if self.api_key_provider == "openai" and not self.api_key.startswith("sk-"):
        raise APIKeyError(
            f"Invalid API key format for {self.api_key_provider}. "
            f"OpenAI API keys should start with 'sk-'."
        )
    
    # Mark the API key as validated
    self.api_key_validated = True
    
    return True
```
