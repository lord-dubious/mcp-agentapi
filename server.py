#!/usr/bin/env python3
"""
AgentAPI MCP - Central Control System for AI Agents

This is the main entry point for the AgentAPI MCP server.
It follows the official Model Context Protocol (MCP) specification
and uses the Python MCP SDK to provide a standardized interface
for interacting with AI agents.
"""

import sys
import asyncio
import logging
import argparse
import json
from typing import Dict, Any

# Import the MCP SDK
from mcp.server.fastmcp import FastMCP, Context

# Import our implementation
from src.config import load_config, save_config, TransportType
from src.context import AgentAPIContext, agent_api_lifespan
from src.api_client import AgentAPIClient
from src.models import AgentType, MessageType
from src.utils.error_handler import create_error_response, handle_exception

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp-agentapi")

# Create the MCP server with proper lifespan management
mcp = FastMCP(
    "AgentAPI-MCP",
    description="MCP server for interacting with AI agents through the Agent API",
    lifespan=agent_api_lifespan,
)

# Define MCP tools for agent management
@mcp.tool()
async def get_agent_type(ctx: Context) -> str:
    """
    Get the type of the agent (claude, goose, aider, codex, or custom).

    Returns:
        A string indicating the agent type
    """
    app_ctx: AgentAPIContext = ctx.request_context.lifespan_context

    try:
        # Create API client
        api_client = AgentAPIClient(app_ctx.http_client, app_ctx.agent_api_url)

        # Get agent type from API
        agent_type = await api_client.get_agent_type()
        return agent_type
    except Exception as e:
        # Use standardized error handling
        handle_exception(e)
        logger.error(f"Error getting agent type: {e}")
        return "unknown"

@mcp.tool()
async def list_available_agents(ctx: Context) -> Dict[str, Any]:
    """
    List all available agents and their installation status.

    Returns:
        A JSON string containing information about available agents
    """
    app_ctx: AgentAPIContext = ctx.request_context.lifespan_context

    try:
        # Detect available agents
        agents = await app_ctx.agent_manager.detect_agents()

        # Format the result
        result = {
            "agents": {}
        }

        for agent_type, agent_info in agents.items():
            result["agents"][agent_type.value] = {
                "installed": agent_info.install_status.value,
                "running": agent_info.running_status.value,
                "version": agent_info.version,
                "api_key_required": agent_info.api_key_required,
                "api_key_set": agent_info.api_key_set
            }

        return result
    except Exception as e:
        # Use standardized error handling
        return handle_exception(e)

@mcp.tool()
async def install_agent(ctx: Context, agent_type: str) -> str:
    """
    Install a specific agent.

    Args:
        agent_type: Type of agent to install (claude, goose, aider, codex, or custom)

    Returns:
        A string indicating the result of the installation
    """
    app_ctx: AgentAPIContext = ctx.request_context.lifespan_context

    try:
        # Convert agent type string to enum
        try:
            agent_enum = AgentType(agent_type.lower())
        except ValueError:
            return f"Error: Invalid agent type: {agent_type}"

        # Install the agent
        success = await app_ctx.agent_manager.install_agent(agent_enum)

        if success:
            return f"Agent {agent_type} installed successfully"
        else:
            return f"Failed to install agent {agent_type}"
    except Exception as e:
        # Use standardized error handling
        error_data = handle_exception(e)
        return f"Error: {error_data['error']}"

@mcp.tool()
async def start_agent(ctx: Context, agent_type: str) -> str:
    """
    Start a specific agent.

    Args:
        agent_type: Type of agent to start (claude, goose, aider, codex, or custom)

    Returns:
        A string indicating the result of starting the agent
    """
    app_ctx: AgentAPIContext = ctx.request_context.lifespan_context

    try:
        # Convert agent type string to enum
        try:
            agent_enum = AgentType(agent_type.lower())
        except ValueError:
            return f"Error: Invalid agent type: {agent_type}"

        # Start the agent
        process = await app_ctx.agent_manager.start_agent(agent_enum)

        if process:
            # Update the context with the new agent type
            app_ctx.agent_type = agent_enum

            return f"Agent {agent_type} started successfully with PID {process.pid}"
        else:
            return f"Failed to start agent {agent_type}"
    except Exception as e:
        # Use standardized error handling
        error_data = handle_exception(e)
        return f"Error: {error_data['error']}"

