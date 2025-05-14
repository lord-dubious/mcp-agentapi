#!/usr/bin/env python3
"""
MCP Server for Agent API - Command Line Interface

This script provides a command-line interface for the MCP server for Agent API.
It allows users to start the server with various options and configurations.
"""

import os
import sys
import asyncio
import subprocess

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the server module
from server import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
