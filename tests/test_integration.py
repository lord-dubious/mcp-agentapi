#!/usr/bin/env python3
"""
Integration tests for the MCP server.

This module contains integration tests for the MCP server using the MCP SDK's testing utilities.
"""

import os
import sys
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mcp.server.fastmcp import FastMCP, Context
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from src.models import AgentType
from src.context import AgentAPIContext
from server import mcp as server_mcp


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_available_agents():
    """Test the list_available_agents tool."""
    # Create a mock context
    context = MagicMock(spec=Context)
    app_context = MagicMock(spec=AgentAPIContext)
    context.request_context.lifespan_context = app_context

    # Set up the agent manager
    app_context.agent_manager = AsyncMock()
    app_context.agent_manager.detect_agents.return_value = {
        AgentType.GOOSE: MagicMock(),
        AgentType.AIDER: MagicMock(),
        AgentType.CLAUDE: MagicMock(),
    }

    # Import the tool
    from server import list_available_agents

    # Call the tool
    result = await list_available_agents(context)

    # Check the result
    assert isinstance(result, dict)
    assert "agents" in result
    assert len(result["agents"]) == 3
    assert "goose" in result["agents"]
    assert "aider" in result["agents"]
    assert "claude" in result["agents"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_agent_type():
    """Test the get_agent_type tool."""
    # Create a mock context
    context = MagicMock(spec=Context)
    app_context = MagicMock(spec=AgentAPIContext)
    context.request_context.lifespan_context = app_context

    # Set up the agent type
    app_context.agent_type = AgentType.GOOSE

    # Import the tool
    from server import get_agent_type

    # Call the tool
    result = await get_agent_type(context)

    # Check the result
    assert result == "goose"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_check_health():
    """Test the check_health tool."""
    # Create a mock context
    context = MagicMock(spec=Context)
    app_context = MagicMock(spec=AgentAPIContext)
    context.request_context.lifespan_context = app_context

    # Set up the health check
    app_context.health_check = AsyncMock()
    app_context.health_check.check_health.return_value = {
        "status": "healthy",
        "agent_api": "running",
        "agent": "running",
    }

    # Import the tool
    from server import check_health

    # Call the tool
    result = await check_health(context)

    # Check the result
    assert isinstance(result, dict)
    assert "status" in result
    assert result["status"] == "healthy"
    assert "agent_api" in result
    assert result["agent_api"] == "running"
    assert "agent" in result
    assert result["agent"] == "running"
