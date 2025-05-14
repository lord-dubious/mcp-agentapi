#!/usr/bin/env python3
"""
Unified CLI module for the MCP server for Agent API.

This module provides a command-line interface for managing agents and the MCP server,
including starting, stopping, switching between agents, and checking their status.
"""

import argparse
import asyncio
import logging
import subprocess
import sys

from .agent_manager import AgentInstallStatus, AgentManager
from .config import Config, load_config, save_config
from .models import convert_to_agent_type
from .context import start_agent_api

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp-agentapi.cli")

# ANSI color codes for terminal output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_error(message: str) -> None:
    """Print an error message in red."""
    print(f"{RED}{message}{RESET}")


def print_success(message: str) -> None:
    """Print a success message in green."""
    print(f"{GREEN}{message}{RESET}")


def print_warning(message: str) -> None:
    """Print a warning message in yellow."""
    print(f"{YELLOW}{message}{RESET}")


def print_info(message: str) -> None:
    """Print an info message in blue."""
    print(f"{BLUE}{message}{RESET}")


def print_header(message: str) -> None:
    """Print a header message in bold cyan."""
    print(f"\n{BOLD}{CYAN}{message}{RESET}")


async def handle_start(args: argparse.Namespace, config: Config, agent_manager: AgentManager) -> None:
    """
    Handle the 'start' command.

    Args:
        args: Command-line arguments
        config: Configuration object
        agent_manager: Agent manager instance
    """
    # Get the agent type
    agent_type_str = args.agent_name
    if not agent_type_str:
        # Use the agent type from configuration
        if config.agent_type is None:
            print_error("No agent type specified and no default agent type in configuration.")
            return
        agent_type_str = config.agent_type.value

    # Convert to enum
    try:
        agent_type = convert_to_agent_type(agent_type_str)
    except ValueError as e:
        print_error(str(e))
        return

    # Check if the agent is installed
    install_status, _ = await agent_manager.get_agent_status(agent_type)

    if install_status != AgentInstallStatus.INSTALLED:
        print_warning(f"Agent {agent_type_str} is not installed.")
        if args.auto_install:
            print_info(f"Installing agent {agent_type_str}...")
            success = await agent_manager.install_agent(agent_type)
            if not success:
                print_error(f"Failed to install agent {agent_type_str}.")
                return
            print_success(f"Agent {agent_type_str} installed successfully.")
        else:
            print_info("Use 'agent install' command to install it or use --auto-install flag.")
            return

    # Start the agent
    print_info(f"Starting agent {agent_type_str}...")
    process = await agent_manager.start_agent(agent_type)

    if process:
        print_success(f"Agent {agent_type_str} started successfully with PID {process.pid}.")

        # Update configuration if requested
        if args.update_config:
            config.agent_type = agent_type
            config.auto_start_agent = True
            if save_config(config):
                print_info("Configuration updated.")
    else:
        print_error(f"Failed to start agent {agent_type_str}.")


async def handle_stop(args: argparse.Namespace, config: Config, agent_manager: AgentManager) -> None:
    """
    Handle the 'stop' command.

    Args:
        args: Command-line arguments
        config: Configuration object
        agent_manager: Agent manager instance
    """
    # Get the agent type
    agent_type_str = args.agent_name
    if not agent_type_str:
        # Use the agent type from configuration
        if config.agent_type is None:
            print_error("No agent type specified and no default agent type in configuration.")
            return
        agent_type_str = config.agent_type.value

    # Convert to enum
    try:
        agent_type = convert_to_agent_type(agent_type_str)
    except ValueError as e:
        print_error(str(e))
        return

    # Stop the agent
    print_info(f"Stopping agent {agent_type_str}...")
    success = await agent_manager.stop_agent(agent_type)

    if success:
        print_success(f"Agent {agent_type_str} stopped successfully.")

        # Update configuration if requested
        if args.update_config:
            config.auto_start_agent = False
            if save_config(config):
                print_info("Configuration updated.")
    else:
        print_error(f"Agent {agent_type_str} is not running.")


async def handle_switch(args: argparse.Namespace, config: Config, agent_manager: AgentManager) -> None:
    """
    Handle the 'switch' command.

    Args:
        args: Command-line arguments
        config: Configuration object
        agent_manager: Agent manager instance
    """
    # Get the agent type
    agent_type_str = args.agent_name

    # Convert to enum
    try:
        agent_type = convert_to_agent_type(agent_type_str)
    except ValueError as e:
        print_error(str(e))
        return

    # Check if the agent is installed
    install_status, _ = await agent_manager.get_agent_status(agent_type)

    if install_status != AgentInstallStatus.INSTALLED:
        print_warning(f"Agent {agent_type_str} is not installed.")
        if args.auto_install:
            print_info(f"Installing agent {agent_type_str}...")
            success = await agent_manager.install_agent(agent_type)
            if not success:
                print_error(f"Failed to install agent {agent_type_str}.")
                return
            print_success(f"Agent {agent_type_str} installed successfully.")
        else:
            print_info("Use 'agent install' command to install it or use --auto-install flag.")
            return

    # Switch to the agent
    print_success(f"Switched to agent {agent_type_str}.")

    # Update configuration
    config.agent_type = agent_type

    # Start the agent if requested
    if args.restart:
        print_info(f"Starting agent {agent_type_str}...")
        process = await agent_manager.start_agent(agent_type)

        if process:
            print_success(f"Agent {agent_type_str} started successfully with PID {process.pid}.")
            config.auto_start_agent = True
        else:
            print_error(f"Failed to start agent {agent_type_str}.")

    # Save configuration
    if save_config(config):
        print_info("Configuration updated.")


