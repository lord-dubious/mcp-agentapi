#!/usr/bin/env python3
"""
Context management for the MCP server for Agent API.

This module contains the context class and lifecycle management for the MCP server.
Following the mcp-mem0 pattern, it provides a clean, type-safe context for the MCP server.
"""

import asyncio
import logging
import os
import subprocess
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

from .models import AgentType, ConversationRole
from .event_emitter import EventEmitter
from .config import Config, load_config
from .agent_manager import AgentManager
from .resource_manager import ResourceManager
from .health_check import HealthCheck

# Configure logging
logger = logging.getLogger("mcp-server-agentapi.context")


@dataclass
class AgentAPIContext:
    """
    Context for the Agent API MCP server.

    This class holds all the shared resources and state for the MCP server.
    It is created during server initialization and passed to tools and resources.
    Following the mcp-mem0 pattern, it provides a clean, type-safe context for the MCP server.

    Attributes:
        http_client: HTTP client for communicating with the Agent API
        agent_api_url: URL of the Agent API server
        agent_type: Type of the agent (claude, goose, aider, etc.)
        config: Configuration object
        agent_manager: Agent Manager for detecting, installing, and managing agents
        event_emitter: Event emitter for forwarding Agent API events to MCP clients
        resource_manager: Resource Manager for tracking and cleaning up resources
        health_check: Health Check for monitoring the health of the server and its components
        agent_process: Process handle for the Agent API server if auto-started
    """
    # Core components
    http_client: httpx.AsyncClient
    agent_api_url: str
    agent_type: AgentType
    config: Config
    agent_manager: AgentManager
    event_emitter: EventEmitter
    resource_manager: ResourceManager
    health_check: HealthCheck

    # Optional components
    agent_process: Optional[subprocess.Popen] = None


async def detect_agent_type(
    http_client: httpx.AsyncClient,
    agent_api_url: str
) -> AgentType:
    """
    Detect the agent type from the Agent API.

    Args:
        http_client: The HTTP client to use
        agent_api_url: The Agent API URL

    Returns:
        The detected agent type
    """
    # Import here to avoid circular imports
    from .api_client import AgentAPIClient

    try:
        # Create API client
        api_client = AgentAPIClient(http_client, agent_api_url)

        # Get agent type from API
        agent_type_str = await api_client.get_agent_type()

        # Map the agent type string to an AgentType enum value
        try:
            return AgentType(agent_type_str.lower())
        except ValueError:
            logger.warning(f"Unknown agent type: {agent_type_str}")

        # If we couldn't determine the agent type from the status, check the messages
        messages = await api_client.get_message_list()

        for message in messages:
            if message.role == ConversationRole.AGENT:
                content = message.content.lower()

                # Check for agent-specific patterns in the message content
                if "claude" in content:
                    return AgentType.CLAUDE
                elif "goose" in content:
                    return AgentType.GOOSE
                elif "aider" in content:
                    return AgentType.AIDER
                elif "codex" in content:
                    return AgentType.CODEX
    except Exception as e:
        logger.warning(f"Error detecting agent type: {e}")

    # Default to custom if we couldn't determine the agent type
    return AgentType.CUSTOM


async def start_agent_api(agent_type: str, config: Config) -> subprocess.Popen:
    """
    Start the Agent API server with the specified agent type.

    Args:
        agent_type: The type of agent to start
        config: The configuration object

    Returns:
        The subprocess handle for the Agent API server
    """
    logger.info(f"Starting Agent API server with agent type: {agent_type}")

    # Determine the command to run based on agent type
    cmd = ["agentapi", "server", "--"]

    try:
        agent_enum = AgentType(agent_type.lower())
        agent_config = config.get_agent_config(agent_enum)
    except ValueError:
        logger.warning(f"Invalid agent type: {agent_type}, using CUSTOM")
        agent_enum = AgentType.CUSTOM
        agent_config = config.get_agent_config(agent_enum)

    if agent_enum == AgentType.GOOSE:
        # Check if API key is set
        if not agent_config.api_key:
            logger.warning(f"{agent_config.api_key_env} environment variable not set. Goose may not work correctly.")
        cmd.append("goose")
    elif agent_enum == AgentType.AIDER:
        # Check if API key is set
        if not agent_config.api_key:
            logger.warning(f"{agent_config.api_key_env} environment variable not set. Aider may not work correctly.")

        # Get additional arguments for Aider
        model = agent_config.model or "deepseek"
        api_key = agent_config.api_key

        cmd.extend(["aider", "--model", model])
        if api_key and "api_key_param" in agent_config.additional_args:
            cmd.extend([agent_config.additional_args["api_key_param"], f"{model}={api_key}"])
    elif agent_enum == AgentType.CLAUDE:
        cmd.append("claude")
    elif agent_enum == AgentType.CODEX:
        cmd.append("codex")
    else:
        # Default to custom
        cmd.append("custom")

    # Create a copy of the current environment
    env = os.environ.copy()

    # Ensure API keys are set in the environment
    if agent_enum == AgentType.GOOSE and agent_config.api_key:
        env["GOOGLE_API_KEY"] = agent_config.api_key
    elif agent_enum == AgentType.AIDER and agent_config.api_key:
        env["OPENAI_API_KEY"] = agent_config.api_key
    elif agent_enum == AgentType.CLAUDE and agent_config.api_key:
        env["ANTHROPIC_API_KEY"] = agent_config.api_key
    elif agent_enum == AgentType.CODEX and agent_config.api_key:
        env["OPENAI_API_KEY"] = agent_config.api_key

    # Log the environment variables being used (masked for security)
    masked_env = {k: v[:4] + "..." + v[-4:] if k.endswith("_API_KEY") and len(v) > 8 else v
                 for k, v in env.items() if k.endswith("_API_KEY")}
    logger.info(f"Starting agent with API keys: {masked_env}")

    # Start the Agent API server
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env  # Pass the environment to the child process
    )

    # Wait for the server to start
    logger.info("Waiting for Agent API server to start...")
    await asyncio.sleep(5)

    return process


