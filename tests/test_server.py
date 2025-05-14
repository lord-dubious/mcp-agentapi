#!/usr/bin/env python3
"""
Tests for the MCP server.

This module contains tests for the MCP server functionality,
including tools, resources, and prompts.
"""

import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from mcp.server.fastmcp import Context

# Import the server module
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import (
    get_agent_type, list_available_agents, install_agent, start_agent,
    stop_agent, restart_agent, get_status, check_health, get_messages,
    send_message, get_screen, get_agent_info, get_openapi_schema
)
from src.context import AgentAPIContext
from src.models import AgentType, MessageType, AgentStatus
from src.exceptions import AgentAPIError


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    app_context = MagicMock(spec=AgentAPIContext)
    context.request_context.lifespan_context = app_context

    # Set up the agent manager
    app_context.agent_manager = MagicMock()
    app_context.agent_manager.agents = {
        AgentType.GOOSE: MagicMock(),
        AgentType.AIDER: MagicMock(),
        AgentType.CLAUDE: MagicMock(),
        AgentType.CODEX: MagicMock(),
        AgentType.CUSTOM: MagicMock()
    }

    # Set up the HTTP client
    app_context.http_client = MagicMock()

    # Set up the agent API URL
    app_context.agent_api_url = "http://localhost:3284"

    # Set up the agent type
    app_context.agent_type = AgentType.GOOSE

    # Set up the config
    app_context.config = MagicMock()
    app_context.config.agent_type = AgentType.GOOSE
    app_context.config.agent_api_url = "http://localhost:3284"

    # Set up the health check
    app_context.health_check = MagicMock()

    return context


@pytest.mark.asyncio
async def test_get_agent_type(mock_context):
    """Test the get_agent_type tool."""
    # Mock the API client
    with patch("src.api_client.AgentAPIClient", new_callable=MagicMock) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.get_agent_type = AsyncMock(return_value="goose")

        # Call the tool
        result = await get_agent_type(mock_context)

        # Verify the result
        assert result == "goose"
        mock_client.get_agent_type.assert_called_once()


@pytest.mark.asyncio
async def test_list_available_agents(mock_context):
    """Test the list_available_agents tool."""
    # Mock the agent manager
    mock_context.request_context.lifespan_context.agent_manager.detect_agents = AsyncMock()
    mock_context.request_context.lifespan_context.agent_manager.detect_agents.return_value = {
        AgentType.GOOSE: MagicMock(),
        AgentType.AIDER: MagicMock(),
        AgentType.CLAUDE: MagicMock(),
        AgentType.CODEX: MagicMock(),
        AgentType.CUSTOM: MagicMock()
    }

    # Call the tool
    result = await list_available_agents(mock_context)

    # Verify the result
    assert "agents" in result
    assert len(result["agents"]) == 5
    assert "goose" in result["agents"]
    assert "aider" in result["agents"]
    assert "claude" in result["agents"]
    assert "codex" in result["agents"]
    assert "custom" in result["agents"]
    mock_context.request_context.lifespan_context.agent_manager.detect_agents.assert_called_once()


@pytest.mark.asyncio
async def test_install_agent(mock_context):
    """Test the install_agent tool."""
    # Mock the agent manager
    mock_context.request_context.lifespan_context.agent_manager.install_agent = AsyncMock(return_value=True)

    # Call the tool
    result = await install_agent(mock_context, "goose")

    # Verify the result
    assert "installed successfully" in result
    mock_context.request_context.lifespan_context.agent_manager.install_agent.assert_called_once_with(AgentType.GOOSE)

    # Test with invalid agent type
    result = await install_agent(mock_context, "invalid")

    # Verify the result
    assert "Error: Invalid agent type" in result
    assert mock_context.request_context.lifespan_context.agent_manager.install_agent.call_count == 1


@pytest.mark.asyncio
async def test_start_agent(mock_context):
    """Test the start_agent tool."""
    # Mock the agent manager
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_context.request_context.lifespan_context.agent_manager.start_agent = AsyncMock(return_value=mock_process)

    # Call the tool
    result = await start_agent(mock_context, "goose")

    # Verify the result
    assert "started successfully" in result
    assert "12345" in result
    mock_context.request_context.lifespan_context.agent_manager.start_agent.assert_called_once_with(AgentType.GOOSE)
    assert mock_context.request_context.lifespan_context.agent_type == AgentType.GOOSE

    # Test with invalid agent type
    result = await start_agent(mock_context, "invalid")

    # Verify the result
    assert "Error: Invalid agent type" in result
    assert mock_context.request_context.lifespan_context.agent_manager.start_agent.call_count == 1


@pytest.mark.asyncio
async def test_stop_agent(mock_context):
    """Test the stop_agent tool."""
    # Mock the agent manager
    mock_context.request_context.lifespan_context.agent_manager.stop_agent = AsyncMock(return_value=True)

    # Call the tool
    result = await stop_agent(mock_context, "goose")

    # Verify the result
    assert "stopped successfully" in result
    mock_context.request_context.lifespan_context.agent_manager.stop_agent.assert_called_once_with(AgentType.GOOSE)

    # Test with invalid agent type
    result = await stop_agent(mock_context, "invalid")

    # Verify the result
    assert "Error: Invalid agent type" in result
    assert mock_context.request_context.lifespan_context.agent_manager.stop_agent.call_count == 1


