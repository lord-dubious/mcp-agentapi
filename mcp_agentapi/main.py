#!/usr/bin/env python3
"""
MCP Server for Agent API - Main Entry Point

This module provides the main entry point for the MCP server for Agent API
when installed as a package. It imports and runs the main function from server.py.
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
logger = logging.getLogger("mcp-server-agentapi")

# Import the server module
from .server import main as server_main


def main() -> Optional[int]:
    """
    Main entry point for the MCP server for Agent API.
    This function is called when the package is run as a module.
    
    Returns:
        Optional exit code (None for success, non-zero for error)
    """
    try:
        # Run the server
        asyncio.run(server_main())
        return None
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Error running MCP server: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