@mcp.tool()
async def stop_agent(ctx: Context, agent_type: str) -> str:
    """
    Stop a specific agent.

    Args:
        agent_type: Type of agent to stop (claude, goose, aider, codex, or custom)

    Returns:
        A string indicating the result of stopping the agent
    """
    app_ctx: AgentAPIContext = ctx.request_context.lifespan_context

    try:
        # Convert agent type string to enum
        try:
            agent_enum = AgentType(agent_type.lower())
        except ValueError:
            return f"Error: Invalid agent type: {agent_type}"

        # Stop the agent
        success = await app_ctx.agent_manager.stop_agent(agent_enum)

        if success:
            return f"Agent {agent_type} stopped successfully"
        else:
            return f"Failed to stop agent {agent_type}"
    except Exception as e:
        # Use standardized error handling
        error_data = handle_exception(e)
        return f"Error: {error_data['error']}"

@mcp.tool()
async def restart_agent(ctx: Context, agent_type: str) -> str:
    """
    Restart a specific agent.

    Args:
        agent_type: Type of agent to restart (claude, goose, aider, codex, or custom)

    Returns:
        A string indicating the result of restarting the agent
    """
    app_ctx: AgentAPIContext = ctx.request_context.lifespan_context

    try:
        # Convert agent type string to enum
        try:
            agent_enum = AgentType(agent_type.lower())
        except ValueError:
            return f"Error: Invalid agent type: {agent_type}"

        # Stop the agent first
        await app_ctx.agent_manager.stop_agent(agent_enum)

        # Start the agent
        process = await app_ctx.agent_manager.start_agent(agent_enum)

        if process:
            # Update the context with the new agent type
            app_ctx.agent_type = agent_enum

            return f"Agent {agent_type} restarted successfully with PID {process.pid}"
        else:
            return f"Failed to restart agent {agent_type}"
    except Exception as e:
        # Use standardized error handling
        error_data = handle_exception(e)
        return f"Error: {error_data['error']}"

@mcp.tool()
async def get_status(ctx: Context) -> str:
    """
    Get the current status of the agent.

    Returns:
        A string indicating the agent's status: 'running' or 'stable'.
    """
    app_ctx: AgentAPIContext = ctx.request_context.lifespan_context

    try:
        # Create API client
        api_client = AgentAPIClient(app_ctx.http_client, app_ctx.agent_api_url)

        # Get status from API
        status = await api_client.get_status()
        return status.get("status", "unknown")
    except Exception as e:
        # Use standardized error handling
        handle_exception(e)
        return "unknown"

@mcp.tool()
async def check_health(ctx: Context) -> Dict[str, Any]:
    """
    Check the health of the MCP server and its components.

    This tool performs a fresh health check on the server, agent, and resources.
    It can be used to diagnose issues with the system.

    Returns:
        A JSON string containing detailed health status information
    """
    app_ctx: AgentAPIContext = ctx.request_context.lifespan_context

    try:
        # Perform health check
        health_status = await app_ctx.health_check.check_health()
        return health_status
    except Exception as e:
        # Use standardized error handling
        return handle_exception(e)

@mcp.tool()
async def get_messages(ctx: Context) -> Dict[str, Any]:
    """
    Get all messages in the conversation history.

    Returns:
        A dictionary containing all messages in the conversation or error information.
    """
    app_ctx: AgentAPIContext = ctx.request_context.lifespan_context

    try:
        # Create API client
        api_client = AgentAPIClient(app_ctx.http_client, app_ctx.agent_api_url)

        # Get messages from API
        messages = await api_client.get_messages()
        return messages
    except Exception as e:
        # Use standardized error handling
        return handle_exception(e)

@mcp.tool()
async def send_message(ctx: Context, content: str, type: str = "user") -> Dict[str, Any]:
    """
    Send a message to the agent.

    Args:
        content: The message content to send
        type: Message type ('user' or 'raw')

    Returns:
        A dictionary with the result or error information
    """
    app_ctx: AgentAPIContext = ctx.request_context.lifespan_context

    try:
        # Create API client
        api_client = AgentAPIClient(app_ctx.http_client, app_ctx.agent_api_url)

        # Validate message type
        try:
            message_type = MessageType(type.lower())
        except ValueError:
            return create_error_response(
                error_message=f"Invalid message type: {type}. Must be 'user' or 'raw'.",
                error_type="ValidationError",
                status_code=400
            )

        # Send message to API
        result = await api_client.send_message(content, message_type)
        return result
    except Exception as e:
        # Use standardized error handling
        return handle_exception(e)

@mcp.tool()
async def get_screen(ctx: Context) -> Dict[str, Any]:
    """
    Get the current screen content from the Agent API.

    This tool retrieves the current terminal screen content from the Agent API.
    It's useful for getting a snapshot of the terminal screen without subscribing
    to the screen stream.

    Returns:
        A dictionary containing the screen content or error information
    """
    app_ctx: AgentAPIContext = ctx.request_context.lifespan_context

    try:
        # Create API client
        api_client = AgentAPIClient(app_ctx.http_client, app_ctx.agent_api_url)

        # Get screen content from API
        screen = await api_client.get_screen()
        return {"screen": screen}
    except Exception as e:
        # Use standardized error handling
        return handle_exception(e)

