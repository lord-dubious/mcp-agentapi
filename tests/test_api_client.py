#!/usr/bin/env python3
"""
Tests for the API client module.

This module contains tests for the Agent API client functionality,
including making requests, handling errors, and processing responses.
"""

import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
import httpx

from src.api_client import AgentAPIClient, create_error_response
from src.models import AgentStatus, MessageType, ConversationRole
from src.exceptions import AgentAPIError, TimeoutError


def test_create_error_response():
    """Test creating a standardized error response."""
    # Test with minimal parameters
    response = create_error_response("Test error")
    assert response["error"] == "Test error"
    assert response["error_type"] == "AgentAPIError"
    assert response["status_code"] == 500
    assert "detail" not in response

    # Test with all parameters
    response = create_error_response(
        "Test error",
        error_type="ValidationError",
        status_code=400,
        detail="Invalid input"
    )
    assert response["error"] == "Test error"
    assert response["error_type"] == "ValidationError"
    assert response["status_code"] == 400
    assert response["detail"] == "Invalid input"


@pytest.mark.asyncio
async def test_make_request_success():
    """Test making a successful request."""
    # Mock the HTTP client
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "stable"}
    mock_client.get.return_value = mock_response

    # Create the API client
    client = AgentAPIClient(mock_client, "http://localhost:3284")

    # Make a request
    result = await client.make_request("status")

    # Verify the result
    assert result == {"status": "stable"}
    mock_client.get.assert_called_once_with(
        "http://localhost:3284/status",
        headers={
            "User-Agent": "mcp-agentapi/1.0",
            "Accept": "application/json"
        },
        params=None,
        timeout=30.0
    )


@pytest.mark.asyncio
async def test_make_request_http_error():
    """Test handling HTTP errors."""
    # Mock the HTTP client
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not Found", request=MagicMock(), response=mock_response
    )
    mock_response.text = "Not Found"
    mock_response.json.side_effect = json.JSONDecodeError("", "", 0)
    mock_client.get.return_value = mock_response

    # Create the API client
    client = AgentAPIClient(mock_client, "http://localhost:3284")

    # Make a request that should fail
    with pytest.raises(AgentAPIError) as excinfo:
        await client.make_request("status")

    # Verify the error
    assert "HTTP error 404" in str(excinfo.value)
    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_make_request_timeout():
    """Test handling timeout errors."""
    # Mock the HTTP client
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.TimeoutException("Timeout")

    # Create the API client
    client = AgentAPIClient(mock_client, "http://localhost:3284")

    # Make a request that should time out
    with pytest.raises(TimeoutError) as excinfo:
        await client.make_request("status")

    # Verify the error
    assert "Request timed out" in str(excinfo.value)
    assert excinfo.value.timeout == 30.0


@pytest.mark.asyncio
async def test_make_request_retry():
    """Test request retry logic."""
    # Mock the HTTP client
    mock_client = AsyncMock()
    
    # First call fails with a 503 error
    mock_response_1 = AsyncMock()
    mock_response_1.status_code = 503
    mock_response_1.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Service Unavailable", request=MagicMock(), response=mock_response_1
    )
    
    # Second call succeeds
    mock_response_2 = AsyncMock()
    mock_response_2.status_code = 200
    mock_response_2.json.return_value = {"status": "stable"}
    
    # Set up the mock to return different responses on successive calls
    mock_client.get.side_effect = [mock_response_1, mock_response_2]

    # Create the API client with a short retry delay
    client = AgentAPIClient(mock_client, "http://localhost:3284")

    # Patch asyncio.sleep to avoid actual delays
    with patch("asyncio.sleep", new_callable=AsyncMock):
        # Make a request that should retry and succeed
        result = await client.make_request(
            "status",
            retry_attempts=2,
            retry_for_statuses=[503],
            retry_initial_delay=0.1
        )

    # Verify the result
    assert result == {"status": "stable"}
    assert mock_client.get.call_count == 2


@pytest.mark.asyncio
async def test_get_status():
    """Test getting agent status."""
    # Mock the make_request method
    with patch.object(
        AgentAPIClient, "make_request", new_callable=AsyncMock
    ) as mock_make_request:
        mock_make_request.return_value = {"status": "stable"}

        # Create the API client
        client = AgentAPIClient(AsyncMock(), "http://localhost:3284")

        # Get status
        result = await client.get_status()

        # Verify the result
        assert result == {"status": "stable"}
        mock_make_request.assert_called_once_with("status")