@asynccontextmanager
async def agent_api_lifespan(server: FastMCP) -> AsyncIterator[AgentAPIContext]:
    """
    Manages the Agent API client lifecycle.

    This context manager initializes and cleans up resources for the MCP server.
    Following the mcp-mem0 pattern, it creates all necessary resources during startup,
    yields a type-safe context object, and ensures proper cleanup during shutdown.

    Args:
        server: The FastMCP server instance

    Yields:
        AgentAPIContext: The context containing the Agent API client and resources
    """
    # Load configuration
    config = load_config()

    # Configure logging level based on debug flag
    if config.debug:
        logging.getLogger("mcp-server-agentapi").setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    # Initialize core components
    logger.info("Initializing core components...")
    http_client = httpx.AsyncClient()
    resource_manager = ResourceManager()
    health_check = HealthCheck(config, http_client)
    agent_manager = AgentManager(config)

    # Initialize event emitter
    event_emitter = EventEmitter(
        http_client=http_client,
        agent_api_url=config.agent_api_url
    )
    event_emitter.set_resource_manager(resource_manager)

    # Detect available agents
    logger.info("Detecting available agents...")
    await agent_manager.detect_agents()

    # Determine agent type (from config or detection)
    agent_type = None
    agent_process = None

    if config.agent_type:
        # Use the agent type from configuration
        agent_type = config.agent_type
        logger.info(f"Using configured agent type: {agent_type.value}")
    else:
        # Detect agent type
        try:
            agent_type = await detect_agent_type(http_client, config.agent_api_url)
            logger.info(f"Detected agent type: {agent_type.value}")
        except Exception as e:
            logger.warning(f"Error detecting agent type: {e}, using CUSTOM")
            agent_type = AgentType.CUSTOM

    # Start agent if auto-start is enabled
    if config.auto_start_agent and agent_type:
        logger.info(f"Auto-starting agent: {agent_type.value}")
        try:
            # Check if the agent is installed
            install_status, _ = await agent_manager.get_agent_status(agent_type)

            # Install the agent if needed
            if install_status != "installed":
                logger.info(f"Agent {agent_type.value} is not installed. Installing...")
                if await agent_manager.install_agent(agent_type):
                    logger.info(f"Agent {agent_type.value} installed successfully")
                else:
                    logger.warning(f"Failed to install agent {agent_type.value}")

            # Start the agent
            agent_process = await agent_manager.start_agent(agent_type)
            if agent_process:
                logger.info(f"Agent API server started with PID {agent_process.pid}")

                # Register the process with the resource manager
                process_key = f"agent_{agent_type.value}"
                await resource_manager.register_process(process_key, agent_process)

                # Start agent monitoring in a background task
                monitoring_task = asyncio.create_task(
                    agent_manager.monitor_agent(agent_type, auto_reconnect=True)
                )

                # Register the monitoring task with the resource manager
                await resource_manager.register_task(f"monitor_{agent_type.value}", monitoring_task)
                logger.info(f"Agent monitoring started for {agent_type.value}")
            else:
                logger.error(f"Failed to start Agent API server")
        except Exception as e:
            logger.error(f"Failed to start Agent API server: {e}")

    # Create context with all components
    context = AgentAPIContext(
        http_client=http_client,
        agent_api_url=config.agent_api_url,
        agent_type=agent_type,
        config=config,
        agent_manager=agent_manager,
        event_emitter=event_emitter,
        resource_manager=resource_manager,
        health_check=health_check,
        agent_process=agent_process
    )

    # Start health check
    logger.info("Starting health check...")
    await health_check.start()

    # Start event stream in a background task
    logger.info("Starting event stream...")
    event_stream_task = event_emitter.start_background_stream(server)

    # Register the event stream task with the resource manager
    if event_stream_task:
        await resource_manager.register_task("event_stream", event_stream_task)

    # Start screen stream in a background task (if supported by the Agent API)
    logger.info("Starting screen stream...")
    screen_stream_task = event_emitter.start_background_screen_stream(server)

    # Register the screen stream task with the resource manager
    if screen_stream_task:
        await resource_manager.register_task("screen_stream", screen_stream_task)

    logger.info("Initialization complete, yielding context...")

    try:
        # Yield context to the server
        yield context
    finally:
        # Perform cleanup in reverse order of initialization
        logger.info("Shutting down...")

        # Stop health check
        logger.info("Stopping health check...")
        await health_check.stop()

        # Clean up all resources using the resource manager
        logger.info("Cleaning up resources...")
        await resource_manager.cleanup_all()

        # Close HTTP client
        logger.info("Closing HTTP client...")
        await http_client.aclose()

        logger.info("Shutdown complete")
