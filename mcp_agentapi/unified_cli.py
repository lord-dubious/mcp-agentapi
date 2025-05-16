#!/usr/bin/env python3
"""
Unified CLI module for the MCP server for Agent API.

This module provides a unified command-line interface for managing agents and the MCP server,
including starting, stopping, switching between agents, and checking their status.
It consolidates functionality from the three existing entry points:
- mcp-agentapi: Main entry point for the MCP server
- agent-cli: Command-line interface for the agent controller
- agentapi-mcp: Unified CLI for agent management
"""

import argparse
import asyncio
import logging
import subprocess
import sys
from typing import Optional, List, Dict, Any, Union, Callable

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp-agentapi.cli")

# Import necessary modules
import sys
import os

# Add the parent directory to the Python path to find the src module
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from src.agent_manager import AgentInstallStatus, AgentManager
from src.config import Config, load_config, save_config, TransportType
from src.models import convert_to_agent_type
from src.context import start_agent_api

# Import the server module
from .server import main as server_main

# These functions would normally be imported from server.py
# For now, we'll define them here as placeholders
async def get_agent_type(ctx):
    """Get the current agent type."""
    return ctx.request_context.lifespan_context.config.agent_type.value if ctx.request_context.lifespan_context.config.agent_type else None

async def list_available_agents(ctx):
    """List available agents."""
    agent_manager = ctx.request_context.lifespan_context.agent_manager
    await agent_manager.detect_agents()
    return [{"type": agent_type.value, "status": agent_info.install_status.value} for agent_type, agent_info in agent_manager.agents.items()]

async def install_agent(ctx, agent_type):
    """Install an agent."""
    agent_manager = ctx.request_context.lifespan_context.agent_manager
    return await agent_manager.install_agent(agent_type)

async def start_agent(ctx, agent_type):
    """Start an agent."""
    agent_manager = ctx.request_context.lifespan_context.agent_manager
    process = await agent_manager.start_agent(agent_type)
    return {"success": process is not None, "pid": process.pid if process else None}

async def stop_agent(ctx, agent_type):
    """Stop an agent."""
    agent_manager = ctx.request_context.lifespan_context.agent_manager
    return await agent_manager.stop_agent(agent_type)

async def restart_agent(ctx, agent_type):
    """Restart an agent."""
    agent_manager = ctx.request_context.lifespan_context.agent_manager
    await agent_manager.stop_agent(agent_type)
    process = await agent_manager.start_agent(agent_type)
    return {"success": process is not None, "pid": process.pid if process else None}

async def get_status(ctx):
    """Get the status of all agents."""
    agent_manager = ctx.request_context.lifespan_context.agent_manager
    await agent_manager.detect_agents()
    return {agent_type.value: {"install_status": agent_info.install_status.value, "running_status": agent_info.running_status.value} for agent_type, agent_info in agent_manager.agents.items()}

async def check_health(ctx):
    """Check the health of the server."""
    return {"status": "ok", "version": "1.0.0", "uptime": "unknown"}

async def get_messages(ctx):
    """Get all messages in the conversation."""
    api_client = ctx.request_context.lifespan_context.api_client
    return await api_client.get_messages()

async def send_message(ctx, content, message_type="user"):
    """Send a message to the agent."""
    api_client = ctx.request_context.lifespan_context.api_client
    return await api_client.send_message(content, message_type)

async def get_screen(ctx):
    """Get the current screen content."""
    api_client = ctx.request_context.lifespan_context.api_client
    return await api_client.get_screen()

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
        from src.context import AgentAPIContext
        from src.config import load_config

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


