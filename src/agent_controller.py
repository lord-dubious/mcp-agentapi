#!/usr/bin/env python3
"""
Agent Controller for the MCP server.

This module provides a unified interface for controlling agents through the MCP server.
It imports the tools from server.py and provides a CLI interface for them.
"""

import json
import logging
import sys
import os
import asyncio
import argparse
from typing import Dict, Any, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp-server-agentapi.agent-controller")

# Add the parent directory to the Python path to find the server module
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import the tools from server.py
from server import (
    get_agent_type,
    list_available_agents,
    install_agent,
    start_agent,
    stop_agent,
    restart_agent,
    get_status,
    check_health,
    get_messages,
    send_message,
    get_screen
)

# Mock context for CLI usage
class MockContext:
    """
    Mock context for the agent controller tools.

    This class implements the MCP SDK Context interface for CLI usage.
    It provides access to the AgentAPIContext through the request_context.lifespan_context
    property, following the MCP SDK pattern.

    Attributes:
        request_context: Mock request context with lifespan_context
    """
    def __init__(self) -> None:
        from .context import AgentAPIContext
        from .config import load_config

        # Create a mock request context with proper typing
        class MockRequestContext:
            """Mock request context with lifespan_context."""
            def __init__(self, lifespan_context: Any) -> None:
                self.lifespan_context: Any = lifespan_context

        # Create the AgentAPIContext with proper configuration
        config = load_config()

        # Create a mock lifespan context
        self.request_context: Any = MockRequestContext(AgentAPIContext(config))

    async def report_progress(self, current: int, total: int) -> None:
        """
        Report progress for long-running operations.

        Args:
            current: Current progress value
            total: Total progress value
        """
        # In CLI mode, we just print the progress
        print(f"Progress: {current}/{total} ({current/total*100:.1f}%)")

    def info(self, message: str) -> None:
        """
        Log an informational message.

        Args:
            message: Message to log
        """
        # In CLI mode, we just print the message
        print(f"INFO: {message}")

    def warning(self, message: str) -> None:
        """
        Log a warning message.

        Args:
            message: Message to log
        """
        # In CLI mode, we just print the message
        print(f"WARNING: {message}")

    def error(self, message: str) -> None:
        """
        Log an error message.

        Args:
            message: Message to log
        """
        # In CLI mode, we just print the message
        print(f"ERROR: {message}")


async def run_cli():
    """
    Run the CLI interface for the agent controller.
    This function is the main entry point for the CLI.
    """
    # Create the argument parser
    parser = argparse.ArgumentParser(description="Agent Controller CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # get_agent_type command
    subparsers.add_parser("get_agent_type", help="Get the type of the agent")

    # list_available_agents command
    subparsers.add_parser("list_available_agents", help="List all available agents")

    # install_agent command
    install_parser = subparsers.add_parser("install_agent", help="Install an agent")
    install_parser.add_argument("--agent_type", required=True, help="Type of agent to install")

    # start_agent command
    start_parser = subparsers.add_parser("start_agent", help="Start an agent")
    start_parser.add_argument("--agent_type", required=True, help="Type of agent to start")

    # stop_agent command
    stop_parser = subparsers.add_parser("stop_agent", help="Stop an agent")
    stop_parser.add_argument("--agent_type", required=True, help="Type of agent to stop")

    # restart_agent command
    restart_parser = subparsers.add_parser("restart_agent", help="Restart an agent")
    restart_parser.add_argument("--agent_type", required=True, help="Type of agent to restart")

    # get_status command
    subparsers.add_parser("get_status", help="Get the current status of the agent")

    # check_health command
    subparsers.add_parser("check_health", help="Check the health of the MCP server")

    # get_messages command
    subparsers.add_parser("get_messages", help="Get all messages in the conversation")

    # send_message command
    send_parser = subparsers.add_parser("send_message", help="Send a message to the agent")
    send_parser.add_argument("--content", required=True, help="Message content")
    send_parser.add_argument("--type", default="user", help="Message type (user or raw)")

    # get_screen command
    subparsers.add_parser("get_screen", help="Get the current screen content")

    # Parse arguments
    args = parser.parse_args()

    # Create a mock context
    ctx = MockContext()

    # Execute the command
    try:
        if args.command == "get_agent_type":
            result = await get_agent_type(ctx)
        elif args.command == "list_available_agents":
            result = await list_available_agents(ctx)
        elif args.command == "install_agent":
            result = await install_agent(ctx, args.agent_type)
        elif args.command == "start_agent":
            result = await start_agent(ctx, args.agent_type)
        elif args.command == "stop_agent":
            result = await stop_agent(ctx, args.agent_type)
        elif args.command == "restart_agent":
            result = await restart_agent(ctx, args.agent_type)
        elif args.command == "get_status":
            result = await get_status(ctx)
        elif args.command == "check_health":
            result = await check_health(ctx)
        elif args.command == "get_messages":
            result = await get_messages(ctx)
        elif args.command == "send_message":
            result = await send_message(ctx, args.content, args.type)
        elif args.command == "get_screen":
            result = await get_screen(ctx)
        else:
            parser.print_help()
            sys.exit(1)

        # Print the result
        if isinstance(result, (dict, list)):
            print(json.dumps(result, indent=2))
        else:
            print(result)
    except Exception as e:
        # Use standardized error handling
        from src.utils.error_handler import handle_exception
        error_data = handle_exception(e)
        logger.error(f"Error executing command: {error_data['error']}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_cli())
