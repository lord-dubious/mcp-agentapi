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
from typing import Dict, Any, Optional, List, Union

# Import the MCP SDK
from mcp.server.fastmcp import FastMCP, Context

# Import our implementation
import sys
import os

# Add the parent directory to the Python path to find the src module
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from src.config import load_config, save_config, TransportType, Config
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

# Import the rest of the server implementation from the original server.py file
# This is a placeholder - you would need to copy the actual implementation here

async def main() -> None:
    """
    Main entry point for the MCP server.
    This function is called when the server is started.
    """
    # Parse command line arguments
    args = parse_args()

    # Load configuration
    config = load_config()

    # Update configuration from command line arguments
    if args.transport:
        config.server.transport = TransportType(args.transport)
    if args.host:
        config.server.host = args.host
    if args.port:
        config.server.port = args.port
    if args.agent_api_url:
        config.agent_api_url = args.agent_api_url
    if args.agent_name:
        try:
            config.agent_type = AgentType(args.agent_name.lower())
        except ValueError:
            logger.warning(f"Invalid agent type: {args.agent_name}")
    if args.auto_start is not None:
        config.auto_start_agent = args.auto_start
    if args.debug is not None:
        config.debug = args.debug

    # Save configuration
    save_config(config)

    # Configure logging level based on debug flag
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


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="MCP Server for Agent API")
    parser.add_argument("--transport", choices=["stdio", "sse"], default=None, help="Transport mode (stdio or sse)")
    parser.add_argument("--host", default=None, help="Host to bind to (for SSE mode)")
    parser.add_argument("--port", type=int, default=None, help="Port to listen on (for SSE mode)")
    parser.add_argument("--agent-api-url", default=None, help="Agent API URL")
    parser.add_argument("--agent", dest="agent_name", default=None, help="Agent type to use")
    parser.add_argument("--auto-start", action="store_true", dest="auto_start", default=None, help="Automatically start the agent")
    parser.add_argument("--debug", action="store_true", default=None, help="Enable debug logging")
    parser.add_argument("--config", default=None, help="Path to configuration file")
    return parser.parse_args()


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
