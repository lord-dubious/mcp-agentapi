#!/usr/bin/env python3
"""
Agent CLI - Command Line Interface for the MCP server.

This script provides a command-line interface for the MCP server for Agent API.
It allows users to interact with agents through the Agent API.
"""

import sys
import asyncio

# Add the current directory to the Python path
sys.path.insert(0, '.')

# Import the agent controller
from src.agent_controller import run_cli


def main():
    """
    Main entry point for the agent-cli command.
    This function is called when the user runs the agent-cli command.
    """
    asyncio.run(run_cli())


if __name__ == "__main__":
    main()
