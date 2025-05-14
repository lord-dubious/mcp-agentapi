#!/usr/bin/env python3
"""
Tests for the error handler module.

This module contains tests for the error handler module, including
the create_error_response and handle_exception functions.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.utils.error_handler import create_error_response, handle_exception, add_cors_headers
from src.exceptions import MCPServerError, AgentAPIError


def test_create_error_response():
    """Test creating a standardized error response."""
    # Test with minimal parameters
    response = create_error_response("Test error")
    assert response["error"] == "Test error"
    assert response["error_type"] == "AgentAPIError"
    assert response["status_code"] == 500
    assert "detail" not in response
    assert "context" not in response

    # Test with all parameters
    response = create_error_response(
        error_message="Test error",
        error_type="ValidationError",
        status_code=400,
        detail="Invalid input",
        context={"field": "username"}
    )
    assert response["error"] == "Test error"
    assert response["error_type"] == "ValidationError"
    assert response["status_code"] == 400
    assert response["detail"] == "Invalid input"
    assert response["context"] == {"field": "username"}


def test_handle_exception():
    """Test handling exceptions."""
    # Test with a standard exception
    exception = ValueError("Invalid value")
    response = handle_exception(exception, log_error=False)
    assert response["error"] == "Invalid value"
    assert response["error_type"] == "ValueError"
    assert response["status_code"] == 500
    assert "detail" not in response
    assert "context" not in response

    # Test with an MCPServerError
    exception = MCPServerError("Server error", context={"server": "test"})
    response = handle_exception(exception, log_error=False)
    assert response["error"] == "Server error"
    assert response["error_type"] == "MCPServerError"
    assert response["status_code"] == 500
    assert "context" in response
    assert response["context"] == {"server": "test"}

    # Test with an AgentAPIError with status code
    exception = AgentAPIError(
        message="API error",
        status_code=404,
        response_text="Not found",
        context={"url": "http://example.com"}
    )
    response = handle_exception(exception, log_error=False)
    assert response["error"] == "API error"
    assert response["error_type"] == "AgentAPIError"
    assert response["status_code"] == 404
    assert "context" in response
    assert response["context"] == {"url": "http://example.com"}

    # Test with include_traceback=True
    with patch("traceback.format_exc", return_value="Traceback: ..."):
        exception = ValueError("Invalid value")
        response = handle_exception(exception, log_error=False, include_traceback=True)
        assert response["error"] == "Invalid value"
        assert response["error_type"] == "ValueError"
        assert response["status_code"] == 500
        assert "detail" in response
        assert response["detail"] == "Traceback: ..."


def test_add_cors_headers():
    """Test adding CORS headers."""
    # Test with empty headers
    headers = {}
    result = add_cors_headers(headers)
    assert "Access-Control-Allow-Origin" in result
    assert "Access-Control-Allow-Methods" in result
    assert "Access-Control-Allow-Headers" in result
    assert "Access-Control-Expose-Headers" in result
    assert "Access-Control-Max-Age" in result

    # Test with existing headers
    headers = {"Content-Type": "application/json"}
    result = add_cors_headers(headers)
    assert "Content-Type" in result
    assert result["Content-Type"] == "application/json"
    assert "Access-Control-Allow-Origin" in result
