#!/usr/bin/env python3
"""
Custom exceptions for the MCP server for Agent API.

This module defines custom exceptions used throughout the MCP server
to provide more specific error information and enable better error handling.
Each exception class includes detailed information about the error context
to facilitate debugging and error reporting.
"""

import traceback
import sys
from typing import Any, Dict, Optional, List, Union


class MCPServerError(Exception):
    """
    Base exception for all MCP server errors.

    This class provides common functionality for all MCP server exceptions,
    including error context tracking, stack trace capture, and formatted
    error messages.
    """
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception with a message and optional context.

        Args:
            message: Error message
            context: Optional dictionary with additional error context
        """
        self.message = message
        self.context = context or {}
        self.timestamp = self.context.get('timestamp', None)
        self.traceback = traceback.format_exc() if sys.exc_info()[0] else None
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the exception to a dictionary for serialization.

        This method formats the error in a way that's compatible with both:
        1. The original Agent API error format
        2. The MCP server error format

        Returns:
            Dictionary representation of the exception
        """
        # Create a standard error response that matches the Agent API format
        result = {
            'error': self.message,
            'error_type': self.__class__.__name__,
            'detail': str(self),
        }

        # Add additional context for MCP clients
        if self.context:
            result['context'] = self.context

        # Include traceback for debugging (only in debug mode)
        if self.traceback and self.traceback != 'NoneType: None\n':
            result['traceback'] = self.traceback

        return result

    def to_mcp_error(self) -> Dict[str, Any]:
        """
        Convert the exception to an MCP-compatible error format.

        This method formats the error according to the MCP specification,
        which requires a specific format for error responses.

        Returns:
            MCP-compatible error dictionary
        """
        # Get the error code based on the exception type
        error_code = self._get_error_code()

        # Create an MCP-compatible error response
        result = {
            'code': error_code,
            'message': self.message,
            'data': {
                'type': self.__class__.__name__,
                'detail': str(self)
            }
        }

        # Add additional context if available
        if self.context:
            result['data']['context'] = self.context

        return result

    def _get_error_code(self) -> int:
        """
        Get the error code for this exception type.

        Error codes follow the JSON-RPC 2.0 specification:
        - Standard error codes: -32700 to -32603
        - Custom error codes: -32000 to -32099

        Returns:
            Error code as an integer
        """
        # Map exception types to error codes
        error_codes = {
            'AgentAPIError': -32000,
            'AgentDetectionError': -32001,
            'AgentStartError': -32002,
            'AgentInstallError': -32003,
            'ConfigurationError': -32010,
            'APIKeyError': -32011,
            'ResourceError': -32020,
            'TimeoutError': -32030,
            'EventStreamError': -32040,
            'MCPServerError': -32603,  # Default to Internal Error
        }

        # Get the error code for this exception type
        return error_codes.get(self.__class__.__name__, -32603)

    def __str__(self) -> str:
        """
        Get a string representation of the exception.

        Returns:
            Formatted error message with context
        """
        parts = [f"{self.__class__.__name__}: {self.message}"]

        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"Context: {context_str}")

        return " | ".join(parts)


class AgentAPIError(MCPServerError):
    """
    Exception raised for Agent API errors.

    This exception is used when there's an error communicating with the Agent API,
    such as HTTP errors, connection issues, or invalid responses.
    """
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_text: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            status_code: HTTP status code (if applicable)
            response_text: Response text (if applicable)
            context: Optional dictionary with additional error context
        """
        self.status_code = status_code
        self.response_text = response_text

        # Add status code and response text to context
        context = context or {}
        if status_code is not None:
            context['status_code'] = status_code
        if response_text is not None:
            context['response_text'] = response_text

        super().__init__(message, context)


class AgentDetectionError(MCPServerError):
    """
    Exception raised when agent detection fails.

    This exception is used when the system fails to detect if an agent
    is installed or running.
    """
    def __init__(
        self,
        message: str,
        agent_type: Optional[str] = None,
        detection_steps: Optional[Dict[str, bool]] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            agent_type: Type of agent being detected
            detection_steps: Dictionary of detection steps and their results
            context: Optional dictionary with additional error context
        """
        context = context or {}
        if agent_type is not None:
            context['agent_type'] = agent_type
        if detection_steps is not None:
            context['detection_steps'] = detection_steps

        super().__init__(message, context)


