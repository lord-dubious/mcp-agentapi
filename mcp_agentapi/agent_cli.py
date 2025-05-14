#!/usr/bin/env python3
"""
Agent CLI - Command Line Interface for the MCP server.

This module provides a command-line interface for the MCP server for Agent API.
It allows users to interact with agents through the Agent API.
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
logger = logging.getLogger("agent-cli")

# Import the agent controller
from .agent_controller import run_cli


def main() -> Optional[int]:
    """
    Main entry point for the agent-cli command.
    This function is called when the user runs the agent-cli command.
    
    Returns:
        Optional exit code (None for success, non-zero for error)
    """
    try:
        asyncio.run(run_cli())
        return None
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Error running agent CLI: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
