#!/usr/bin/env python3
"""
Error handling utilities for the MCP server.

This module provides standardized error handling functions for the MCP server,
ensuring consistent error responses across all endpoints.
"""

import logging
import traceback
from typing import Any, Dict, Optional, Union

from ..exceptions import MCPServerError, AgentAPIError
from ..constants import CORS_HEADERS

# Configure logging
logger = logging.getLogger("mcp-server-agentapi.error-handler")

def create_error_response(
    error_message: str,
    error_type: str = "AgentAPIError",
    status_code: int = 500,
    detail: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized error response that matches the original Agent API format.

    This function ensures all error responses follow the same format and provide
    consistent information to clients. It is designed to be used across all
    endpoints in the MCP server.

    Args:
        error_message: The main error message
        error_type: The type of error (e.g., "ValidationError", "AgentAPIError")
        status_code: The HTTP status code
        detail: Optional detailed error information
        context: Optional dictionary with additional error context

    Returns:
        A dictionary with the standardized error format
    """
    # Create the base error response
    response = {
        "error": error_message,
        "error_type": error_type,
        "status_code": status_code
    }

    # Add detail if provided
    if detail:
        response["detail"] = detail

    # Add context if provided (for debugging)
    if context:
        response["context"] = context

    # Log the error
    logger.error(f"Error: {error_message} ({error_type}, {status_code})")
    if detail:
        logger.debug(f"Error detail: {detail}")
    if context:
        logger.debug(f"Error context: {context}")

    return response

def handle_exception(
    exception: Exception,
    log_error: bool = True,
    include_traceback: bool = False
) -> Dict[str, Any]:
    """
    Handle an exception and convert it to a standardized error response.

    This function takes an exception and converts it to a standardized error
    response format. It handles both MCPServerError exceptions (which have
    additional context) and standard Python exceptions.

    Args:
        exception: The exception to handle
        log_error: Whether to log the error (default: True)
        include_traceback: Whether to include the traceback in the response (default: False)

    Returns:
        A dictionary with the standardized error format
    """
    # Get the exception details
    error_message = str(exception)
    error_type = exception.__class__.__name__
    
    # Default status code
    status_code = 500
    
    # Default detail
    detail = None
    
    # Default context
    context = None
    
    # Handle MCPServerError exceptions
    if isinstance(exception, MCPServerError):
        # Use the exception's message
        error_message = exception.message
        
        # Get the context from the exception
        context = exception.context
        
        # Include traceback if requested and available
        if include_traceback and exception.traceback:
            detail = exception.traceback
    
    # Handle AgentAPIError exceptions
    if isinstance(exception, AgentAPIError):
        # Use the status code from the exception if available
        status_code = getattr(exception, 'status_code', 500)
    
    # For other exceptions, capture the traceback if requested
    elif include_traceback:
        detail = traceback.format_exc()
    
    # Log the error if requested
    if log_error:
        logger.error(f"Exception: {error_type}: {error_message}")
        if detail:
            logger.debug(f"Exception detail: {detail}")
        if context:
            logger.debug(f"Exception context: {context}")
    
    # Create and return the standardized error response
    return create_error_response(
        error_message=error_message,
        error_type=error_type,
        status_code=status_code,
        detail=detail,
        context=context
    )

def add_cors_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """
    Add CORS headers to the response headers.

    This function adds the standard CORS headers to the response headers,
    ensuring consistent CORS handling across all endpoints.

    Args:
        headers: The existing response headers

    Returns:
        The response headers with CORS headers added
    """
    # Create a copy of the headers
    result = headers.copy()
    
    # Add CORS headers
    result.update(CORS_HEADERS)
    
    return result