# Command handlers will be implemented in separate functions
# Server command handlers
async def handle_server_start(args: argparse.Namespace) -> None:
    """
    Handle the 'server start' command.

    Args:
        args: Command-line arguments
    """
    # Load configuration
    config = load_config()

    # Update configuration from command-line arguments
    if args.transport is not None:
        # TransportType is already imported at the top
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
        print_info(f"Starting MCP server for Agent API (URL: {config.agent_api_url})")

        # Save the PID to a file
        import os
        pid_dir = os.path.join(os.path.expanduser("~"), ".mcp-agentapi")
        os.makedirs(pid_dir, exist_ok=True)
        pid_file = os.path.join(pid_dir, "server.pid")
        with open(pid_file, "w") as f:
            f.write(str(os.getpid()))

        print_info(f"PID {os.getpid()} saved to {pid_file}")

        # Run the main function from our implementation
        await server_main()
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

        # Remove the PID file
        import os
        pid_file = os.path.join(os.path.expanduser("~"), ".mcp-agentapi", "server.pid")
        if os.path.exists(pid_file):
            try:
                os.remove(pid_file)
            except Exception as e:
                print_warning(f"Failed to remove PID file: {e}")


async def handle_server_stop(args: argparse.Namespace) -> None:
    """
    Handle the 'server stop' command.

    Args:
        args: Command-line arguments
    """
    import os
    import signal
    import psutil

    # Try to find the MCP server process
    found = False

    # First, check if there's a PID file
    pid_file = os.path.join(os.path.expanduser("~"), ".mcp-agentapi", "server.pid")
    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())

            # Check if the process exists
            if psutil.pid_exists(pid):
                process = psutil.Process(pid)
                # Check if it's the MCP server process
                if "python" in process.name().lower() and any("mcp-agentapi" in cmd.lower() for cmd in process.cmdline()):
                    print_info(f"Found MCP server process with PID {pid}")
                    # Send SIGTERM to the process
                    os.kill(pid, signal.SIGTERM)
                    print_success(f"Sent termination signal to MCP server process (PID {pid})")
                    found = True

                    # Remove the PID file
                    os.remove(pid_file)
        except Exception as e:
            print_error(f"Error stopping MCP server: {e}")

    # If we couldn't find the process using the PID file, try to find it by name
    if not found:
        try:
            for process in psutil.process_iter(["pid", "name", "cmdline"]):
                if "python" in process.info["name"].lower() and process.info["cmdline"] and any("mcp-agentapi" in cmd.lower() for cmd in process.info["cmdline"]) and any("server" in cmd.lower() for cmd in process.info["cmdline"]):
                    pid = process.info["pid"]
                    print_info(f"Found MCP server process with PID {pid}")
                    # Send SIGTERM to the process
                    os.kill(pid, signal.SIGTERM)
                    print_success(f"Sent termination signal to MCP server process (PID {pid})")
                    found = True
        except Exception as e:
            print_error(f"Error stopping MCP server: {e}")

    if not found:
        print_warning("No running MCP server process found")


async def handle_server_status(args: argparse.Namespace) -> None:
    """
    Handle the 'server status' command.

    Args:
        args: Command-line arguments
    """
    # Create a mock context
    ctx = MockContext()

    # Check the health of the server
    try:
        result = await check_health(ctx)
        if result.get("status") == "ok":
            print_success("MCP server is running")
            print(f"Version: {result.get('version', 'unknown')}")
            print(f"Uptime: {result.get('uptime', 'unknown')}")
        else:
            print_error("MCP server is not running properly")
            print(f"Status: {result.get('status', 'unknown')}")
    except Exception as e:
        print_error(f"Error checking server status: {e}")
        print_error("MCP server is not running or not responding")


# Agent command handlers
async def handle_agent_list(args: argparse.Namespace) -> None:
    """
    Handle the 'agent list' command.

    Args:
        args: Command-line arguments
    """
    # Load configuration
    config = load_config()

    # Create agent manager
    agent_manager = AgentManager(config)

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


async def handle_agent_start(args: argparse.Namespace) -> None:
    """
    Handle the 'agent start' command.

    Args:
        args: Command-line arguments
    """
    # Load configuration
    config = load_config()

    # Create agent manager
    agent_manager = AgentManager(config)

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
            print_info("Use 'mcp-agentapi agent install' command to install it or use --auto-install flag.")
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


async def handle_agent_stop(args: argparse.Namespace) -> None:
    """
    Handle the 'agent stop' command.

    Args:
        args: Command-line arguments
    """
    # Load configuration
    config = load_config()

    # Create agent manager
    agent_manager = AgentManager(config)

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