class AgentSwitchError(MCPServerError):
    """
    Exception raised when agent switching fails.

    This exception is used when the system fails to switch from one agent
    to another.
    """
    def __init__(
        self,
        message: str,
        from_agent: Optional[str] = None,
        to_agent: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            from_agent: Current agent type
            to_agent: Target agent type
            context: Optional dictionary with additional error context
        """
        context = context or {}
        if from_agent is not None:
            context['from_agent'] = from_agent
        if to_agent is not None:
            context['to_agent'] = to_agent

        super().__init__(message, context)


class AgentStartError(MCPServerError):
    """
    Exception raised when agent starting fails.

    This exception is used when the system fails to start an agent.
    """
    def __init__(
        self,
        message: str,
        agent_type: Optional[str] = None,
        command: Optional[List[str]] = None,
        exit_code: Optional[int] = None,
        stderr: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            agent_type: Type of agent being started
            command: Command used to start the agent
            exit_code: Exit code of the agent process (if available)
            stderr: Standard error output from the agent process
            context: Optional dictionary with additional error context
        """
        context = context or {}
        if agent_type is not None:
            context['agent_type'] = agent_type
        if command is not None:
            context['command'] = command
        if exit_code is not None:
            context['exit_code'] = exit_code
        if stderr is not None:
            context['stderr'] = stderr

        super().__init__(message, context)


class AgentStopError(MCPServerError):
    """
    Exception raised when agent stopping fails.

    This exception is used when the system fails to stop an agent.
    """
    def __init__(
        self,
        message: str,
        agent_type: Optional[str] = None,
        pid: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            agent_type: Type of agent being stopped
            pid: Process ID of the agent
            context: Optional dictionary with additional error context
        """
        context = context or {}
        if agent_type is not None:
            context['agent_type'] = agent_type
        if pid is not None:
            context['pid'] = pid

        super().__init__(message, context)


class AgentInstallError(MCPServerError):
    """
    Exception raised when agent installation fails.

    This exception is used when the system fails to install an agent.
    """
    def __init__(
        self,
        message: str,
        agent_type: Optional[str] = None,
        command: Optional[List[str]] = None,
        exit_code: Optional[int] = None,
        stderr: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            agent_type: Type of agent being installed
            command: Command used to install the agent
            exit_code: Exit code of the installation process
            stderr: Standard error output from the installation process
            context: Optional dictionary with additional error context
        """
        context = context or {}
        if agent_type is not None:
            context['agent_type'] = agent_type
        if command is not None:
            context['command'] = command
        if exit_code is not None:
            context['exit_code'] = exit_code
        if stderr is not None:
            context['stderr'] = stderr

        super().__init__(message, context)


class ConfigurationError(MCPServerError):
    """
    Exception raised for configuration errors.

    This exception is used when there's an error in the configuration,
    such as missing or invalid configuration values.
    """
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            config_key: Configuration key that caused the error
            config_value: Configuration value that caused the error
            context: Optional dictionary with additional error context
        """
        context = context or {}
        if config_key is not None:
            context['config_key'] = config_key
        if config_value is not None:
            context['config_value'] = str(config_value)

        super().__init__(message, context)


class APIKeyError(ConfigurationError):
    """
    Exception raised for API key errors.

    This exception is used when there's an error with API keys,
    such as missing or invalid API keys.
    """
    def __init__(
        self,
        message: str,
        api_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            api_name: Name of the API (e.g., 'openai', 'anthropic')
            context: Optional dictionary with additional error context
        """
        context = context or {}
        if api_name is not None:
            context['api_name'] = api_name

        super().__init__(message, context)


class ResourceError(MCPServerError):
    """
    Exception raised for resource management errors.

    This exception is used when there's an error managing resources,
    such as processes, tasks, or custom resources.
    """
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_key: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            resource_type: Type of resource (e.g., 'process', 'task')
            resource_key: Key or identifier of the resource
            context: Optional dictionary with additional error context
        """
        context = context or {}
        if resource_type is not None:
            context['resource_type'] = resource_type
        if resource_key is not None:
            context['resource_key'] = resource_key

        super().__init__(message, context)


class TimeoutError(MCPServerError):
    """
    Exception raised when an operation times out.

    This exception is used when an operation takes too long to complete.
    """
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        timeout: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            operation: Name of the operation that timed out
            timeout: Timeout value in seconds
            context: Optional dictionary with additional error context
        """
        context = context or {}
        if operation is not None:
            context['operation'] = operation
        if timeout is not None:
            context['timeout'] = timeout

        super().__init__(message, context)


class ConcurrencyError(MCPServerError):
    """
    Exception raised for concurrency-related errors.

    This exception is used when there's an error related to concurrent operations,
    such as deadlocks or race conditions.
    """
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            operation: Name of the operation that encountered a concurrency issue
            context: Optional dictionary with additional error context
        """
        context = context or {}
        if operation is not None:
            context['operation'] = operation

        super().__init__(message, context)


class HealthCheckError(MCPServerError):
    """
    Exception raised for health check errors.

    This exception is used when a health check fails.
    """
    def __init__(
        self,
        message: str,
        component: Optional[str] = None,
        status: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            component: Name of the component that failed the health check
            status: Status of the component
            context: Optional dictionary with additional error context
        """
        context = context or {}
        if component is not None:
            context['component'] = component
        if status is not None:
            context['status'] = status

        super().__init__(message, context)


class EventStreamError(MCPServerError):
    """
    Exception raised for event stream errors.

    This exception is used when there's an error with the event stream,
    such as connection issues or parsing errors.
    """
    def __init__(
        self,
        message: str,
        stream_url: Optional[str] = None,
        event_count: Optional[int] = None,
        last_event_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            stream_url: URL of the event stream
            event_count: Number of events processed before the error
            last_event_id: ID of the last event processed
            context: Optional dictionary with additional error context
        """
        context = context or {}
        if stream_url is not None:
            context['stream_url'] = stream_url
        if event_count is not None:
            context['event_count'] = event_count
        if last_event_id is not None:
            context['last_event_id'] = last_event_id

        super().__init__(message, context)
