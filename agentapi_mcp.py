#!/usr/bin/env python3
"""
AgentAPI MCP - Command Line Interface

This module provides a unified command-line interface for the MCP server for Agent API.
It serves as the main entry point for the agentapi-mcp command.
"""

import sys
import asyncio
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("agentapi-mcp")

# Import the server module
from server import main as server_main


def cli_main():
    """
    Main entry point for the agentapi-mcp command.
    This function is called when the user runs the agentapi-mcp command.
    """
    try:
        # Run the server
        asyncio.run(server_main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error running MCP server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
