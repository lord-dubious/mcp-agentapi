#!/usr/bin/env python3
"""
Unified CLI module for the MCP server for Agent API.

This module provides a command-line interface for managing agents and the MCP server,
including starting, stopping, switching between agents, and checking their status.
"""

import sys
import asyncio
import logging
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("agentapi-mcp")

# Import the main CLI function
from .src.cli import main as cli_main_impl


def main() -> Optional[int]:
    """
    Main entry point for the AgentAPI MCP CLI.
    This function is called when the user runs the agentapi-mcp command.
    
    Returns:
        Optional exit code (None for success, non-zero for error)
    """
    try:
        asyncio.run(cli_main_impl())
        return None
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Error running AgentAPI MCP CLI: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