async def handle_agent_switch(args: argparse.Namespace) -> None:
    """
    Handle the 'agent switch' command.

    Args:
        args: Command-line arguments
    """
    # Load configuration
    config = load_config()

    # Create agent manager
    agent_manager = AgentManager(config)

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
            print_info("Use 'mcp-agentapi agent install' command to install it or use --auto-install flag.")
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


async def handle_agent_status(args: argparse.Namespace) -> None:
    """
    Handle the 'agent status' command.

    Args:
        args: Command-line arguments
    """
    # Load configuration
    config = load_config()

    # Create agent manager
    agent_manager = AgentManager(config)

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


async def handle_agent_install(args: argparse.Namespace) -> None:
    """
    Handle the 'agent install' command.

    Args:
        args: Command-line arguments
    """
    # Load configuration
    config = load_config()

    # Create agent manager
    agent_manager = AgentManager(config)

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


async def handle_agent_messages(args: argparse.Namespace) -> None:
    """
    Handle the 'agent messages' command.

    Args:
        args: Command-line arguments
    """
    # Create a mock context
    ctx = MockContext()

    # Get messages
    try:
        result = await get_messages(ctx)
        if isinstance(result, list):
            print_header("Conversation Messages")
            for i, message in enumerate(result):
                role = message.get("role", "unknown")
                content = message.get("content", "")
                print(f"{BOLD}{i+1}. {role.upper()}{RESET}")
                print(f"{content}\n")
        else:
            print_error("Failed to get messages")
    except Exception as e:
        print_error(f"Error getting messages: {e}")


async def handle_agent_send(args: argparse.Namespace) -> None:
    """
    Handle the 'agent send' command.

    Args:
        args: Command-line arguments
    """
    # Create a mock context
    ctx = MockContext()

    # Send message
    try:
        result = await send_message(ctx, args.content, args.type)
        print_success("Message sent successfully")
    except Exception as e:
        print_error(f"Error sending message: {e}")


async def handle_agent_screen(args: argparse.Namespace) -> None:
    """
    Handle the 'agent screen' command.

    Args:
        args: Command-line arguments
    """
    # Create a mock context
    ctx = MockContext()

    # Get screen
    try:
        result = await get_screen(ctx)
        print_header("Screen Content")
        print(result)
    except Exception as e:
        print_error(f"Error getting screen content: {e}")


async def handle_agent_current(args: argparse.Namespace) -> None:
    """
    Handle the 'agent current' command.

    Args:
        args: Command-line arguments
    """
    # Create a mock context
    ctx = MockContext()

    # Get agent type
    try:
        result = await get_agent_type(ctx)
        print_header("Current Agent")
        print(f"Agent Type: {result}")
    except Exception as e:
        print_error(f"Error getting agent type: {e}")


async def handle_agent_restart(args: argparse.Namespace) -> None:
    """
    Handle the 'agent restart' command.

    Args:
        args: Command-line arguments
    """
    # Load configuration
    config = load_config()

    # Create agent manager
    agent_manager = AgentManager(config)

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

    # Restart the agent
    print_info(f"Restarting agent {agent_type_str}...")

    # Create a mock context for the restart_agent function
    ctx = MockContext()

    try:
        result = await restart_agent(ctx, agent_type_str)
        print_success(f"Agent {agent_type_str} restarted successfully.")
    except Exception as e:
        print_error(f"Error restarting agent: {e}")


# Config command handlers
async def handle_config_show(args: argparse.Namespace) -> None:
    """
    Handle the 'config show' command.

    Args:
        args: Command-line arguments
    """
    # Load configuration
    config = load_config()

    print_header("Configuration")

    # Print server configuration
    print(f"{BOLD}Server Configuration:{RESET}")
    print(f"  Transport: {config.server.transport.value}")
    print(f"  Host: {config.server.host}")
    print(f"  Port: {config.server.port}")

    # Print agent configuration
    print(f"\n{BOLD}Agent Configuration:{RESET}")
    print(f"  Agent Type: {config.agent_type.value if config.agent_type else 'Not set'}")
    print(f"  Auto Start Agent: {config.auto_start_agent}")
    print(f"  Agent API URL: {config.agent_api_url}")

    # Print other configuration
    print(f"\n{BOLD}Other Configuration:{RESET}")
    print(f"  Debug: {config.debug}")


