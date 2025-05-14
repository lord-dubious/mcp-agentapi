#!/usr/bin/env python3
"""
Agent API client for the MCP server.

This module contains the client for communicating with the Agent API.
It provides methods for interacting with all Agent API endpoints,
including status, messages, events, and more.
"""

import asyncio
import json
import logging
import random
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union, Callable

import httpx
from mcp.server.fastmcp import FastMCP

from .models import (
    AgentStatus, ConversationRole, Message, MessageType
)
from .exceptions import AgentAPIError, TimeoutError, EventStreamError
from .constants import (
    SNAPSHOT_INTERVAL, EVENT_BUFFER_SIZE, USER_AGENT,
    DEFAULT_TIMEOUT, DEFAULT_RECONNECT_DELAY, MAX_RECONNECT_ATTEMPTS,
    DEFAULT_RETRY_ATTEMPTS, DEFAULT_RETRY_INITIAL_DELAY, DEFAULT_RETRY_MAX_DELAY,
    DEFAULT_RETRY_BACKOFF_FACTOR, DEFAULT_RETRY_JITTER, CORS_HEADERS
)
from .utils.error_handler import create_error_response, handle_exception, add_cors_headers

# Configure logging
logger = logging.getLogger("mcp-agentapi.api-client")


class AgentAPIClient:
    """
    Client for interacting with the Agent API.

    This class provides methods for communicating with the Agent API,
    including getting status, messages, sending messages, and streaming events.

    Attributes:
        http_client: HTTP client for making requests
        agent_api_url: URL of the Agent API server
        logger: Logger instance
    """

    def __init__(self, http_client: httpx.AsyncClient, agent_api_url: str):
        """
        Initialize the Agent API client.

        Args:
            http_client: HTTP client for making requests
            agent_api_url: URL of the Agent API server
        """
        self.http_client = http_client
        self.agent_api_url = agent_api_url.rstrip('/')
        self.logger = logger

    async def make_request(
        self,
        endpoint: str,
        method: str = "GET",
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,  # Add support for custom headers
        params: Optional[Dict[str, str]] = None,  # Add support for query parameters
        timeout: float = DEFAULT_TIMEOUT,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        retry_for_statuses: Optional[List[int]] = None,
        retry_initial_delay: float = DEFAULT_RETRY_INITIAL_DELAY,
        retry_max_delay: float = DEFAULT_RETRY_MAX_DELAY,
        retry_backoff_factor: float = DEFAULT_RETRY_BACKOFF_FACTOR,
        retry_jitter: float = DEFAULT_RETRY_JITTER
    ) -> Dict[str, Any]:
        """
        Make a request to the Agent API with proper error handling and retry logic.

        This method implements exponential backoff with jitter for retrying failed requests.
        It will retry for network errors and optionally for specific HTTP status codes.

        Args:
            endpoint: The endpoint to request (without the base URL)
            method: HTTP method to use (GET, POST, etc.)
            json_data: Optional JSON data to send with the request
            headers: Optional custom headers to include in the request
            params: Optional query parameters to include in the request URL
            timeout: Request timeout in seconds
            retry_attempts: Maximum number of retry attempts
            retry_for_statuses: List of HTTP status codes to retry for (default: [429, 500, 502, 503, 504])
            retry_initial_delay: Initial delay between retries in seconds
            retry_max_delay: Maximum delay between retries in seconds
            retry_backoff_factor: Factor to increase delay for each retry
            retry_jitter: Random jitter factor to add to delay (0.0 to 1.0)

        Returns:
            A dictionary containing the JSON response if successful

        Raises:
            AgentAPIError: If the request fails after all retry attempts
            TimeoutError: If the request times out after all retry attempts
        """
        url = f"{self.agent_api_url}/{endpoint.lstrip('/')}"

        # Set default headers with proper content negotiation to match the original Agent API
        default_headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json" if method == "POST" else None
        }

        # Remove None values from default headers
        default_headers = {k: v for k, v in default_headers.items() if v is not None}

        # Merge with custom headers if provided
        if headers:
            default_headers.update(headers)

        headers = default_headers

        # Default retry status codes if not provided
        if retry_for_statuses is None:
            retry_for_statuses = [429, 500, 502, 503, 504]  # Common transient errors

        # Initialize retry counter and delay
        attempt = 0
        delay = retry_initial_delay

        while True:
            attempt += 1
            last_attempt = attempt >= retry_attempts

            try:
                if method == "GET":
                    response = await self.http_client.get(url, headers=headers, params=params, timeout=timeout)
                elif method == "POST":
                    response = await self.http_client.post(url, headers=headers, json=json_data, params=params, timeout=timeout)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Check if we got a status code that should be retried
                if response.status_code in retry_for_statuses and not last_attempt:
                    retry_reason = f"status code {response.status_code}"
                    should_retry = True
                else:
                    # For other status codes, raise for status as usual
                    response.raise_for_status()
                    # If we get here, the request was successful
                    return response.json()

            except httpx.HTTPStatusError as e:
                # For HTTP errors, we only retry specific status codes
                if e.response.status_code in retry_for_statuses and not last_attempt:
                    retry_reason = f"HTTP error {e.response.status_code}"
                    should_retry = True
                else:
                    # For other status codes or on the last attempt, we raise the error
                    error_message = f"HTTP error {e.response.status_code} for {url}"
                    error_context = {
                        "url": url,
                        "method": method,
                        "status_code": e.response.status_code
                    }

                    # Try to parse the error response as JSON
                    try:
                        error_data = e.response.json()
                        if "error" in error_data:
                            error_message = f"{error_message}: {error_data['error']}"
                            error_context["error_data"] = error_data
                        elif "detail" in error_data:
                            error_message = f"{error_message}: {error_data['detail']}"
                            error_context["error_data"] = error_data
                    except Exception:
                        # If we can't parse the response as JSON, include the raw text
                        error_context["response_text"] = e.response.text

                    self.logger.error(error_message)

                    # Create a standardized error response
                    exception = AgentAPIError(
                        message=error_message,
                        status_code=e.response.status_code,
                        response_text=e.response.text,
                        context=error_context
                    )

                    # Use the standardized error handler
                    raise exception

            except httpx.TimeoutException as e:
                if not last_attempt:
                    retry_reason = "timeout"
                    should_retry = True
                else:
                    error_message = f"Request timed out for {url} after {timeout} seconds"
                    self.logger.error(error_message)

                    # Create a context with detailed information
                    error_context = {
                        "url": url,
                        "method": method,
                        "timeout": timeout,
                        "retry_attempts": retry_attempts,
                        "operation": f"{method} {endpoint}"
                    }

                    # Create a standardized error response
                    exception = TimeoutError(
                        message=error_message,
                        operation=f"{method} {endpoint}",
                        timeout=timeout,
                        context=error_context
                    )

                    # Use the standardized error handler
                    raise exception from e

            except httpx.RequestError as e:
                if not last_attempt:
                    retry_reason = f"request error: {str(e)}"
                    should_retry = True
                else:
                    error_message = f"Request error for {url}: {str(e)}"
                    self.logger.error(error_message)

                    # Create a context with detailed information
                    error_context = {
                        "url": url,
                        "method": method,
                        "error_type": type(e).__name__,
                        "retry_attempts": retry_attempts,
                        "operation": f"{method} {endpoint}"
                    }

                    # Create a standardized error response
                    exception = AgentAPIError(
                        message=error_message,
                        context=error_context
                    )

                    # Use the standardized error handler
                    raise exception from e

            except Exception as e:
                # For unexpected errors, we don't retry
                error_message = f"Error making request to {url}: {str(e)}"
                self.logger.error(error_message)

                # Create a context with detailed information
                error_context = {
                    "url": url,
                    "method": method,
                    "error_type": type(e).__name__,
                    "operation": f"{method} {endpoint}"
                }

                # Capture stack trace for debugging
                import traceback
                error_context["traceback"] = traceback.format_exc()

                # Create a standardized error response
                exception = AgentAPIError(
                    message=error_message,
                    context=error_context
                )

                # Use the standardized error handler
                raise exception from e

            # If we should retry, calculate the next delay with exponential backoff and jitter
            if should_retry:
                # Calculate the next delay with exponential backoff
                delay = min(delay * retry_backoff_factor, retry_max_delay)

                # Add jitter to avoid thundering herd problem
                jitter_amount = delay * retry_jitter
                actual_delay = delay + random.uniform(-jitter_amount, jitter_amount)
                actual_delay = max(0.1, actual_delay)  # Ensure delay is at least 0.1 seconds

                self.logger.warning(
                    f"Retrying request to {url} due to {retry_reason} "
                    f"(attempt {attempt}/{retry_attempts}, delay: {actual_delay:.2f}s)"
                )

                # Wait before retrying
                await asyncio.sleep(actual_delay)

    async def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the agent.

        Returns:
            A dictionary containing the status information with the following structure:
            {
                "status": "stable" | "running",
                "agentType": "claude" | "goose" | "aider" | "codex" | "custom"
            }

        Raises:
            AgentAPIError: If the request fails
        """
        return await self.make_request("status")

    async def get_agent_status(self) -> AgentStatus:
        """
        Get the current status of the agent as an enum value.

        Returns:
            The agent status as an AgentStatus enum value

        Raises:
            AgentAPIError: If the request fails
        """
        status_data = await self.get_status()
        status_str = status_data.get("status", "unknown")

        try:
            return AgentStatus(status_str)
        except ValueError:
            self.logger.warning(f"Unknown agent status: {status_str}")
            return AgentStatus.RUNNING  # Default to running if unknown

    async def get_agent_type(self) -> str:
        """
        Get the type of the agent from the Agent API.

        This method attempts to determine the agent type using multiple strategies:
        1. Checking the "agentType" field in the status response (added by our MCP server)
        2. Analyzing the agent's output patterns in messages
        3. Examining the command used to start the agent (if available)
        4. Looking for agent-specific keywords in the status response

        The detection follows the same approach as the original Agent API, ensuring
        compatibility with the original implementation.

        Returns:
            The agent type as a string (claude, goose, aider, codex, or custom)

        Raises:
            AgentAPIError: If the request fails
        """
        try:
            # Define agent-specific patterns for detection
            agent_patterns = {
                "claude": [
                    "claude", "anthropic", "assistant", "claude-3", "claude-2",
                    "claude-instant", "claude-sonnet", "claude-haiku"
                ],
                "goose": [
                    "goose", "google", "gemini", "bard", "palm", "block's ai assistant",
                    "( o)>", "(o )>"
                ],
                "aider": [
                    "aider", "coding assistant", "git", "repo", "repository", "commit",
                    "v0.", "tokens:", "main model:", "weak model:"
                ],
                "codex": [
                    "codex", "openai", "gpt", "code assistant", "davinci", "code-davinci",
                    "code interpreter"
                ]
            }

            # Strategy 1: Check the status endpoint for agentType field
            try:
                status_data = await self.get_status()

                # The Agent API might return the agent type in the "agentType" field
                # (This is an extension added by our MCP server)
                agent_type = status_data.get("agentType", "").lower()

                if agent_type and agent_type != "unknown" and agent_type in [
                    "claude", "goose", "aider", "codex", "custom"
                ]:
                    self.logger.info(f"Agent type detected from status endpoint: {agent_type}")
                    return agent_type
            except Exception as status_error:
                self.logger.debug(f"Error getting status for agent type detection: {status_error}")

            # Strategy 2: Analyze messages for agent-specific patterns
            try:
                messages = await self.get_messages()
                if messages and "messages" in messages:
                    # Look at all agent messages, prioritizing the most recent ones
                    agent_messages = []
                    for msg in messages["messages"]:
                        if msg.get("role") == "agent":
                            agent_messages.append(msg.get("content", "").lower())

                    # Reverse to check most recent messages first
                    for content in reversed(agent_messages):
                        # Check each agent type's patterns
                        for agent_type, patterns in agent_patterns.items():
                            for pattern in patterns:
                                if pattern in content:
                                    self.logger.info(f"Agent type inferred as '{agent_type}' from message content (pattern: {pattern})")
                                    return agent_type

                    # If we have agent messages but couldn't identify the type,
                    # do a more thorough analysis of the first message which often contains
                    # the agent's introduction
                    if agent_messages:
                        first_message = agent_messages[0] if agent_messages else ""

                        # Check for more specific patterns in the first message
                        if "i'm goose" in first_message or "block's ai assistant" in first_message:
                            self.logger.info("Agent type inferred as 'goose' from first message")
                            return "goose"
                        elif "aider v" in first_message:
                            self.logger.info("Agent type inferred as 'aider' from first message")
                            return "aider"
                        elif "i'm claude" in first_message or "anthropic" in first_message:
                            self.logger.info("Agent type inferred as 'claude' from first message")
                            return "claude"
                        elif "openai" in first_message or "gpt" in first_message:
                            self.logger.info("Agent type inferred as 'codex' from first message")
                            return "codex"
            except Exception as msg_error:
                self.logger.debug(f"Error checking messages for agent type: {msg_error}")

            # Strategy 3: Look for agent-specific patterns in the status response
            try:
                status_data = await self.get_status()
                status_str = str(status_data).lower()

                # Check each agent type's patterns in the status string
                for agent_type, patterns in agent_patterns.items():
                    for pattern in patterns:
                        if pattern in status_str:
                            self.logger.info(f"Agent type inferred as '{agent_type}' from status data (pattern: {pattern})")
                            return agent_type
            except Exception as status_error:
                self.logger.debug(f"Error analyzing status for agent type: {status_error}")

            # Strategy 4: Try to get screen content (if available)
            # This is a more advanced strategy that might work with some agents
            try:
                # This is an experimental approach - the screen endpoint might not be available
                # We'll make a direct request to avoid adding a dependency on the screen streaming methods
                url = f"{self.agent_api_url}/internal/screen"
                headers = {
                    "User-Agent": USER_AGENT,
                    "Accept": "text/event-stream"
                }

                # Use a short timeout to avoid blocking
                timeout = 2.0

                async with self.http_client.stream("GET", url, headers=headers, timeout=timeout) as response:
                    if response.status_code == 200:
                        # Read a small amount of data to check for agent-specific patterns
                        content = ""
                        async for line in response.aiter_lines():
                            content += line.lower()
                            # Check after collecting some data
                            if len(content) > 1000:
                                break

                        # Check each agent type's patterns in the screen content
                        for agent_type, patterns in agent_patterns.items():
                            for pattern in patterns:
                                if pattern in content:
                                    self.logger.info(f"Agent type inferred as '{agent_type}' from screen content (pattern: {pattern})")
                                    return agent_type
            except Exception as screen_error:
                # This is expected to fail often, so we'll just log at debug level
                self.logger.debug(f"Error checking screen for agent type: {screen_error}")

            # If we still can't determine the type, return "custom"
            self.logger.info("Could not determine specific agent type, using 'custom'")
            return "custom"
        except Exception as e:
            self.logger.error(f"Error getting agent type: {e}")
            return "unknown"

    async def get_messages(self) -> Dict[str, Any]:
        """
        Get all messages in the conversation history.

        Returns:
            A dictionary containing the messages with the following structure:
            {
                "messages": [
                    {
                        "id": 1,
                        "content": "Hello",
                        "role": "user",
                        "time": "2023-01-01T00:00:00Z"
                    },
                    ...
                ]
            }

        Raises:
            AgentAPIError: If the request fails
        """
        return await self.make_request("messages")

    async def get_screen(self) -> str:
        """
        Get the current screen content from the Agent API.

        This method retrieves the current terminal screen content from the Agent API.
        It's useful for getting a snapshot of the terminal screen without subscribing
        to the screen stream.

        Returns:
            A string containing the screen content

        Raises:
            AgentAPIError: If the request fails
            TimeoutError: If the request times out
        """
        try:
            # The screen endpoint is a hidden endpoint in the original Agent API
            # It's located at /internal/screen
            response = await self.make_request("internal/screen")

            # The response should be a dictionary with a "screen" field
            if isinstance(response, dict) and "screen" in response:
                return response["screen"]

            # If the response is a string, assume it's the screen content
            if isinstance(response, str):
                return response

            # Otherwise, return the raw response
            return str(response)
        except Exception:
            # Rethrow the exception without capturing it
            raise

    async def get_message_list(self) -> List[Message]:
        """
        Get all messages in the conversation history as a list of Message objects.

        Returns:
            A list of Message objects

        Raises:
            AgentAPIError: If the request fails
        """
        messages_data = await self.get_messages()
        messages = []

        for msg_data in messages_data.get("messages", []):
            try:
                message = Message(
                    id=msg_data["id"],
                    content=msg_data["content"],
                    role=ConversationRole(msg_data["role"]),
                    time=msg_data["time"]
                )
                messages.append(message)
            except (KeyError, ValueError) as e:
                self.logger.warning(f"Error parsing message: {e}")

        return messages

    async def send_message(
        self,
        content: str,
        message_type: Union[str, MessageType] = MessageType.USER
    ) -> Dict[str, Any]:
        """
        Send a message to the agent.

        Args:
            content: The message content
            message_type: The message type (user or raw), can be a string or MessageType enum

        Returns:
            A dictionary containing the response with the following structure:
            {
                "ok": true
            }

        Raises:
            AgentAPIError: If the request fails
        """
        # Convert MessageType enum to string if needed
        if isinstance(message_type, MessageType):
            message_type = message_type.value

        payload = {
            "content": content,
            "type": message_type
        }

        return await self.make_request("message", method="POST", json_data=payload)

    async def get_openapi_schema(self) -> Dict[str, Any]:
        """
        Get the OpenAPI schema for the Agent API.

        This method retrieves the OpenAPI schema from the Agent API and validates it
        to ensure it contains the required endpoints and components. If the schema
        is missing required elements, it will be enhanced with default values.

        Returns:
            A dictionary containing the validated and enhanced OpenAPI schema

        Raises:
            AgentAPIError: If the request fails
        """
        try:
            # Get the raw schema from the Agent API
            schema = await self.make_request("openapi.json")

            # Validate and enhance the schema
            return await self._validate_and_enhance_schema(schema)
        except Exception as e:
            self.logger.error(f"Error getting OpenAPI schema: {e}")
            # If we can't get the schema, return a fallback schema
            return self._get_fallback_schema()

    async def _validate_and_enhance_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and enhance the OpenAPI schema.

        This method checks if the schema contains the required endpoints and components,
        and adds them if they're missing. This ensures that the schema is complete and
        accurate, even if the Agent API doesn't provide all the information.

        Args:
            schema: The raw OpenAPI schema from the Agent API

        Returns:
            The validated and enhanced OpenAPI schema
        """
        # Make a deep copy of the schema to avoid modifying the original
        enhanced_schema = json.loads(json.dumps(schema))

        # Ensure the schema has the required fields
        if "openapi" not in enhanced_schema:
            enhanced_schema["openapi"] = "3.1.0"

        if "info" not in enhanced_schema:
            enhanced_schema["info"] = {
                "title": "Agent API",
                "version": "0.1.0",
                "description": "HTTP API for AI agents (Claude, Goose, Aider, etc.)"
            }

        if "paths" not in enhanced_schema:
            enhanced_schema["paths"] = {}

        # Ensure the schema has the required endpoints
        paths = enhanced_schema["paths"]

        # Check for /status endpoint
        if "/status" not in paths:
            paths["/status"] = {
                "get": {
                    "operationId": "getStatus",
                    "summary": "Get agent status",
                    "description": "Returns the current status of the agent.",
                    "responses": {
                        "200": {
                            "description": "Agent status",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {
                                                "type": "string",
                                                "enum": ["running", "stable"],
                                                "description": "Current agent status"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

        # Check for /messages endpoint
        if "/messages" not in paths:
            paths["/messages"] = {
                "get": {
                    "operationId": "getMessages",
                    "summary": "Get conversation history",
                    "description": "Returns a list of messages representing the conversation history with the agent.",
                    "responses": {
                        "200": {
                            "description": "Conversation history",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "messages": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "id": {
                                                            "type": "integer",
                                                            "description": "Message ID"
                                                        },
                                                        "content": {
                                                            "type": "string",
                                                            "description": "Message content"
                                                        },
                                                        "role": {
                                                            "type": "string",
                                                            "enum": ["user", "agent"],
                                                            "description": "Message role"
                                                        },
                                                        "time": {
                                                            "type": "string",
                                                            "format": "date-time",
                                                            "description": "Message timestamp"
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

        # Check for /message endpoint
        if "/message" not in paths:
            paths["/message"] = {
                "post": {
                    "operationId": "createMessage",
                    "summary": "Send a message to the agent",
                    "description": "Send a message to the agent. For messages of type 'user', the agent's status must be 'stable' for the operation to complete successfully. Otherwise, this endpoint will return an error.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "content": {
                                            "type": "string",
                                            "description": "Message content"
                                        },
                                        "type": {
                                            "type": "string",
                                            "enum": ["user", "raw"],
                                            "description": "Message type"
                                        }
                                    },
                                    "required": ["content", "type"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Message sent successfully",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "ok": {
                                                "type": "boolean",
                                                "description": "Whether the message was sent successfully"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

        # Check for /events endpoint
        if "/events" not in paths:
            paths["/events"] = {
                "get": {
                    "operationId": "subscribeEvents",
                    "summary": "Subscribe to events",
                    "description": "The events are sent as Server-Sent Events (SSE). Initially, the endpoint returns a list of events needed to reconstruct the current state of the conversation and the agent's status. After that, it only returns events that have occurred since the last event was sent.",
                    "responses": {
                        "200": {
                            "description": "Event stream",
                            "content": {
                                "text/event-stream": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "type": {
                                                "type": "string",
                                                "enum": ["message_update", "status_change"],
                                                "description": "Event type"
                                            },
                                            "data": {
                                                "type": "object",
                                                "description": "Event data"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

        # Check for /internal/screen endpoint
        if "/internal/screen" not in paths:
            paths["/internal/screen"] = {
                "get": {
                    "operationId": "subscribeScreen",
                    "summary": "Subscribe to screen",
                    "description": "Subscribe to screen updates from the agent. The updates are sent as Server-Sent Events (SSE).",
                    "responses": {
                        "200": {
                            "description": "Screen update stream",
                            "content": {
                                "text/event-stream": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "screen": {
                                                "type": "string",
                                                "description": "Screen content"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

        # Add any additional validation or enhancement here

        return enhanced_schema

    def _get_fallback_schema(self) -> Dict[str, Any]:
        """
        Get a fallback OpenAPI schema.

        This method returns a complete OpenAPI schema with all the required endpoints
        and components. It's used when we can't get the schema from the Agent API.

        Returns:
            A complete OpenAPI schema
        """
        # Create a basic schema with all the required endpoints
        schema = {
            "openapi": "3.1.0",
            "info": {
                "title": "Agent API",
                "version": "0.1.0",
                "description": "HTTP API for AI agents (Claude, Goose, Aider, etc.)"
            },
            "paths": {
                "/status": {
                    "get": {
                        "operationId": "getStatus",
                        "summary": "Get agent status",
                        "description": "Returns the current status of the agent.",
                        "responses": {
                            "200": {
                                "description": "Agent status",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "status": {
                                                    "type": "string",
                                                    "enum": ["running", "stable"],
                                                    "description": "Current agent status"
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "/messages": {
                    "get": {
                        "operationId": "getMessages",
                        "summary": "Get conversation history",
                        "description": "Returns a list of messages representing the conversation history with the agent.",
                        "responses": {
                            "200": {
                                "description": "Conversation history",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "messages": {
                                                    "type": "array",
                                                    "items": {
                                                        "type": "object",
                                                        "properties": {
                                                            "id": {
                                                                "type": "integer",
                                                                "description": "Message ID"
                                                            },
                                                            "content": {
                                                                "type": "string",
                                                                "description": "Message content"
                                                            },
                                                            "role": {
                                                                "type": "string",
                                                                "enum": ["user", "agent"],
                                                                "description": "Message role"
                                                            },
                                                            "time": {
                                                                "type": "string",
                                                                "format": "date-time",
                                                                "description": "Message timestamp"
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "/message": {
                    "post": {
                        "operationId": "createMessage",
                        "summary": "Send a message to the agent",
                        "description": "Send a message to the agent. For messages of type 'user', the agent's status must be 'stable' for the operation to complete successfully. Otherwise, this endpoint will return an error.",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "content": {
                                                "type": "string",
                                                "description": "Message content"
                                            },
                                            "type": {
                                                "type": "string",
                                                "enum": ["user", "raw"],
                                                "description": "Message type"
                                            }
                                        },
                                        "required": ["content", "type"]
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "Message sent successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "ok": {
                                                    "type": "boolean",
                                                    "description": "Whether the message was sent successfully"
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "/events": {
                    "get": {
                        "operationId": "subscribeEvents",
                        "summary": "Subscribe to events",
                        "description": "The events are sent as Server-Sent Events (SSE). Initially, the endpoint returns a list of events needed to reconstruct the current state of the conversation and the agent's status. After that, it only returns events that have occurred since the last event was sent.",
                        "responses": {
                            "200": {
                                "description": "Event stream",
                                "content": {
                                    "text/event-stream": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "type": {
                                                    "type": "string",
                                                    "enum": ["message_update", "status_change"],
                                                    "description": "Event type"
                                                },
                                                "data": {
                                                    "type": "object",
                                                    "description": "Event data"
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "/internal/screen": {
                    "get": {
                        "operationId": "subscribeScreen",
                        "summary": "Subscribe to screen",
                        "description": "Subscribe to screen updates from the agent. The updates are sent as Server-Sent Events (SSE).",
                        "responses": {
                            "200": {
                                "description": "Screen update stream",
                                "content": {
                                    "text/event-stream": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "screen": {
                                                    "type": "string",
                                                    "description": "Screen content"
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        return schema

    async def stream_events(
        self,
        callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
        reconnect: bool = True,
        max_reconnect_attempts: int = MAX_RECONNECT_ATTEMPTS,
        reconnect_initial_delay: float = DEFAULT_RECONNECT_DELAY,
        reconnect_max_delay: float = DEFAULT_RETRY_MAX_DELAY,
        reconnect_backoff_factor: float = DEFAULT_RETRY_BACKOFF_FACTOR,
        reconnect_jitter: float = DEFAULT_RETRY_JITTER,
        last_event_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream events from the Agent API.

        This method connects to the Agent API events endpoint and yields events
        as they arrive. It can also call a callback function for each event.
        It implements exponential backoff with jitter for reconnection attempts.

        Args:
            callback: Optional callback function to call for each event
            reconnect: Whether to automatically reconnect if the connection is lost
            max_reconnect_attempts: Maximum number of reconnection attempts
            reconnect_initial_delay: Initial delay between reconnection attempts in seconds
            reconnect_max_delay: Maximum delay between reconnection attempts in seconds
            reconnect_backoff_factor: Factor to increase delay for each reconnection attempt
            reconnect_jitter: Random jitter factor to add to delay (0.0 to 1.0)
            last_event_id: Optional ID of the last event received, used for reconnection

        Yields:
            Event data as dictionaries

        Raises:
            AgentAPIError: If the connection fails and reconnection is disabled or fails
            TimeoutError: If the connection times out and reconnection is disabled or fails
        """
        url = f"{self.agent_api_url}/events"
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/event-stream"
        }

        # Add Last-Event-ID header if we have a last event ID
        # This allows the server to send only events that occurred after the last event we received
        # This is exactly how the original Agent API handles reconnection in the SSE protocol
        if last_event_id:
            self.logger.info(f"Reconnecting with Last-Event-ID: {last_event_id}")
            headers["Last-Event-ID"] = last_event_id

            # The original Agent API also supports a query parameter for last event ID
            # This is a fallback for clients that don't support the Last-Event-ID header
            url_with_id = f"{url}?lastEventId={last_event_id}"
            self.logger.debug(f"Using URL with lastEventId: {url_with_id}")
            url = url_with_id

        attempt = 0
        delay = reconnect_initial_delay

        while True:
            try:
                self.logger.info(f"Connecting to event stream at {url}")

                # Use a timeout for the initial connection
                connection_timeout = 30.0  # 30 seconds for initial connection

                try:
                    async with self.http_client.stream("GET", url, headers=headers, timeout=connection_timeout) as response:
                        response.raise_for_status()

                        # Reset reconnection attempts and delay on successful connection
                        attempt = 0
                        delay = reconnect_initial_delay
                        self.logger.info("Successfully connected to event stream")

                        # Process events as they arrive
                        event_type = None
                        event_buffer = ""
                        event_id = None
                        event_count = 0

                        # Log connection success
                        self.logger.info("Connected to Agent API event stream, processing events...")

                        async for line in response.aiter_lines():

                            # Skip empty lines (but they're still important for event boundaries)
                            if not line.strip():
                                # Empty line can signal the end of an event
                                if event_type and event_buffer:
                                    try:
                                        # Try to parse the accumulated data as JSON
                                        try:
                                            data = json.loads(event_buffer)

                                            # Create the event object with proper metadata
                                            event = {
                                                "type": event_type,
                                                "data": data,
                                                "id": event_id,
                                                "timestamp": time.time()
                                            }

                                            # Log event details at debug level
                                            self.logger.debug(f"Received event: {event_type} (id: {event_id})")

                                            # Call the callback if provided
                                            if callback:
                                                try:
                                                    await callback(event)
                                                except Exception as callback_error:
                                                    self.logger.error(f"Error in event callback: {callback_error}")
                                                    # Continue processing events even if callback fails

                                            # Yield the event
                                            yield event

                                            # Update event count and log periodically
                                            event_count += 1
                                            if event_count % 50 == 0:
                                                self.logger.info(f"Processed {event_count} events from stream")

                                            # Reset buffers for next event
                                            event_type = None
                                            event_buffer = ""
                                            event_id = None
                                        except json.JSONDecodeError:
                                            # If we can't parse as JSON yet, continue accumulating data
                                            # This handles multi-line data fields
                                            pass
                                    except Exception as e:
                                        self.logger.error(f"Error processing event: {e}")
                                        # Reset buffers on error
                                        event_type = None
                                        event_buffer = ""
                                        event_id = None
                                continue

                            # Parse SSE event fields
                            if line.startswith("event:"):
                                event_type = line[6:].strip()
                                # Keep existing buffer for multi-line events
                            elif line.startswith("id:"):
                                event_id = line[3:].strip()
                            elif line.startswith("data:"):
                                try:
                                    # Extract the event data
                                    data_str = line[5:].strip()

                                    # For the first data line, replace the buffer
                                    # For subsequent lines, append with newlines
                                    if not event_buffer:
                                        event_buffer = data_str
                                    else:
                                        event_buffer += "\n" + data_str
                                except Exception as e:
                                    self.logger.error(f"Error processing data line: {e}")
                            elif line.startswith(":"):
                                # Comment line, often used for heartbeats
                                self.logger.debug(f"SSE comment: {line[1:].strip()}")
                            else:
                                # Unknown line format
                                self.logger.warning(f"Unknown SSE line format: {line}")

                except httpx.TimeoutException as e:
                    # Handle connection timeout
                    self.logger.error(f"Timeout connecting to event stream: {e}")
                    if not reconnect:
                        raise TimeoutError(f"Event stream connection timeout: {str(e)}")
                    raise  # Re-raise to be caught by the outer try/except

            except (httpx.HTTPError, httpx.StreamError, httpx.TimeoutException) as e:
                error_type = type(e).__name__
                self.logger.error(f"{error_type} in event stream: {e}")

                if not reconnect:
                    if isinstance(e, httpx.TimeoutException):
                        raise TimeoutError(f"Event stream timeout: {str(e)}")
                    else:
                        raise AgentAPIError(f"Event stream error: {str(e)}")

                # Check if we've exceeded the maximum number of attempts
                attempt += 1
                if attempt > max_reconnect_attempts:
                    self.logger.error(f"Failed to reconnect to event stream after {max_reconnect_attempts} attempts")
                    raise AgentAPIError(
                        f"Failed to reconnect to event stream after {max_reconnect_attempts} attempts"
                    )

                # Calculate the next delay with exponential backoff and jitter
                delay = min(delay * reconnect_backoff_factor, reconnect_max_delay)
                jitter_amount = delay * reconnect_jitter
                actual_delay = delay + random.uniform(-jitter_amount, jitter_amount)
                actual_delay = max(0.1, actual_delay)  # Ensure delay is at least 0.1 seconds

                self.logger.info(
                    f"Reconnecting to event stream (attempt {attempt}/{max_reconnect_attempts}) "
                    f"in {actual_delay:.2f}s after {error_type}"
                )

                # Wait before reconnecting
                await asyncio.sleep(actual_delay)

            except asyncio.CancelledError:
                # Allow cancellation to propagate
                self.logger.info("Event stream task cancelled")
                raise

            except Exception as e:
                self.logger.error(f"Unexpected error in event stream: {e}")

                # Check if we should reconnect
                if not reconnect:
                    raise AgentAPIError(f"Unexpected event stream error: {str(e)}")

                # Check if we've exceeded the maximum number of attempts
                attempt += 1
                if attempt > max_reconnect_attempts:
                    self.logger.error(f"Failed to reconnect to event stream after {max_reconnect_attempts} attempts")
                    raise AgentAPIError(
                        f"Failed to reconnect to event stream after {max_reconnect_attempts} attempts"
                    )

                # Use a shorter delay for unexpected errors to recover quickly
                actual_delay = min(delay, 5.0)

                self.logger.info(
                    f"Reconnecting to event stream (attempt {attempt}/{max_reconnect_attempts}) "
                    f"in {actual_delay:.2f}s after unexpected error"
                )

                # Wait before reconnecting
                await asyncio.sleep(actual_delay)

    async def stream_screen(
        self,
        callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
        reconnect: bool = True,
        max_reconnect_attempts: int = MAX_RECONNECT_ATTEMPTS,
        reconnect_initial_delay: float = DEFAULT_RECONNECT_DELAY,
        reconnect_max_delay: float = DEFAULT_RETRY_MAX_DELAY,
        reconnect_backoff_factor: float = DEFAULT_RETRY_BACKOFF_FACTOR,
        reconnect_jitter: float = DEFAULT_RETRY_JITTER
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream screen updates from the Agent API.

        This method connects to the Agent API internal screen endpoint and yields screen updates
        as they arrive. It can also call a callback function for each update.
        It implements exponential backoff with jitter for reconnection attempts.

        Args:
            callback: Optional callback function to call for each screen update
            reconnect: Whether to automatically reconnect if the connection is lost
            max_reconnect_attempts: Maximum number of reconnection attempts
            reconnect_initial_delay: Initial delay between reconnection attempts in seconds
            reconnect_max_delay: Maximum delay between reconnection attempts in seconds
            reconnect_backoff_factor: Factor to increase delay for each reconnection attempt
            reconnect_jitter: Random jitter factor to add to delay (0.0 to 1.0)

        Yields:
            Screen update events as dictionaries

        Raises:
            AgentAPIError: If the connection fails and reconnection is disabled or fails
            TimeoutError: If the connection times out and reconnection is disabled or fails
            EventStreamError: If there's an error processing the event stream
        """
        url = f"{self.agent_api_url}/internal/screen"
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/event-stream"
        }

        attempt = 0
        delay = reconnect_initial_delay

        while True:
            try:
                self.logger.info(f"Connecting to screen stream at {url}")

                # Use a timeout for the initial connection
                connection_timeout = 30.0  # 30 seconds for initial connection

                try:
                    async with self.http_client.stream("GET", url, headers=headers, timeout=connection_timeout) as response:
                        response.raise_for_status()

                        # Reset reconnection attempts and delay on successful connection
                        attempt = 0
                        delay = reconnect_initial_delay
                        self.logger.info("Successfully connected to screen stream")

                        # Process events as they arrive
                        event_type = None
                        event_buffer = ""
                        event_count = 0

                        # Log connection success
                        self.logger.info("Connected to Agent API screen stream, processing updates...")

                        async for line in response.aiter_lines():
                            # Skip empty lines (but they're still important for event boundaries)
                            if not line.strip():
                                # Empty line can signal the end of an event
                                if event_type and event_buffer:
                                    try:
                                        # Try to parse the accumulated data as JSON
                                        try:
                                            data = json.loads(event_buffer)

                                            # Create the event object with proper metadata
                                            event = {
                                                "type": "screen",
                                                "data": data,
                                                "timestamp": time.time()
                                            }

                                            # Log event details at debug level
                                            self.logger.debug(f"Received screen update (size: {len(data.get('screen', ''))} chars)")

                                            # Call the callback if provided
                                            if callback:
                                                try:
                                                    await callback(event)
                                                except Exception as callback_error:
                                                    self.logger.error(f"Error in screen callback: {callback_error}")
                                                    # Continue processing events even if callback fails

                                            # Yield the event
                                            event_count += 1
                                            yield event

                                        except json.JSONDecodeError as json_error:
                                            self.logger.warning(f"Failed to parse screen data as JSON: {json_error}")
                                            self.logger.debug(f"Raw data: {event_buffer}")
                                    except Exception as e:
                                        self.logger.error(f"Error processing screen update: {e}")

                                    # Reset for the next event
                                    event_type = None
                                    event_buffer = ""
                                continue

                            # Parse SSE fields
                            if line.startswith("event:"):
                                event_type = line[6:].strip()
                            elif line.startswith("data:"):
                                event_buffer = line[5:].strip()
                            elif line.startswith("id:"):
                                pass  # We don't use event IDs for screen updates
                            elif line.startswith(":"):
                                pass  # Comment, ignore
                            else:
                                self.logger.warning(f"Unknown SSE line format: {line}")

                except httpx.HTTPStatusError as status_error:
                    self.logger.error(f"HTTP error in screen stream: {status_error}")
                    if status_error.response.status_code == 404:
                        self.logger.warning("Screen endpoint not found (404). This endpoint might not be supported by the Agent API.")
                        if not reconnect:
                            raise AgentAPIError(
                                f"Screen endpoint not found: {str(status_error)}",
                                status_code=status_error.response.status_code
                            )
                        # Don't retry 404 errors even if reconnect is enabled
                        return
                    raise

            except (httpx.HTTPError, httpx.StreamError, httpx.TimeoutException) as e:
                error_type = type(e).__name__
                self.logger.error(f"{error_type} in screen stream: {e}")

                if not reconnect:
                    if isinstance(e, httpx.TimeoutException):
                        raise TimeoutError(f"Screen stream timeout: {str(e)}")
                    else:
                        raise AgentAPIError(f"Screen stream error: {str(e)}")

                # Check if we've exceeded the maximum number of attempts
                attempt += 1
                if attempt > max_reconnect_attempts:
                    self.logger.error(f"Failed to reconnect to screen stream after {max_reconnect_attempts} attempts")
                    raise AgentAPIError(
                        f"Failed to reconnect to screen stream after {max_reconnect_attempts} attempts"
                    )

                # Calculate delay with exponential backoff and jitter
                delay = min(delay * reconnect_backoff_factor, reconnect_max_delay)
                # Add jitter to avoid thundering herd problem
                jitter_factor = 1.0 - reconnect_jitter + (2 * reconnect_jitter * random.random())
                actual_delay = delay * jitter_factor

                self.logger.info(f"Reconnecting to screen stream in {actual_delay:.2f}s (attempt {attempt}/{max_reconnect_attempts})")

                # Wait before reconnecting
                await asyncio.sleep(actual_delay)

    async def stream_screen_to_mcp(self, server: FastMCP, event_emitter=None) -> None:
        """
        Stream screen updates from the Agent API to MCP clients.

        This method connects to the Agent API internal screen endpoint and forwards screen updates
        to MCP clients as notifications. It includes robust error handling and
        automatic reconnection with exponential backoff.

        Note: The screen endpoint is optional in the original Agent API and might not be
        supported by all agent implementations. This method handles that gracefully.

        Args:
            server: The FastMCP server instance
            event_emitter: Optional event emitter instance for tracking metrics

        Raises:
            AgentAPIError: If the connection fails and reconnection fails
            TimeoutError: If the connection times out and reconnection fails
            EventStreamError: If there's an error processing the event stream
        """
        # First, check if the screen endpoint is supported
        try:
            # Make a HEAD request to check if the endpoint exists
            url = f"{self.agent_api_url}/internal/screen"
            self.logger.debug(f"Checking if screen endpoint is supported: {url}")

            async with self.http_client.head(url, timeout=5.0) as response:
                if response.status_code == 404:
                    self.logger.info("Screen endpoint not supported (404). This is normal for some agent implementations.")
                    # Don't try to stream from an unsupported endpoint
                    return

                # If we get here, the endpoint exists
                self.logger.info("Screen endpoint is supported, starting screen stream")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                self.logger.info("Screen endpoint not supported (404). This is normal for some agent implementations.")
                return
            # For other HTTP errors, log and continue (we'll try to connect anyway)
            self.logger.warning(f"Error checking screen endpoint: {e}")
        except Exception as e:
            # For other errors, log and continue (we'll try to connect anyway)
            self.logger.warning(f"Error checking screen endpoint: {e}")

        # Track health metrics
        event_count = 0
        error_count = 0
        last_event_time = 0
        connection_start_time = time.time()

        # Create a heartbeat task to ensure the connection is still alive
        # Use a multiple of SNAPSHOT_INTERVAL for heartbeats to align with the original Agent API's timing
        # The original Agent API checks health every 1200 snapshots (30 seconds at 25ms per snapshot)
        heartbeat_interval = SNAPSHOT_INTERVAL * 1200  # 30 seconds (1200 * 25ms)
        heartbeat_task = None

        async def heartbeat():
            """Send periodic heartbeats to keep the connection alive."""
            try:
                while True:
                    await asyncio.sleep(heartbeat_interval)
                    self.logger.debug(f"Screen stream heartbeat: {event_count} updates processed")

                    # Check if we haven't received events for a while
                    if last_event_time > 0 and time.time() - last_event_time > heartbeat_interval * 2:
                        self.logger.warning(
                            f"No screen updates received for {time.time() - last_event_time:.1f}s, "
                            f"connection may be stale"
                        )
            except asyncio.CancelledError:
                self.logger.debug("Screen heartbeat task cancelled")
            except Exception as e:
                self.logger.error(f"Error in screen heartbeat task: {e}")

        async def process_screen_update(event: Dict[str, Any]) -> None:
            """Process and forward a screen update to MCP clients."""
            nonlocal event_count, error_count, last_event_time

            try:
                # Convert the event to a JSON string
                event_json = json.dumps(event)

                # Send the event as a notification to MCP clients
                await server.notify(event_json)

                # Update metrics
                event_count += 1
                last_event_time = time.time()

                # Update event emitter metrics if available
                if event_emitter:
                    event_emitter.record_event_processed()

                # Log periodic status updates (every 100 events)
                if event_count % 100 == 0:
                    connection_duration = time.time() - connection_start_time
                    events_per_second = event_count / connection_duration if connection_duration > 0 else 0
                    self.logger.info(
                        f"Forwarded {event_count} screen updates to MCP clients "
                        f"(errors: {error_count}, rate: {events_per_second:.1f}/s)"
                    )

            except Exception as e:
                error_count += 1
                if event_emitter:
                    event_emitter.record_error()
                self.logger.error(f"Error forwarding screen update to MCP clients: {e}")

                # Log detailed error information for debugging
                if hasattr(e, "__traceback__"):
                    import traceback
                    tb_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
                    self.logger.debug(f"Screen update forwarding error traceback: {tb_str}")

        try:
            # Start heartbeat task
            heartbeat_task = asyncio.create_task(heartbeat())

            # Stream screen updates with enhanced error handling and reconnection
            async for _ in self.stream_screen(
                callback=process_screen_update,
                reconnect=True,
                max_reconnect_attempts=15,  # More attempts for this critical service
                reconnect_initial_delay=0.5,  # Start with a shorter delay
                reconnect_max_delay=60.0,  # Maximum 1 minute between attempts
                reconnect_backoff_factor=1.5,  # Moderate backoff
                reconnect_jitter=0.2  # Add jitter to avoid thundering herd
            ):
                pass  # We don't need to do anything with the yielded events

        except (AgentAPIError, TimeoutError) as e:
            self.logger.error(f"Fatal error in screen stream: {e}")
            # Re-raise the exception to be handled by the caller
            raise
        except asyncio.CancelledError:
            self.logger.info("Screen stream task cancelled")
            # Don't re-raise, allow clean cancellation
        except Exception as e:
            self.logger.error(f"Unexpected error in screen stream to MCP: {e}")
            raise EventStreamError(f"Unexpected error in screen stream to MCP: {str(e)}")
        finally:
            # Clean up heartbeat task
            if heartbeat_task and not heartbeat_task.done():
                self.logger.debug(f"Cancelling screen heartbeat task")
                heartbeat_task.cancel()
                try:
                    await asyncio.wait_for(asyncio.shield(heartbeat_task), timeout=2.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    self.logger.debug(f"Screen heartbeat task cancelled")
                except Exception as e:
                    self.logger.error(f"Error cancelling screen heartbeat task: {e}")

    async def stream_events_to_mcp(self, server: FastMCP, event_emitter=None) -> None:
        """
        Stream events from the Agent API to MCP clients.

        This method connects to the Agent API events endpoint and forwards events
        to MCP clients as notifications. It includes robust error handling and
        automatic reconnection with exponential backoff.

        Args:
            server: The FastMCP server instance
            event_emitter: Optional event emitter instance for tracking metrics

        Raises:
            AgentAPIError: If the connection fails and reconnection fails
            TimeoutError: If the connection times out and reconnection fails
        """
        # Track health metrics
        event_count = 0
        error_count = 0
        last_event_time = 0
        connection_start_time = time.time()
        last_event_id = None  # Track last event ID for proper ordering
        event_buffer = []  # Buffer for events to ensure proper ordering
        event_buffer_lock = asyncio.Lock()  # Lock for thread-safe access to the buffer

        # Maximum buffer size to prevent memory issues (matches original Agent API's 1024)
        # This is the same value used in the original Agent API's NewEventEmitter function
        max_buffer_size = EVENT_BUFFER_SIZE

        # Create a heartbeat task to ensure the connection is still alive
        # Use a multiple of SNAPSHOT_INTERVAL for heartbeats to align with the original Agent API's timing
        # The original Agent API checks health every 1200 snapshots (30 seconds at 25ms per snapshot)
        heartbeat_interval = SNAPSHOT_INTERVAL * 1200  # 30 seconds (1200 * 25ms)
        heartbeat_task = None
        event_processor_task = None

        # Flag to track if we've sent initial state events
        initial_state_sent = False

        async def heartbeat():
            """Send periodic heartbeats to keep the connection alive."""
            try:
                while True:
                    await asyncio.sleep(heartbeat_interval)
                    self.logger.debug(f"Event stream heartbeat: {event_count} events processed")

                    # Check if we haven't received events for a while
                    if last_event_time > 0 and time.time() - last_event_time > heartbeat_interval * 2:
                        self.logger.warning(
                            f"No events received for {time.time() - last_event_time:.1f}s, "
                            f"connection may be stale"
                        )
            except asyncio.CancelledError:
                self.logger.debug("Heartbeat task cancelled")
            except Exception as e:
                self.logger.error(f"Error in heartbeat task: {e}")

        async def process_event_buffer():
            """
            Process events from the buffer in order.

            This method ensures events are processed in the correct order by:
            1. Sorting events by ID (for message_update events) or timestamp
            2. Deduplicating events by type and ID to avoid duplicates
            3. Processing events in batches for better performance
            4. Handling errors gracefully to ensure the event stream continues
            """
            nonlocal event_count, error_count, last_event_time, last_event_id

            try:
                while True:
                    # Process events in the buffer
                    async with event_buffer_lock:
                        if not event_buffer:
                            # No events to process, wait for more
                            await asyncio.sleep(0.01)  # 10ms delay to avoid busy waiting
                            continue

                        # Sort events to ensure proper ordering
                        # This sorting logic exactly matches the original Agent API's behavior in events.go
                        # The original Agent API prioritizes events in this order:
                        # 1. Status changes (to ensure UI reflects current state)
                        # 2. Message updates in order by ID (to ensure conversation history is correct)
                        # 3. Screen updates (to ensure terminal display is current)
                        # 4. Other events in order of occurrence
                        event_buffer.sort(key=lambda e: (
                            # First, prioritize status_change events to ensure UI reflects current state
                            # This matches the original Agent API's behavior in events.go
                            0 if e.get("type") == "status_change" else (
                                # Then prioritize message_update events with valid IDs
                                1 if e.get("type") == "message_update" and e.get("id") and e.get("id").isdigit() else (
                                    # Then prioritize screen updates
                                    2 if e.get("type") in ["screen_update", "screen"] else 3
                                )
                            ),

                            # For status changes, sort by timestamp to get the most recent status first
                            # This ensures the UI always shows the most current state
                            -e.get("timestamp", 0) if e.get("type") == "status_change" else 0,

                            # For message updates, sort by ID to ensure conversation history is in order
                            # This matches the original Agent API's behavior in UpdateMessagesAndEmitChanges
                            int(e.get("id", 0)) if e.get("type") == "message_update" and e.get("id") and e.get("id").isdigit() else 0,

                            # For screen updates, sort by timestamp to get the most recent screen first
                            # This ensures the terminal display is always current
                            -e.get("timestamp", 0) if e.get("type") in ["screen_update", "screen"] else 0,

                            # For all other events, sort by timestamp
                            e.get("timestamp", 0)
                        ))

                        # Deduplicate events by type and ID
                        # This ensures we don't send duplicate events to clients
                        # For example, if we receive multiple status_change events with the same status
                        events_to_process = []
                        seen_events = set()  # Set of (type, id) tuples

                        for event in event_buffer:
                            event_type = event.get("type", "")
                            event_id = event.get("id", "")
                            event_data = event.get("data", {})

                            # Filter out screen updates from the main event stream
                            # This matches the original Agent API's behavior in subscribeEvents
                            # where screen updates are only sent to clients that subscribe to /internal/screen
                            if event_type == "screen_update":
                                self.logger.debug("Filtering out screen_update event from main event stream")
                                continue

                            # Create a deduplication key based on event type
                            # This exactly matches the original Agent API's behavior in events.go
                            if event_type == "message_update":
                                # For message updates, use the message ID
                                # This matches the original Agent API's behavior in UpdateMessagesAndEmitChanges
                                message_id = event_id or event_data.get("id", "")

                                # Also include a hash of the content to detect content changes
                                # This ensures we don't deduplicate messages with the same ID but different content
                                message_content = event_data.get("message", "")
                                content_hash = hash(message_content[:1000] if len(message_content) > 1000 else message_content)

                                event_key = (event_type, str(message_id), content_hash)

                            elif event_type == "status_change":
                                # For status changes, use the status value
                                # This matches the original Agent API's behavior in UpdateStatusAndEmitChanges
                                status = event_data.get("status", "")

                                # Include a timestamp component to ensure we get the most recent status
                                # but still deduplicate identical statuses that arrive in quick succession
                                timestamp = event.get("timestamp", 0)
                                # Round to nearest second to deduplicate rapid status changes
                                timestamp_bucket = int(timestamp)

                                event_key = (event_type, status, timestamp_bucket)

                            elif event_type == "screen_update" or event_type == "screen":
                                # For screen updates, use a hash of the screen content
                                # This matches the original Agent API's behavior in UpdateScreenAndEmitChanges
                                screen = event_data.get("screen", "")

                                # Use a truncated hash to avoid excessive memory usage
                                # We only hash the first 1000 characters to avoid performance issues with large screens
                                # This is similar to how the original Agent API handles screen updates
                                screen_hash = hash(screen[:1000] if len(screen) > 1000 else screen)

                                # Include a timestamp component to ensure we get the most recent screen
                                # but still deduplicate identical screens that arrive in quick succession
                                timestamp = event.get("timestamp", 0)
                                # Use a higher resolution for screen updates (100ms buckets)
                                # This ensures we don't miss important screen updates while still deduplicating
                                timestamp_bucket = int(timestamp * 10) / 10

                                event_key = (event_type, screen_hash, timestamp_bucket)

                            else:
                                # For other event types, use a hash of the entire data
                                # This is a catch-all for any custom event types
                                data_hash = hash(str(event_data))

                                # Include the event type to ensure different event types with the same data
                                # are not deduplicated
                                event_key = (event_type, data_hash)

                            if event_key not in seen_events:
                                seen_events.add(event_key)
                                events_to_process.append(event)

                        # Clear the buffer after copying events to process
                        event_buffer.clear()

                    # Process events outside the lock to avoid blocking
                    for event in events_to_process:
                        try:
                            # Convert the event to a JSON string
                            event_json = json.dumps(event)

                            # Send the event as a notification to MCP clients
                            await server.notify(event_json)

                            # Update metrics
                            event_count += 1
                            last_event_time = time.time()

                            # Update last event ID if available
                            # This is critical for proper reconnection and event ordering
                            # The original Agent API uses event IDs to ensure events are processed in order
                            if event.get("id") and event.get("id").isdigit():
                                event_id = int(event["id"])

                                # Store the highest event ID we've seen
                                # This is used for reconnection to avoid missing events
                                if not last_event_id or event_id > int(last_event_id):
                                    last_event_id = str(event_id)
                                    self.logger.debug(f"Updated last event ID to {last_event_id}")

                            # For message_update events, also check the ID in the data
                            # This ensures we don't miss any message updates
                            elif event.get("type") == "message_update" and event.get("data", {}).get("id") and str(event.get("data", {}).get("id")).isdigit():
                                message_id = str(event.get("data", {}).get("id"))

                                # If this is a higher ID than we've seen, update last_event_id
                                if not last_event_id or int(message_id) > int(last_event_id):
                                    last_event_id = message_id
                                    self.logger.debug(f"Updated last event ID to {last_event_id} from message data")

                            # Update event emitter metrics if available
                            if event_emitter:
                                event_emitter.record_event_processed()

                            # Log periodic status updates
                            if event_count % 100 == 0:
                                connection_duration = time.time() - connection_start_time
                                events_per_second = event_count / connection_duration if connection_duration > 0 else 0
                                self.logger.info(
                                    f"Forwarded {event_count} events to MCP clients "
                                    f"(errors: {error_count}, rate: {events_per_second:.1f}/s)"
                                )
                        except Exception as e:
                            error_count += 1
                            if event_emitter:
                                event_emitter.record_error()

                            # Log the error
                            self.logger.error(f"Error forwarding event to MCP clients: {e}")

                            # Log detailed error information for debugging
                            if hasattr(e, "__traceback__"):
                                import traceback
                                tb_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
                                self.logger.debug(f"Event forwarding error traceback: {tb_str}")

                            # For critical errors, we might want to take additional action
                            if isinstance(e, (ConnectionError, TimeoutError)):
                                # These are critical errors that might require reconnection
                                self.logger.warning("Critical error processing event, may require reconnection")

                                # We don't raise here to avoid breaking the event processing loop
                                # Instead, the health check will detect the issue and trigger reconnection

                            # For other errors, we continue processing events
                            # This ensures that a single bad event doesn't break the entire stream

                    # Wait a short time before checking the buffer again
                    # This helps reduce CPU usage while still maintaining responsiveness
                    # Use SNAPSHOT_INTERVAL to match the original Agent API's behavior
                    if events_to_process:
                        # Process events more frequently when there are events to process
                        # Use a fraction of SNAPSHOT_INTERVAL to ensure we process events quickly
                        # but still respect the original Agent API's timing
                        await asyncio.sleep(SNAPSHOT_INTERVAL / 25)  # 1ms delay (25ms / 25)
                    else:
                        # Wait longer when there are no events to process
                        # Use a multiple of SNAPSHOT_INTERVAL to reduce CPU usage
                        # but still check frequently enough to avoid missing events
                        await asyncio.sleep(SNAPSHOT_INTERVAL * 0.4)  # 10ms delay (25ms * 0.4)
            except asyncio.CancelledError:
                self.logger.debug("Event processor task cancelled")
            except Exception as e:
                self.logger.error(f"Error in event processor task: {e}")

        async def buffer_event(event: Dict[str, Any]) -> None:
            """
            Add an event to the buffer for ordered processing.

            This method adds events to the buffer, ensuring that the buffer doesn't
            exceed the maximum size. If the buffer is full, it drops the oldest events
            to make room for new ones, similar to how the original Agent API closes
            channels when they're full.

            Args:
                event: The event to add to the buffer
            """
            async with event_buffer_lock:
                # Check if buffer is too large
                if len(event_buffer) >= max_buffer_size:
                    # This matches the original Agent API's behavior in events.go
                    # When a channel is full, it closes the channel
                    # In our case, we drop the oldest event to make room
                    self.logger.warning(
                        f"Event buffer overflow ({len(event_buffer)}/{max_buffer_size}), "
                        f"dropping oldest event to match original Agent API behavior"
                    )

                    # Drop the oldest event
                    event_buffer.pop(0)

                # Add the event to the buffer
                event_buffer.append(event)

        # Create a task to monitor agent status changes
        async def monitor_agent_status():
            """
            Monitor agent status and emit status change events.

            This method periodically checks the agent status and emits events
            when the status changes, similar to how the original Agent API's
            UpdateStatusAndEmitChanges method works.
            """
            last_status = None
            # Use SNAPSHOT_INTERVAL to exactly match the original Agent API's behavior
            # The original Agent API checks status every snapshot interval (25ms)
            # This is defined in agentapi/lib/httpapi/server.go
            check_interval = SNAPSHOT_INTERVAL

            try:
                while True:
                    try:
                        # Get current status
                        current_status = await self.get_agent_status()

                        # If status has changed, emit an event
                        if current_status != last_status:
                            self.logger.info(f"Agent status changed from {last_status} to {current_status}")

                            # Create a status change event
                            event = {
                                "type": "status_change",
                                "data": {
                                    "status": current_status.value
                                },
                                "timestamp": time.time()
                            }

                            # Buffer the event
                            await buffer_event(event)

                            # Update last status
                            last_status = current_status

                    except Exception as e:
                        self.logger.error(f"Error monitoring agent status: {e}")

                    # Wait before checking again
                    await asyncio.sleep(check_interval)
            except asyncio.CancelledError:
                self.logger.debug("Status monitor task cancelled")
            except Exception as e:
                self.logger.error(f"Unexpected error in status monitor: {e}")

        # Create a task to monitor message updates
        async def monitor_messages():
            """
            Monitor messages and emit message update events.

            This method periodically checks for message updates and emits events
            when messages change, similar to how the original Agent API's
            UpdateMessagesAndEmitChanges method works.
            """
            last_messages = []
            # Use SNAPSHOT_INTERVAL to exactly match the original Agent API's behavior
            # The original Agent API checks messages every snapshot interval (25ms)
            # This is defined in agentapi/lib/httpapi/server.go in the UpdateMessagesAndEmitChanges method
            check_interval = SNAPSHOT_INTERVAL

            try:
                while True:
                    try:
                        # Get current messages
                        messages_data = await self.get_messages()
                        current_messages = messages_data.get("messages", [])

                        # Compare with last messages
                        # First, check for new or updated messages
                        for message in current_messages:
                            # Find matching message in last_messages
                            found = False
                            for last_message in last_messages:
                                if last_message["id"] == message["id"]:
                                    found = True
                                    # Check if message has changed
                                    if last_message["content"] != message["content"]:
                                        # Message has changed, emit an event
                                        self.logger.debug(f"Message {message['id']} has changed")

                                        # Create a message update event
                                        event = {
                                            "type": "message_update",
                                            "data": {
                                                "id": message["id"],
                                                "role": message["role"],
                                                "message": message["content"],
                                                "time": message["time"]
                                            },
                                            "id": str(message["id"]),
                                            "timestamp": time.time()
                                        }

                                        # Buffer the event
                                        await buffer_event(event)
                                    break

                            # If message not found, it's new
                            if not found:
                                # New message, emit an event
                                self.logger.debug(f"New message {message['id']}")

                                # Create a message update event
                                event = {
                                    "type": "message_update",
                                    "data": {
                                        "id": message["id"],
                                        "role": message["role"],
                                        "message": message["content"],
                                        "time": message["time"]
                                    },
                                    "id": str(message["id"]),
                                    "timestamp": time.time()
                                }

                                # Buffer the event
                                await buffer_event(event)

                        # Update last messages
                        last_messages = current_messages

                    except Exception as e:
                        self.logger.error(f"Error monitoring messages: {e}")

                    # Wait before checking again
                    await asyncio.sleep(check_interval)
            except asyncio.CancelledError:
                self.logger.debug("Message monitor task cancelled")
            except Exception as e:
                self.logger.error(f"Unexpected error in message monitor: {e}")

        try:
            # Start heartbeat task
            heartbeat_task = asyncio.create_task(heartbeat())

            # Start event processor task
            event_processor_task = asyncio.create_task(process_event_buffer())

            # Start status monitor task
            status_monitor_task = asyncio.create_task(monitor_agent_status())

            # Start message monitor task
            message_monitor_task = asyncio.create_task(monitor_messages())

            # Fetch and send initial state events (similar to Agent API's currentStateAsEvents)
            if not initial_state_sent:
                try:
                    self.logger.info("Fetching initial state events...")

                    # Get current messages
                    messages_data = await self.get_messages()

                    # Get current agent status
                    agent_status = await self.get_agent_status()

                    # Create initial state events
                    initial_events = []

                    # Add message events
                    for message in messages_data.get("messages", []):
                        initial_events.append({
                            "type": "message_update",
                            "data": {
                                "id": message["id"],
                                "role": message["role"],
                                "message": message["content"],
                                "time": message["time"]
                            },
                            "id": str(message["id"]),
                            "timestamp": time.time()
                        })

                    # Add status event
                    initial_events.append({
                        "type": "status_change",
                        "data": {
                            "status": agent_status.value
                        },
                        "timestamp": time.time()
                    })

                    # Buffer initial events
                    self.logger.info(f"Sending {len(initial_events)} initial state events")
                    for event in initial_events:
                        await buffer_event(event)

                    initial_state_sent = True
                except Exception as e:
                    self.logger.error(f"Error fetching initial state: {e}")
                    # Continue even if we can't get initial state

            # Stream events with enhanced error handling and reconnection
            try:
                async for _ in self.stream_events(
                    callback=buffer_event,
                    reconnect=True,
                    max_reconnect_attempts=15,  # More attempts for this critical service
                    reconnect_initial_delay=0.5,  # Start with a shorter delay
                    reconnect_max_delay=60.0,  # Maximum 1 minute between attempts
                    reconnect_backoff_factor=1.5,  # Moderate backoff
                    reconnect_jitter=0.2,  # Add jitter to avoid thundering herd
                    last_event_id=last_event_id  # Use last event ID for reconnection
                ):
                    pass  # We don't need to do anything with the yielded events
            except Exception as e:
                # Log the error
                self.logger.error(f"Event stream disconnected: {e}")

                # Clean up resources
                if heartbeat_task and not heartbeat_task.done():
                    heartbeat_task.cancel()
                if event_processor_task and not event_processor_task.done():
                    event_processor_task.cancel()
                if status_monitor_task and not status_monitor_task.done():
                    status_monitor_task.cancel()
                if message_monitor_task and not message_monitor_task.done():
                    message_monitor_task.cancel()

                # Clear the event buffer
                async with event_buffer_lock:
                    event_buffer.clear()

                # Raise the exception to trigger reconnection
                raise

        except (AgentAPIError, TimeoutError) as e:
            self.logger.error(f"Fatal error in event stream: {e}")
            # Re-raise the exception to be handled by the caller
            raise
        except asyncio.CancelledError:
            self.logger.info("Event stream task cancelled")
            # Don't re-raise, allow clean cancellation
        except Exception as e:
            self.logger.error(f"Unexpected error in event stream to MCP: {e}")
            raise AgentAPIError(f"Unexpected error in event stream to MCP: {str(e)}")
        finally:
            # Clean up tasks
            for task, name in [
                (heartbeat_task, "heartbeat"),
                (event_processor_task, "event processor"),
                (status_monitor_task, "status monitor"),
                (message_monitor_task, "message monitor")
            ]:
                if task and not task.done():
                    self.logger.debug(f"Cancelling {name} task")
                    task.cancel()
                    try:
                        await asyncio.wait_for(asyncio.shield(task), timeout=2.0)
                    except (asyncio.TimeoutError, asyncio.CancelledError):
                        self.logger.debug(f"{name.capitalize()} task cancelled")
                    except Exception as e:
                        self.logger.error(f"Error cancelling {name} task: {e}")