# Define MCP resources
@mcp.resource("agent-api://info")
async def get_agent_info(ctx: Context) -> str:
    """
    Get information about the agent and the MCP server.

    Returns:
        A JSON string containing information about the agent and server
    """
    app_ctx: AgentAPIContext = ctx.request_context.lifespan_context

    try:
        # Get configuration from context
        config = app_ctx.config

        # Create basic info
        info = {
            "server": {
                "name": "AgentAPI-MCP",
                "description": "MCP server for interacting with AI agents through the Agent API",
                "agent_api_url": config.agent_api_url,
                "agent_type": config.agent_type.value if config.agent_type else "unknown",
                "version": "1.0.0"
            }
        }

        # Add agent-specific information if available
        if app_ctx.agent_type:
            agent_info = app_ctx.agent_manager.agents.get(app_ctx.agent_type)
            if agent_info:
                info["agent"] = {
                    "type": app_ctx.agent_type.value,
                    "version": agent_info.version or "unknown",
                    "status": agent_info.running_status.value,
                    "api_key_required": agent_info.api_key_required,
                    "api_key_set": agent_info.api_key_set
                }

        return json.dumps(info, indent=2)
    except Exception as e:
        # Use standardized error handling
        error_data = handle_exception(e)
        return json.dumps(error_data, indent=2)

@mcp.resource("agent-api://openapi.json")
async def get_openapi_schema(ctx: Context) -> str:
    """
    Get the OpenAPI schema for the Agent API.

    This resource retrieves the OpenAPI schema from the Agent API, validates it,
    and enhances it if necessary to ensure it contains all required endpoints
    and components.

    Returns:
        The OpenAPI schema as a JSON string
    """
    app_ctx: AgentAPIContext = ctx.request_context.lifespan_context

    try:
        # Create API client
        api_client = AgentAPIClient(app_ctx.http_client, app_ctx.agent_api_url)

        # Get OpenAPI schema
        schema = await api_client.get_openapi_schema()

        # Return as JSON string
        return json.dumps(schema, indent=2)
    except Exception as e:
        # Use standardized error handling
        error_data = handle_exception(e)
        return json.dumps(error_data, indent=2)

# No prompts needed for this MCP server implementation

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="MCP Server for Agent API")
    parser.add_argument("--transport", choices=["stdio", "sse"], default=None, help="Transport mode (stdio or sse)")
    parser.add_argument("--host", default=None, help="Host to bind to (for SSE mode)")
    parser.add_argument("--port", type=int, default=None, help="Port to listen on (for SSE mode)")
    parser.add_argument("--agent-api-url", default=None, help="Agent API URL")
    parser.add_argument("--agent", dest="agent_name", default=None, help="Agent type to use")
    parser.add_argument("--auto-start", action="store_true", dest="auto_start", default=None, help="Automatically start the agent")
    parser.add_argument("--debug", action="store_true", default=None, help="Enable debug logging")
    return parser.parse_args()

async def main():
    """Main entry point for the MCP server"""
    # Parse command line arguments
    args = parse_args()

    # Load configuration
    config = load_config()

    # Update configuration from command line arguments
    if args.transport is not None:
        config.server.transport = TransportType(args.transport)
    if args.host is not None:
        config.server.host = args.host
    if args.port is not None:
        config.server.port = args.port
    if args.agent_api_url is not None:
        config.agent_api_url = args.agent_api_url
    if args.agent_name is not None:
        try:
            config.agent_type = AgentType(args.agent_name.lower())
        except ValueError:
            logger.error(f"Invalid agent type: {args.agent_name}")
            sys.exit(1)
    if args.auto_start is not None:
        config.auto_start_agent = args.auto_start
    if args.debug is not None:
        config.debug = args.debug

    # Save updated configuration
    save_config(config)

    # Set debug logging if enabled
    if config.debug:
        logging.getLogger("mcp-agentapi").setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    try:
        # Set server host and port for SSE transport
        if config.server.transport == TransportType.SSE:
            # Run with SSE transport
            logger.info(f"Starting MCP server with SSE transport on {config.server.host}:{config.server.port}")
            await mcp.run_sse_async(host=config.server.host, port=config.server.port)
        else:
            # Run with stdio transport
            logger.info("Starting MCP server with stdio transport")
            await mcp.run_stdio_async()
    except Exception as e:
        # Use standardized error handling
        error_data = handle_exception(e)
        logger.error(f"Error running MCP server: {error_data['error']}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        # Use standardized error handling
        error_data = handle_exception(e)
        logger.error(f"Error running MCP server: {error_data['error']}")
        sys.exit(1)