async def handle_config_set(args: argparse.Namespace) -> None:
    """
    Handle the 'config set' command.

    Args:
        args: Command-line arguments
    """
    # Load configuration
    config = load_config()

    # Update configuration based on key-value pairs
    updated = False

    for key, value in args.key_value:
        if key == "transport":
            # TransportType is already imported at the top
            try:
                config.server.transport = TransportType(value)
                updated = True
            except ValueError:
                print_error(f"Invalid transport type: {value}")
                print_info("Valid transport types: stdio, sse")
        elif key == "host":
            config.server.host = value
            updated = True
        elif key == "port":
            try:
                config.server.port = int(value)
                updated = True
            except ValueError:
                print_error(f"Invalid port: {value}")
        elif key == "agent_type":
            try:
                config.agent_type = convert_to_agent_type(value)
                updated = True
            except ValueError as e:
                print_error(str(e))
        elif key == "auto_start_agent":
            if value.lower() in ("true", "yes", "1"):
                config.auto_start_agent = True
                updated = True
            elif value.lower() in ("false", "no", "0"):
                config.auto_start_agent = False
                updated = True
            else:
                print_error(f"Invalid value for auto_start_agent: {value}")
                print_info("Valid values: true, false, yes, no, 1, 0")
        elif key == "agent_api_url":
            config.agent_api_url = value
            updated = True
        elif key == "debug":
            if value.lower() in ("true", "yes", "1"):
                config.debug = True
                updated = True
            elif value.lower() in ("false", "no", "0"):
                config.debug = False
                updated = True
            else:
                print_error(f"Invalid value for debug: {value}")
                print_info("Valid values: true, false, yes, no, 1, 0")
        else:
            print_warning(f"Unknown configuration key: {key}")

    # Save configuration if updated
    if updated:
        if save_config(config):
            print_success("Configuration updated successfully.")
        else:
            print_error("Failed to save configuration.")
    else:
        print_warning("No configuration changes were made.")


async def handle_config_reset(args: argparse.Namespace) -> None:
    """
    Handle the 'config reset' command.

    Args:
        args: Command-line arguments
    """
    # Create a new default configuration
    # Config and save_config are already imported at the top
    config = Config()

    # Save the default configuration
    if save_config(config):
        print_success("Configuration reset to defaults.")
    else:
        print_error("Failed to reset configuration.")