@pytest.mark.asyncio
async def test_get_agent_status():
    """Test getting agent status as enum."""
    # Mock the get_status method
    with patch.object(
        AgentAPIClient, "get_status", new_callable=AsyncMock
    ) as mock_get_status:
        mock_get_status.return_value = {"status": "stable"}

        # Create the API client
        client = AgentAPIClient(AsyncMock(), "http://localhost:3284")

        # Get agent status
        result = await client.get_agent_status()

        # Verify the result
        assert result == AgentStatus.STABLE
        mock_get_status.assert_called_once()


@pytest.mark.asyncio
async def test_get_agent_type():
    """Test getting agent type."""
    # Mock the necessary methods
    with patch.object(
        AgentAPIClient, "get_status", new_callable=AsyncMock
    ) as mock_get_status, patch.object(
        AgentAPIClient, "get_messages", new_callable=AsyncMock
    ) as mock_get_messages:
        # Set up the mock responses
        mock_get_status.return_value = {"status": "stable", "agentType": "goose"}
        mock_get_messages.return_value = {"messages": []}

        # Create the API client
        client = AgentAPIClient(AsyncMock(), "http://localhost:3284")

        # Get agent type
        result = await client.get_agent_type()

        # Verify the result
        assert result == "goose"
        mock_get_status.assert_called_once()
        mock_get_messages.assert_not_called()


@pytest.mark.asyncio
async def test_send_message():
    """Test sending a message."""
    # Mock the make_request method
    with patch.object(
        AgentAPIClient, "make_request", new_callable=AsyncMock
    ) as mock_make_request:
        mock_make_request.return_value = {"ok": True}

        # Create the API client
        client = AgentAPIClient(AsyncMock(), "http://localhost:3284")

        # Send a message
        result = await client.send_message("Hello", MessageType.USER)

        # Verify the result
        assert result == {"ok": True}
        mock_make_request.assert_called_once_with(
            "message",
            method="POST",
            json_data={"content": "Hello", "type": "user"}
        )


@pytest.mark.asyncio
async def test_get_messages():
    """Test getting messages."""
    # Mock the make_request method
    with patch.object(
        AgentAPIClient, "make_request", new_callable=AsyncMock
    ) as mock_make_request:
        mock_make_request.return_value = {
            "messages": [
                {
                    "id": 1,
                    "content": "Hello",
                    "role": "user",
                    "time": "2023-01-01T00:00:00Z"
                },
                {
                    "id": 2,
                    "content": "Hi there!",
                    "role": "agent",
                    "time": "2023-01-01T00:00:01Z"
                }
            ]
        }

        # Create the API client
        client = AgentAPIClient(AsyncMock(), "http://localhost:3284")

        # Get messages
        result = await client.get_messages()

        # Verify the result
        assert len(result["messages"]) == 2
        assert result["messages"][0]["content"] == "Hello"
        assert result["messages"][1]["content"] == "Hi there!"
        mock_make_request.assert_called_once_with("messages")


@pytest.mark.asyncio
async def test_get_message_list():
    """Test getting messages as a list of Message objects."""
    # Mock the get_messages method
    with patch.object(
        AgentAPIClient, "get_messages", new_callable=AsyncMock
    ) as mock_get_messages:
        mock_get_messages.return_value = {
            "messages": [
                {
                    "id": 1,
                    "content": "Hello",
                    "role": "user",
                    "time": "2023-01-01T00:00:00Z"
                },
                {
                    "id": 2,
                    "content": "Hi there!",
                    "role": "agent",
                    "time": "2023-01-01T00:00:01Z"
                }
            ]
        }

        # Create the API client
        client = AgentAPIClient(AsyncMock(), "http://localhost:3284")

        # Get message list
        result = await client.get_message_list()

        # Verify the result
        assert len(result) == 2
        assert result[0].content == "Hello"
        assert result[0].role == ConversationRole.USER
        assert result[1].content == "Hi there!"
        assert result[1].role == ConversationRole.AGENT
        mock_get_messages.assert_called_once()
