#!/usr/bin/env python3
"""
Configuration management for the MCP server for Agent API.

This module handles loading, validating, and providing access to configuration
values from different sources (environment variables, configuration files).
It includes secure API key handling and validation.
"""

import json
import logging
import os
import re
import secrets
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union, Callable

from .models import AgentType
from .exceptions import ConfigurationError, APIKeyError

# Configure logging
logger = logging.getLogger("mcp-server-agentapi.config")

# Constants
DEFAULT_AGENT_API_URL = "http://localhost:3284"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8080
CONFIG_FILE_NAME = "mcp-server-agentapi.json"


class TransportType(str, Enum):
    """Transport types for the MCP server."""
    STDIO = "stdio"
    SSE = "sse"


# API key validation patterns
API_KEY_PATTERNS = {
    "openai": re.compile(r'^sk-[a-zA-Z0-9]{32,}$'),
    "anthropic": re.compile(r'^sk-ant-[a-zA-Z0-9]{32,}$'),
    "google": re.compile(r'^AIza[a-zA-Z0-9_-]{35}$'),
    "deepseek": re.compile(r'^sk-[a-zA-Z0-9]{32,}$'),
    "generic": re.compile(r'^[a-zA-Z0-9_-]{16,}$')
}

# API key providers
API_KEY_PROVIDERS = {
    "OPENAI_API_KEY": "openai",
    "ANTHROPIC_API_KEY": "anthropic",
    "GOOGLE_API_KEY": "google",
    "DEEPSEEK_API_KEY": "deepseek"
}


@dataclass
class AgentConfig:
    """
    Configuration for a specific agent type.

    Attributes:
        api_key_env: Name of the environment variable for the API key
        api_key: The API key value (loaded from environment)
        model: Default model to use
        additional_args: Additional command-line arguments for the agent
        api_key_provider: The provider of the API key (e.g., openai, anthropic)
        api_key_required: Whether an API key is required for this agent
        api_key_validated: Whether the API key has been validated
    """
    api_key_env: str
    api_key: Optional[str] = None
    model: Optional[str] = None
    additional_args: Dict[str, str] = field(default_factory=dict)
    api_key_provider: Optional[str] = None
    api_key_required: bool = True
    api_key_validated: bool = False

    def __post_init__(self):
        """Initialize API key provider based on environment variable name."""
        if self.api_key_env in API_KEY_PROVIDERS:
            self.api_key_provider = API_KEY_PROVIDERS[self.api_key_env]
        elif self.api_key_env:
            self.api_key_provider = "generic"
        else:
            self.api_key_required = False
            self.api_key_provider = None

    def validate_api_key(self) -> bool:
        """
        Validate the API key format based on the provider.

        Returns:
            True if the API key is valid or not required, False otherwise

        Raises:
            APIKeyError: If the API key is required but invalid
        """
        # If API key is not required, return True
        if not self.api_key_required:
            return True

        # If API key is required but not set, raise an error
        if not self.api_key:
            if self.api_key_env:
                error_msg = f"API key is required but not set in environment variable {self.api_key_env}"
            else:
                error_msg = "API key is required but not set"
            logger.error(error_msg)
            raise APIKeyError(error_msg)

        # Validate API key format based on provider
        if self.api_key_provider and self.api_key_provider in API_KEY_PATTERNS:
            pattern = API_KEY_PATTERNS[self.api_key_provider]
            if not pattern.match(self.api_key):
                error_msg = f"Invalid API key format for provider {self.api_key_provider}"
                logger.error(error_msg)
                raise APIKeyError(error_msg)

        # Mark as validated
        self.api_key_validated = True
        return True

    def mask_api_key(self) -> str:
        """
        Return a masked version of the API key for logging.

        Returns:
            A masked version of the API key
        """
        if not self.api_key:
            return "<not set>"

        # Show only first 4 and last 4 characters
        if len(self.api_key) > 8:
            return f"{self.api_key[:4]}...{self.api_key[-4:]}"
        else:
            return "****"  # For very short keys, just mask everything


@dataclass
class ServerConfig:
    """
    Server configuration.

    Attributes:
        transport: Transport type (stdio or sse)
        host: Host to bind to when using SSE transport
        port: Port to listen on when using SSE transport
    """
    transport: TransportType = TransportType.STDIO
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT


@dataclass
class Config:
    """
    Main configuration class.

    Attributes:
        agent_api_url: URL of the Agent API server
        auto_start_agent: Whether to automatically start the Agent API server
        agent_type: Type of the agent to use
        server: Server configuration
        agent_configs: Agent-specific configurations
        debug: Enable debug logging
        config_version: Version of the configuration format
        config_sources: List of sources where configuration was loaded from
        validated: Whether the configuration has been validated
    """
    agent_api_url: str = DEFAULT_AGENT_API_URL
    auto_start_agent: bool = False
    agent_type: Optional[AgentType] = None
    server: ServerConfig = field(default_factory=ServerConfig)
    agent_configs: Dict[AgentType, AgentConfig] = field(default_factory=dict)
    debug: bool = False
    config_version: str = "1.0"
    config_sources: List[str] = field(default_factory=list)
    validated: bool = False

    def __post_init__(self):
        """Initialize agent configurations if not provided."""
        if not self.agent_configs:
            self._init_agent_configs()

        # Add default config source
        if not self.config_sources:
            self.config_sources.append("defaults")

    def _init_agent_configs(self):
        """Initialize default agent configurations."""
        self.agent_configs = {
            AgentType.GOOSE: AgentConfig(
                api_key_env="GOOGLE_API_KEY",
                model=os.environ.get("GOOSE_MODEL", None),
                additional_args={
                    "config_file": os.environ.get("GOOSE_CONFIG_FILE", None),
                }
            ),
            AgentType.AIDER: AgentConfig(
                api_key_env="OPENAI_API_KEY",
                model=os.environ.get("AIDER_MODEL", "deepseek"),
                additional_args={
                    "api_key_param": "--api-key",
                    "config_file": os.environ.get("AIDER_CONFIG_FILE", "~/.aider.conf.yml"),
                }
            ),
            AgentType.CLAUDE: AgentConfig(
                api_key_env="ANTHROPIC_API_KEY",
                model=os.environ.get("CLAUDE_MODEL", "claude-3-7-sonnet-20250219"),
                additional_args={
                    "config_file": os.environ.get("CLAUDE_CONFIG_FILE", None),
                }
            ),
            AgentType.CODEX: AgentConfig(
                api_key_env="OPENAI_API_KEY",
                model=os.environ.get("CODEX_MODEL", "o4-mini"),
                additional_args={
                    "config_file": os.environ.get("CODEX_CONFIG_FILE", "~/.codex/config.json"),
                    "provider": os.environ.get("CODEX_PROVIDER", "openai"),
                }
            ),
            AgentType.CUSTOM: AgentConfig(
                api_key_env="",
                model=None,
                api_key_required=False,
            ),
        }

    def get_agent_config(self, agent_type: AgentType) -> AgentConfig:
        """
        Get the configuration for a specific agent type.

        Args:
            agent_type: The agent type

        Returns:
            The agent configuration

        Raises:
            ConfigurationError: If the agent type is not supported
        """
        if agent_type not in self.agent_configs:
            logger.warning(f"Unsupported agent type: {agent_type.value}, using CUSTOM")
            return self.agent_configs[AgentType.CUSTOM]

        return self.agent_configs[agent_type]

    def load_api_keys(self, validate: bool = True) -> Dict[AgentType, bool]:
        """
        Load API keys from environment variables and optionally validate them.

        Args:
            validate: Whether to validate API keys after loading

        Returns:
            Dictionary mapping agent types to API key validation status

        Raises:
            APIKeyError: If validation is enabled and an API key is invalid
        """
        results = {}

        for agent_type, agent_config in self.agent_configs.items():
            if agent_config.api_key_env:
                # Get API key from environment
                api_key = os.environ.get(agent_config.api_key_env)

                # Check if the API key has changed
                if api_key != agent_config.api_key:
                    agent_config.api_key = api_key
                    agent_config.api_key_validated = False

                # Special handling for specific agent types to check alternative environment variables
                if not agent_config.api_key:
                    if agent_type == AgentType.GOOSE and os.environ.get("GOOGLE_API_KEY"):
                        agent_config.api_key = os.environ.get("GOOGLE_API_KEY")
                        logger.info(f"Using GOOGLE_API_KEY for {agent_type.value}")
                    elif agent_type == AgentType.AIDER and os.environ.get("OPENAI_API_KEY"):
                        agent_config.api_key = os.environ.get("OPENAI_API_KEY")
                        logger.info(f"Using OPENAI_API_KEY for {agent_type.value}")
                    elif agent_type == AgentType.CLAUDE and os.environ.get("ANTHROPIC_API_KEY"):
                        agent_config.api_key = os.environ.get("ANTHROPIC_API_KEY")
                        logger.info(f"Using ANTHROPIC_API_KEY for {agent_type.value}")
                    elif agent_type == AgentType.CODEX and os.environ.get("OPENAI_API_KEY"):
                        agent_config.api_key = os.environ.get("OPENAI_API_KEY")
                        logger.info(f"Using OPENAI_API_KEY for {agent_type.value}")

                if agent_config.api_key:
                    logger.debug(f"Loaded API key for {agent_type.value} from {agent_config.api_key_env}: {agent_config.mask_api_key()}")
                else:
                    logger.debug(f"No API key found for {agent_type.value} in {agent_config.api_key_env}")

                # Validate API key if requested
                if validate and agent_config.api_key_required:
                    try:
                        valid = agent_config.validate_api_key()
                        results[agent_type] = valid
                    except APIKeyError as e:
                        results[agent_type] = False
                        if agent_type == self.agent_type:
                            # Re-raise the error if this is the selected agent type
                            raise
                        else:
                            # Just log the error for other agent types
                            logger.warning(f"API key validation failed for {agent_type.value}: {e}")
                else:
                    # If validation is disabled, just check if the key is set
                    results[agent_type] = bool(agent_config.api_key) or not agent_config.api_key_required
            else:
                # No API key environment variable specified
                results[agent_type] = not agent_config.api_key_required

        return results

    def validate(self) -> bool:
        """
        Validate the entire configuration.

        Returns:
            True if the configuration is valid, False otherwise

        Raises:
            ConfigurationError: If the configuration is invalid
        """
        # Validate agent API URL
        if not self.agent_api_url:
            raise ConfigurationError("Agent API URL is required")

        # Validate server configuration
        if self.server.transport == TransportType.SSE:
            if not self.server.host:
                raise ConfigurationError("Host is required for SSE transport")
            if not isinstance(self.server.port, int) or self.server.port <= 0:
                raise ConfigurationError(f"Invalid port: {self.server.port}")

        # Validate agent type if specified
        if self.agent_type and self.agent_type not in self.agent_configs:
            raise ConfigurationError(f"Unsupported agent type: {self.agent_type.value}")

        # Validate API keys for all agents
        self.load_api_keys(validate=True)

        # Mark as validated
        self.validated = True
        return True

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the configuration to a dictionary.

        Returns:
            A dictionary representation of the configuration
        """
        agent_configs_dict = {}
        for agent_type, agent_config in self.agent_configs.items():
            agent_configs_dict[agent_type.value] = {
                "api_key_env": agent_config.api_key_env,
                "api_key_set": bool(agent_config.api_key),
                "api_key_validated": agent_config.api_key_validated,
                "model": agent_config.model,
                "api_key_required": agent_config.api_key_required,
            }

        return {
            "agent_api_url": self.agent_api_url,
            "auto_start_agent": self.auto_start_agent,
            "agent_type": self.agent_type.value if self.agent_type else None,
            "server": {
                "transport": self.server.transport.value,
                "host": self.server.host,
                "port": self.server.port,
            },
            "debug": self.debug,
            "config_version": self.config_version,
            "config_sources": self.config_sources,
            "validated": self.validated,
            "agent_configs": agent_configs_dict,
        }


def load_from_env() -> Config:
    """
    Load configuration from environment variables.

    Returns:
        A Config object with values from environment variables

    Raises:
        ConfigurationError: If the configuration is invalid
    """
    # Create default config
    config = Config()
    config.config_sources.append("environment")

    # Load server configuration
    transport_str = os.environ.get("TRANSPORT", "stdio").lower()
    try:
        config.server.transport = TransportType(transport_str)
    except ValueError:
        logger.warning(f"Invalid transport type: {transport_str}, using stdio")
        config.server.transport = TransportType.STDIO

    try:
        # Load host and port with validation
        config.server.host = os.environ.get("HOST", DEFAULT_HOST)
        port_str = os.environ.get("PORT")
        if port_str:
            try:
                port = int(port_str)
                if port <= 0 or port > 65535:
                    raise ValueError(f"Port must be between 1 and 65535, got {port}")
                config.server.port = port
            except ValueError as e:
                logger.warning(f"Invalid port: {port_str}, using default {DEFAULT_PORT}: {e}")
                config.server.port = DEFAULT_PORT
        else:
            config.server.port = DEFAULT_PORT

        # Load agent configuration
        config.agent_api_url = os.environ.get("AGENT_API_URL", DEFAULT_AGENT_API_URL)
        config.auto_start_agent = os.environ.get("AUTO_START_AGENT", "").lower() in ("true", "1", "yes")

        agent_type_str = os.environ.get("AGENT_TYPE")
        if agent_type_str:
            try:
                config.agent_type = AgentType(agent_type_str.lower())
            except ValueError:
                logger.warning(f"Invalid agent type: {agent_type_str}, using default")
                config.agent_type = None

        # Load debug flag
        config.debug = os.environ.get("DEBUG", "").lower() in ("true", "1", "yes")

        # Load API keys (without validation at this stage)
        config.load_api_keys(validate=False)

        return config
    except Exception as e:
        logger.error(f"Error loading configuration from environment: {e}")
        raise ConfigurationError(f"Error loading configuration from environment: {e}") from e


def load_from_file(file_path: Union[str, Path]) -> Optional[Config]:
    """
    Load configuration from a JSON file.

    Args:
        file_path: Path to the configuration file

    Returns:
        A Config object with values from the file, or None if the file doesn't exist

    Raises:
        ConfigurationError: If the configuration file is invalid
    """
    path = Path(file_path)
    if not path.exists():
        logger.debug(f"Configuration file not found: {path}")
        return None

    try:
        with open(path, "r") as f:
            data = json.load(f)

        config = Config()
        config.config_sources.append(f"file:{path}")

        # Check configuration version
        if "config_version" in data:
            config.config_version = data["config_version"]

        # Load server configuration
        if "server" in data:
            server_data = data["server"]
            if "transport" in server_data:
                try:
                    config.server.transport = TransportType(server_data["transport"].lower())
                except ValueError:
                    logger.warning(f"Invalid transport type in config file: {server_data['transport']}, using default")
            if "host" in server_data:
                config.server.host = server_data["host"]
            if "port" in server_data:
                try:
                    port = int(server_data["port"])
                    if port <= 0 or port > 65535:
                        logger.warning(f"Invalid port in config file: {port}, using default {DEFAULT_PORT}")
                        config.server.port = DEFAULT_PORT
                    else:
                        config.server.port = port
                except (ValueError, TypeError):
                    logger.warning(f"Invalid port in config file: {server_data['port']}, using default {DEFAULT_PORT}")
                    config.server.port = DEFAULT_PORT

        # Load agent configuration
        if "agent_api_url" in data:
            config.agent_api_url = data["agent_api_url"]
        if "auto_start_agent" in data:
            config.auto_start_agent = bool(data["auto_start_agent"])
        if "agent_type" in data and data["agent_type"]:
            try:
                config.agent_type = AgentType(data["agent_type"].lower())
            except ValueError:
                logger.warning(f"Invalid agent type in config file: {data['agent_type']}, using default")

        # Load agent-specific configurations
        if "agent_configs" in data and isinstance(data["agent_configs"], dict):
            for agent_type_str, agent_config_data in data["agent_configs"].items():
                try:
                    agent_type = AgentType(agent_type_str.lower())
                    if agent_type in config.agent_configs:
                        # Update existing agent config
                        agent_config = config.agent_configs[agent_type]

                        # Update model if specified
                        if "model" in agent_config_data and agent_config_data["model"]:
                            agent_config.model = agent_config_data["model"]

                        # Update additional args if specified
                        if "additional_args" in agent_config_data and isinstance(agent_config_data["additional_args"], dict):
                            agent_config.additional_args.update(agent_config_data["additional_args"])

                        # Update API key environment variable if specified
                        if "api_key_env" in agent_config_data and agent_config_data["api_key_env"]:
                            agent_config.api_key_env = agent_config_data["api_key_env"]

                        # Update API key required flag if specified
                        if "api_key_required" in agent_config_data:
                            agent_config.api_key_required = bool(agent_config_data["api_key_required"])
                except ValueError:
                    logger.warning(f"Invalid agent type in config file: {agent_type_str}, skipping")

        # Load debug flag
        if "debug" in data:
            config.debug = bool(data["debug"])

        # Load API keys (without validation at this stage)
        config.load_api_keys(validate=False)

        return config
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file {path}: {e}")
        raise ConfigurationError(f"Invalid JSON in configuration file {path}: {e}") from e
    except Exception as e:
        logger.error(f"Error loading configuration from file {path}: {e}")
        raise ConfigurationError(f"Error loading configuration from file {path}: {e}") from e


def save_config(config: Config, file_path: Union[str, Path] = CONFIG_FILE_NAME) -> bool:
    """
    Save configuration to a file.

    Args:
        config: Configuration object to save
        file_path: Path to the configuration file

    Returns:
        True if the configuration was saved successfully, False otherwise
    """
    try:
        # Convert config to dictionary
        config_dict = {
            "agent_api_url": config.agent_api_url,
            "auto_start_agent": config.auto_start_agent,
            "agent_type": config.agent_type.value if config.agent_type else None,
            "server": {
                "transport": config.server.transport.value,
                "host": config.server.host,
                "port": config.server.port
            },
            "debug": config.debug,
            "config_version": config.config_version
        }

        # Write to file
        with open(file_path, "w") as f:
            json.dump(config_dict, f, indent=2)

        logger.debug(f"Configuration saved to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving configuration to {file_path}: {e}")
        return False


def load_config() -> Config:
    """
    Load configuration from all sources.

    This function loads configuration from environment variables and configuration files,
    with environment variables taking precedence. It also validates the configuration.

    Returns:
        A Config object with values from all sources

    Raises:
        ConfigurationError: If the configuration is invalid
    """
    # Start with default configuration
    config = Config()

    try:
        # Try to load from configuration file in the current directory
        try:
            file_config = load_from_file(CONFIG_FILE_NAME)
            if file_config:
                # Update config with values from file
                config = file_config
        except ConfigurationError as e:
            logger.warning(f"Error loading configuration from file, using defaults: {e}")
            # Continue with default configuration

        # Try to load from environment variables (highest priority)
        try:
            env_config = load_from_env()

            # Update config with values from environment
            if env_config.agent_type:
                config.agent_type = env_config.agent_type
            if env_config.agent_api_url != DEFAULT_AGENT_API_URL:
                config.agent_api_url = env_config.agent_api_url
            if env_config.auto_start_agent:
                config.auto_start_agent = env_config.auto_start_agent
            if env_config.server.transport != TransportType.STDIO:
                config.server.transport = env_config.server.transport
            if env_config.server.host != DEFAULT_HOST:
                config.server.host = env_config.server.host
            if env_config.server.port != DEFAULT_PORT:
                config.server.port = env_config.server.port
            if env_config.debug:
                config.debug = env_config.debug

            # Add environment to config sources if not already present
            if "environment" not in config.config_sources:
                config.config_sources.append("environment")
        except ConfigurationError as e:
            logger.warning(f"Error loading configuration from environment: {e}")
            # Continue with file or default configuration

        # Ensure API keys are loaded and validated
        try:
            config.load_api_keys(validate=True)
        except APIKeyError as e:
            # Only log a warning here, validation will be done again when needed
            logger.warning(f"API key validation failed: {e}")

        # Validate the entire configuration
        config.validate()

        logger.info(f"Configuration loaded from sources: {', '.join(config.config_sources)}")
        if config.debug:
            logger.debug(f"Configuration: {config.to_dict()}")

        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise ConfigurationError(f"Error loading configuration: {e}") from e