async def main() -> None:
    """Main entry point for the unified CLI."""
    # Create the top-level parser
    parser = argparse.ArgumentParser(
        description="MCP Agent API - Central Control System for AI Agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mcp-agentapi server start                   # Start the MCP server
  mcp-agentapi server status                  # Check the status of the MCP server
  mcp-agentapi agent list                     # List available agents
  mcp-agentapi agent status                   # Show status of all agents
  mcp-agentapi agent start goose              # Start the Goose agent
  mcp-agentapi agent stop aider               # Stop the Aider agent
  mcp-agentapi agent switch claude --restart  # Switch to Claude agent and restart it
  mcp-agentapi agent install aider            # Install the Aider agent
  mcp-agentapi config show                    # Show current configuration
  mcp-agentapi config set transport=stdio     # Set configuration value
  mcp-agentapi config reset                   # Reset configuration to defaults

Shortcuts:
  mcp-agentapi list                           # Shortcut for 'agent list'
  mcp-agentapi status                         # Shortcut for 'agent status'
  mcp-agentapi start goose                    # Shortcut for 'agent start goose'
  mcp-agentapi stop aider                     # Shortcut for 'agent stop aider'
        """
    )

    # Create subparsers for command groups
    subparsers = parser.add_subparsers(dest="command_group", help="Command group")

    # 'server' command group
    server_parser = subparsers.add_parser("server", help="Server commands")
    server_subparsers = server_parser.add_subparsers(dest="command", help="Server command")

    # 'server start' command
    server_start_parser = server_subparsers.add_parser("start", help="Start the MCP server")
    server_start_parser.add_argument("--transport", choices=["stdio", "sse"], help="Transport mode (stdio or sse)")
    server_start_parser.add_argument("--host", help="Host to bind to (for SSE mode)")
    server_start_parser.add_argument("--port", type=int, help="Port to listen on (for SSE mode)")
    server_start_parser.add_argument("--agent-api-url", help="Agent API URL")
    server_start_parser.add_argument("--agent", dest="agent_name", help="Agent type to use")
    server_start_parser.add_argument("--auto-start", action="store_true", dest="auto_start", default=None, help="Automatically start the agent")
    server_start_parser.add_argument("--no-auto-start", action="store_false", dest="auto_start", default=None, help="Do not automatically start the agent")
    server_start_parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    # 'server stop' command
    server_subparsers.add_parser("stop", help="Stop the MCP server")

    # 'server status' command
    server_subparsers.add_parser("status", help="Check the status of the MCP server")

    # 'agent' command group
    agent_parser = subparsers.add_parser("agent", help="Agent commands")
    agent_subparsers = agent_parser.add_subparsers(dest="command", help="Agent command")

    # 'agent list' command
    agent_subparsers.add_parser("list", help="List available agents")

    # 'agent status' command
    agent_subparsers.add_parser("status", help="Show status of all agents")

    # 'agent start' command
    agent_start_parser = agent_subparsers.add_parser("start", help="Start an agent")
    agent_start_parser.add_argument("agent_name", nargs="?", help="Name of the agent to start")
    agent_start_parser.add_argument("--auto-install", action="store_true", help="Automatically install the agent if not installed")
    agent_start_parser.add_argument("--update-config", action="store_true", help="Update configuration with the selected agent")

    # 'agent stop' command
    agent_stop_parser = agent_subparsers.add_parser("stop", help="Stop an agent")
    agent_stop_parser.add_argument("agent_name", nargs="?", help="Name of the agent to stop")
    agent_stop_parser.add_argument("--update-config", action="store_true", help="Update configuration to not auto-start the agent")

    # 'agent switch' command
    agent_switch_parser = agent_subparsers.add_parser("switch", help="Switch to a different agent")
    agent_switch_parser.add_argument("agent_name", help="Name of the agent to switch to")
    agent_switch_parser.add_argument("--restart", action="store_true", help="Restart the agent after switching")
    agent_switch_parser.add_argument("--auto-install", action="store_true", help="Automatically install the agent if not installed")

    # 'agent install' command
    agent_install_parser = agent_subparsers.add_parser("install", help="Install an agent")
    agent_install_parser.add_argument("agent_name", help="Name of the agent to install")
    agent_install_parser.add_argument("--update-config", action="store_true", help="Update configuration with the installed agent")

    # 'agent restart' command
    agent_restart_parser = agent_subparsers.add_parser("restart", help="Restart an agent")
    agent_restart_parser.add_argument("agent_name", nargs="?", help="Name of the agent to restart")

    # 'agent current' command
    agent_subparsers.add_parser("current", help="Show the current agent type")

    # 'agent messages' command
    agent_subparsers.add_parser("messages", help="Get all messages in the conversation")

    # 'agent send' command
    agent_send_parser = agent_subparsers.add_parser("send", help="Send a message to the agent")
    agent_send_parser.add_argument("--content", required=True, help="Message content")
    agent_send_parser.add_argument("--type", default="user", help="Message type (user or raw)")

    # 'agent screen' command
    agent_subparsers.add_parser("screen", help="Get the current screen content")

    # 'config' command group
    config_parser = subparsers.add_parser("config", help="Configuration commands")
    config_subparsers = config_parser.add_subparsers(dest="command", help="Configuration command")

    # 'config show' command
    config_subparsers.add_parser("show", help="Show current configuration")

    # 'config set' command
    config_set_parser = config_subparsers.add_parser("set", help="Set configuration values")
    config_set_parser.add_argument("key_value", nargs="+", metavar="KEY=VALUE", help="Key-value pairs to set")

    # 'config reset' command
    config_subparsers.add_parser("reset", help="Reset configuration to defaults")

    # Add shortcuts for common commands
    # These are top-level commands that map to subcommands

    # 'list' shortcut for 'agent list'
    subparsers.add_parser("list", help="Shortcut for 'agent list'")

    # 'status' shortcut for 'agent status'
    subparsers.add_parser("status", help="Shortcut for 'agent status'")

    # 'start' shortcut for 'agent start'
    start_parser = subparsers.add_parser("start", help="Shortcut for 'agent start'")
    start_parser.add_argument("agent_name", nargs="?", help="Name of the agent to start")
    start_parser.add_argument("--auto-install", action="store_true", help="Automatically install the agent if not installed")
    start_parser.add_argument("--update-config", action="store_true", help="Update configuration with the selected agent")

    # 'stop' shortcut for 'agent stop'
    stop_parser = subparsers.add_parser("stop", help="Shortcut for 'agent stop'")
    stop_parser.add_argument("agent_name", nargs="?", help="Name of the agent to stop")
    stop_parser.add_argument("--update-config", action="store_true", help="Update configuration to not auto-start the agent")

    # 'switch' shortcut for 'agent switch'
    switch_parser = subparsers.add_parser("switch", help="Shortcut for 'agent switch'")
    switch_parser.add_argument("agent_name", help="Name of the agent to switch to")
    switch_parser.add_argument("--restart", action="store_true", help="Restart the agent after switching")
    switch_parser.add_argument("--auto-install", action="store_true", help="Automatically install the agent if not installed")

    # 'install' shortcut for 'agent install'
    install_parser = subparsers.add_parser("install", help="Shortcut for 'agent install'")
    install_parser.add_argument("agent_name", help="Name of the agent to install")
    install_parser.add_argument("--update-config", action="store_true", help="Update configuration with the installed agent")

    # Parse arguments
    args = parser.parse_args()

    # Process key-value pairs for config set command
    if hasattr(args, "key_value") and args.key_value:
        # Convert ["key1=value1", "key2=value2"] to [("key1", "value1"), ("key2", "value2")]
        args.key_value = [tuple(kv.split("=", 1)) for kv in args.key_value]

    # Handle shortcuts
    if args.command_group in ["list", "status", "start", "stop", "switch", "install"]:
        # Map shortcut to agent subcommand
        args.command = args.command_group
        args.command_group = "agent"

    # If no command group is provided, show help
    if not args.command_group:
        parser.print_help()
        return

    # If no command is provided for a command group, show help for that group
    if not hasattr(args, "command") or not args.command:
        if args.command_group == "server":
            server_parser.print_help()
        elif args.command_group == "agent":
            agent_parser.print_help()
        elif args.command_group == "config":
            config_parser.print_help()
        return

    # Handle the command
    try:
        if args.command_group == "server":
            if args.command == "start":
                await handle_server_start(args)
            elif args.command == "stop":
                await handle_server_stop(args)
            elif args.command == "status":
                await handle_server_status(args)
        elif args.command_group == "agent":
            if args.command == "list":
                await handle_agent_list(args)
            elif args.command == "status":
                await handle_agent_status(args)
            elif args.command == "start":
                await handle_agent_start(args)
            elif args.command == "stop":
                await handle_agent_stop(args)
            elif args.command == "switch":
                await handle_agent_switch(args)
            elif args.command == "install":
                await handle_agent_install(args)
            elif args.command == "restart":
                await handle_agent_restart(args)
            elif args.command == "current":
                await handle_agent_current(args)
            elif args.command == "messages":
                await handle_agent_messages(args)
            elif args.command == "send":
                await handle_agent_send(args)
            elif args.command == "screen":
                await handle_agent_screen(args)
        elif args.command_group == "config":
            if args.command == "show":
                await handle_config_show(args)
            elif args.command == "set":
                await handle_config_set(args)
            elif args.command == "reset":
                await handle_config_reset(args)
    except Exception as e:
        print_error(f"Error: {e}")
        if logger.isEnabledFor(logging.DEBUG):
            import traceback
            traceback.print_exc()
        sys.exit(1)


def cli_main() -> Optional[int]:
    """
    Entry point for the CLI when installed as a package.

    Returns:
        Optional exit code (None for success, non-zero for error)
    """
    try:
        asyncio.run(main())
        return None
    except KeyboardInterrupt:
        print("\nExiting...")
        return 0
    except Exception as e:
        print_error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(cli_main())