async def handle_status(_args: argparse.Namespace, config: Config, agent_manager: AgentManager) -> None:
    """
    Handle the 'status' command.

    Args:
        _args: Command-line arguments (unused)
        config: Configuration object
        agent_manager: Agent manager instance
    """
    # Detect all agents
    await agent_manager.detect_agents()

    print_header("Agent Status")

    # Print table header
    print(f"{BOLD}{'Agent Type':<15} {'Install Status':<15} {'Running Status':<15} {'PID':<10} {'Default':<10}{RESET}")
    print("-" * 65)

    # Print status for each agent
    for agent_type, agent_info in agent_manager.agents.items():
        is_default = config.agent_type == agent_type
        default_str = "Yes" if is_default else "No"
        pid_str = str(agent_info.process.pid) if agent_info.process else "N/A"

        print(
            f"{agent_type.value:<15} "
            f"{agent_info.install_status.value:<15} "
            f"{agent_info.running_status.value:<15} "
            f"{pid_str:<10} "
            f"{default_str:<10}"
        )


async def handle_install(args: argparse.Namespace, config: Config, agent_manager: AgentManager) -> None:
    """
    Handle the 'install' command.

    Args:
        args: Command-line arguments
        config: Configuration object
        agent_manager: Agent manager instance
    """
    # Get the agent type
    agent_type_str = args.agent_name

    # Convert to enum
    try:
        agent_type = convert_to_agent_type(agent_type_str)
    except ValueError as e:
        print_error(str(e))
        return

    # Check if the agent is already installed
    install_status, _ = await agent_manager.get_agent_status(agent_type)

    if install_status == AgentInstallStatus.INSTALLED:
        print_warning(f"Agent {agent_type_str} is already installed.")
        return

    # Install the agent
    print_info(f"Installing agent {agent_type_str}...")
    success = await agent_manager.install_agent(agent_type)

    if success:
        print_success(f"Agent {agent_type_str} installed successfully.")

        # Update configuration if requested
        if args.update_config:
            config.agent_type = agent_type
            if save_config(config):
                print_info("Configuration updated.")
    else:
        print_error(f"Failed to install agent {agent_type_str}.")


async def handle_list(_args: argparse.Namespace, _config: Config, agent_manager: AgentManager) -> None:
    """
    Handle the 'list' command.

    Args:
        _args: Command-line arguments (unused)
        _config: Configuration object (unused)
        agent_manager: Agent manager instance
    """
    # Detect all agents
    await agent_manager.detect_agents()

    print_header("Available Agents")

    # Print table header
    print(f"{BOLD}{'Agent Type':<15} {'Install Status':<15} {'Version':<20}{RESET}")
    print("-" * 50)

    # Print status for each agent
    for agent_type, agent_info in agent_manager.agents.items():
        version = agent_info.version or "N/A"
        print(
            f"{agent_type.value:<15} "
            f"{agent_info.install_status.value:<15} "
            f"{version:<20}"
        )


async def handle_start_server(args: argparse.Namespace, config: Config, agent_manager: AgentManager) -> None:
    """
    Handle the 'start-server' command.

    Args:
        args: Command-line arguments
        config: Configuration object
        agent_manager: Agent manager instance
    """
    # Update configuration from command-line arguments
    if args.transport is not None:
        from .config import TransportType
        config.server.transport = TransportType(args.transport)

    if args.host is not None:
        config.server.host = args.host

    if args.port is not None:
        config.server.port = args.port

    if args.agent_api_url is not None:
        config.agent_api_url = args.agent_api_url

    if args.agent_name is not None:
        try:
            config.agent_type = convert_to_agent_type(args.agent_name)
        except ValueError as e:
            print_error(str(e))
            return

    if args.auto_start is not None:
        config.auto_start_agent = args.auto_start

    if args.debug:
        config.debug = True
        logging.getLogger("mcp-agentapi").setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    # Save updated configuration
    save_config(config)

    # Variable to hold the Agent API process if auto-started
    agent_api_process = None

    # Auto-start Agent API if requested
    if config.auto_start_agent:
        if config.agent_type is None:
            print_error("Agent type must be specified when using auto-start-agent")
            return

        # Start the Agent API server
        print_info(f"Starting agent {config.agent_type.value}...")
        agent_api_process = await start_agent_api(config.agent_type.value, config)
        print_success(f"Agent {config.agent_type.value} started with PID {agent_api_process.pid}")

    try:
        # Import here to avoid circular imports
        import sys
        import os

        # Add the project root to the Python path
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Import the main function from server.py
        from server import main as run_server

        print_info(f"Starting MCP server for Agent API (URL: {config.agent_api_url})")

        # Run the main function from our implementation
        await run_server()
    finally:
        # Clean up the Agent API process if it was auto-started
        if agent_api_process is not None:
            print_info(f"Terminating Agent API server (PID {agent_api_process.pid})")
            agent_api_process.terminate()
            try:
                agent_api_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print_warning("Agent API server did not terminate gracefully, forcing...")
                agent_api_process.kill()