@pytest.mark.asyncio
async def test_restart_agent(mock_context):
    """Test the restart_agent tool."""
    # Mock the agent manager
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_context.request_context.lifespan_context.agent_manager.stop_agent = AsyncMock(return_value=True)
    mock_context.request_context.lifespan_context.agent_manager.start_agent = AsyncMock(return_value=mock_process)

    # Call the tool
    result = await restart_agent(mock_context, "goose")

    # Verify the result
    assert "restarted successfully" in result
    assert "12345" in result
    mock_context.request_context.lifespan_context.agent_manager.stop_agent.assert_called_once_with(AgentType.GOOSE)
    mock_context.request_context.lifespan_context.agent_manager.start_agent.assert_called_once_with(AgentType.GOOSE)
    assert mock_context.request_context.lifespan_context.agent_type == AgentType.GOOSE

    # Test with invalid agent type
    result = await restart_agent(mock_context, "invalid")

    # Verify the result
    assert "Error: Invalid agent type" in result
    assert mock_context.request_context.lifespan_context.agent_manager.stop_agent.call_count == 1
    assert mock_context.request_context.lifespan_context.agent_manager.start_agent.call_count == 1


@pytest.mark.asyncio
async def test_get_status(mock_context):
    """Test the get_status tool."""
    # Mock the API client
    with patch("src.api_client.AgentAPIClient", new_callable=MagicMock) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.get_status = AsyncMock(return_value={"status": "stable"})

        # Call the tool
        result = await get_status(mock_context)

        # Verify the result
        assert result == "stable"
        mock_client.get_status.assert_called_once()


@pytest.mark.asyncio
async def test_check_health(mock_context):
    """Test the check_health tool."""
    # Mock the health check
    mock_context.request_context.lifespan_context.health_check.check_health = AsyncMock(
        return_value={"status": "healthy"}
    )

    # Call the tool
    result = await check_health(mock_context)

    # Verify the result
    assert result == {"status": "healthy"}
    mock_context.request_context.lifespan_context.health_check.check_health.assert_called_once()


@pytest.mark.asyncio
async def test_get_messages(mock_context):
    """Test the get_messages tool."""
    # Mock the API client
    with patch("src.api_client.AgentAPIClient", new_callable=MagicMock) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.get_messages = AsyncMock(
            return_value={"messages": [{"id": 1, "content": "Hello", "role": "user"}]}
        )

        # Call the tool
        result = await get_messages(mock_context)

        # Verify the result
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert result["messages"][0]["content"] == "Hello"
        mock_client.get_messages.assert_called_once()


@pytest.mark.asyncio
async def test_send_message(mock_context):
    """Test the send_message tool."""
    # Mock the API client
    with patch("src.api_client.AgentAPIClient", new_callable=MagicMock) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.send_message = AsyncMock(return_value={"ok": True})

        # Call the tool
        result = await send_message(mock_context, "Hello", "user")

        # Verify the result
        assert result == {"ok": True}
        mock_client.send_message.assert_called_once_with("Hello", MessageType.USER)

        # Test with invalid message type
        mock_client.send_message.reset_mock()
        result = await send_message(mock_context, "Hello", "invalid")

        # Verify the result
        assert "error" in result
        assert "Invalid message type" in result["error"]
        mock_client.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_get_screen(mock_context):
    """Test the get_screen tool."""
    # Mock the API client
    with patch("src.api_client.AgentAPIClient", new_callable=MagicMock) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.get_screen = AsyncMock(return_value="Screen content")

        # Call the tool
        result = await get_screen(mock_context)

        # Verify the result
        assert "screen" in result
        assert result["screen"] == "Screen content"
        mock_client.get_screen.assert_called_once()


@pytest.mark.asyncio
async def test_get_agent_info(mock_context):
    """Test the get_agent_info resource."""
    # Call the resource
    result = await get_agent_info(mock_context)

    # Verify the result
    result_dict = json.loads(result)
    assert "server" in result_dict
    assert result_dict["server"]["name"] == "AgentAPI-MCP"
    assert result_dict["server"]["agent_api_url"] == "http://localhost:3284"
    assert result_dict["server"]["agent_type"] == "goose"


@pytest.mark.asyncio
async def test_get_openapi_schema(mock_context):
    """Test the get_openapi_schema resource."""
    # Mock the API client
    with patch("src.api_client.AgentAPIClient", new_callable=MagicMock) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.get_openapi_schema = AsyncMock(
            return_value={"openapi": "3.0.0", "info": {"title": "Agent API"}}
        )

        # Call the resource
        result = await get_openapi_schema(mock_context)

        # Verify the result
        result_dict = json.loads(result)
        assert "openapi" in result_dict
        assert result_dict["openapi"] == "3.0.0"
        assert "info" in result_dict
        assert result_dict["info"]["title"] == "Agent API"
        mock_client.get_openapi_schema.assert_called_once()


# Prompt tests removed as the prompts were unused and removed from the server