async def main() -> None:
    """Main entry point for the AgentAPI MCP CLI."""
    # Create the top-level parser
    parser = argparse.ArgumentParser(
        description="AgentAPI MCP - Central Control System for AI Agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agentapi-mcp list                       # List available agents
  agentapi-mcp status                     # Show status of all agents
  agentapi-mcp start goose                # Start the Goose agent
  agentapi-mcp stop aider                 # Stop the Aider agent
  agentapi-mcp switch claude --restart    # Switch to Claude agent and restart it
  agentapi-mcp install aider              # Install the Aider agent
  agentapi-mcp start-server               # Start the MCP server
  agentapi-mcp start-server --agent goose # Start the MCP server with Goose agent
        """
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # 'list' command
    subparsers.add_parser("list", help="List available agents")

    # 'status' command
    subparsers.add_parser("status", help="Show status of all agents")

    # 'start' command
    start_parser = subparsers.add_parser("start", help="Start an agent")
    start_parser.add_argument("agent_name", nargs="?", help="Name of the agent to start")
    start_parser.add_argument("--auto-install", action="store_true", help="Automatically install the agent if not installed")
    start_parser.add_argument("--update-config", action="store_true", help="Update configuration with the selected agent")

    # 'stop' command
    stop_parser = subparsers.add_parser("stop", help="Stop an agent")
    stop_parser.add_argument("agent_name", nargs="?", help="Name of the agent to stop")
    stop_parser.add_argument("--update-config", action="store_true", help="Update configuration to not auto-start the agent")

    # 'switch' command
    switch_parser = subparsers.add_parser("switch", help="Switch to a different agent")
    switch_parser.add_argument("agent_name", help="Name of the agent to switch to")
    switch_parser.add_argument("--restart", action="store_true", help="Restart the agent after switching")
    switch_parser.add_argument("--auto-install", action="store_true", help="Automatically install the agent if not installed")

    # 'install' command
    install_parser = subparsers.add_parser("install", help="Install an agent")
    install_parser.add_argument("agent_name", help="Name of the agent to install")
    install_parser.add_argument("--update-config", action="store_true", help="Update configuration with the installed agent")

    # 'start-server' command
    start_parser = subparsers.add_parser("start-server", help="Start the MCP server")
    start_parser.add_argument("--transport", choices=["stdio", "sse"], help="Transport mode (stdio or sse)")
    start_parser.add_argument("--host", help="Host to bind to (for SSE mode)")
    start_parser.add_argument("--port", type=int, help="Port to listen on (for SSE mode)")
    start_parser.add_argument("--agent-api-url", help="Agent API URL")
    start_parser.add_argument("--agent", dest="agent_name", help="Agent type to use")
    start_parser.add_argument("--auto-start", action="store_true", dest="auto_start", default=None, help="Automatically start the agent")
    start_parser.add_argument("--no-auto-start", action="store_false", dest="auto_start", default=None, help="Do not automatically start the agent")
    start_parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    # Parse arguments
    args = parser.parse_args()

    # If no command is provided, show help
    if not args.command:
        parser.print_help()
        return

    # Load configuration
    config = load_config()

    # Create agent manager
    agent_manager = AgentManager(config)

    # Handle the command
    if args.command == "list":
        await handle_list(args, config, agent_manager)
    elif args.command == "status":
        await handle_status(args, config, agent_manager)
    elif args.command == "start":
        await handle_start(args, config, agent_manager)
    elif args.command == "stop":
        await handle_stop(args, config, agent_manager)
    elif args.command == "switch":
        await handle_switch(args, config, agent_manager)
    elif args.command == "install":
        await handle_install(args, config, agent_manager)
    elif args.command == "start-server":
        await handle_start_server(args, config, agent_manager)


def cli_main():
    """Entry point for the CLI when installed as a package."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print_error(f"Error: {e}")
        sys.exit(1)
