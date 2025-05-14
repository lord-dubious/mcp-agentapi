#!/usr/bin/env python3
"""
Tests for the exceptions module.

This module contains tests for the custom exceptions used in the MCP server.
"""

import unittest

from src.exceptions import (
    AgentAPIError, ConfigurationError, APIKeyError, AgentDetectionError,
    AgentStartError, AgentStopError, ResourceError, HealthCheckError,
    TimeoutError, EventStreamError
)


class TestExceptions(unittest.TestCase):
    """Tests for the custom exceptions."""

    def test_agent_api_error(self):
        """Test the AgentAPIError exception."""
        # Test with minimal parameters
        error = AgentAPIError("Test error")
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertIsNone(error.status_code)
        self.assertIsNone(error.response_text)
        self.assertEqual(error.context, {})

        # Test with all parameters
        error = AgentAPIError(
            message="Test error",
            status_code=404,
            response_text="Not Found",
            context={"url": "http://localhost:3284/status"}
        )
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.status_code, 404)
        self.assertEqual(error.response_text, "Not Found")
        self.assertEqual(error.context, {"url": "http://localhost:3284/status"})

    def test_configuration_error(self):
        """Test the ConfigurationError exception."""
        # Test with minimal parameters
        error = ConfigurationError("Test error")
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.context, {})

        # Test with context
        error = ConfigurationError(
            message="Test error",
            context={"config_file": "/path/to/config.json"}
        )
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.context, {"config_file": "/path/to/config.json"})

    def test_api_key_error(self):
        """Test the APIKeyError exception."""
        # Test with minimal parameters
        error = APIKeyError("Test error")
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.context, {})

        # Test with context
        error = APIKeyError(
            message="Test error",
            context={"api_key_env": "OPENAI_API_KEY"}
        )
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.context, {"api_key_env": "OPENAI_API_KEY"})

    def test_agent_detection_error(self):
        """Test the AgentDetectionError exception."""
        # Test with minimal parameters
        error = AgentDetectionError("Test error")
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.context, {})

        # Test with context
        error = AgentDetectionError(
            message="Test error",
            context={"agent_type": "goose"}
        )
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.context, {"agent_type": "goose"})

    def test_agent_start_error(self):
        """Test the AgentStartError exception."""
        # Test with minimal parameters
        error = AgentStartError("Test error")
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.context, {})

        # Test with context
        error = AgentStartError(
            message="Test error",
            context={"agent_type": "goose"}
        )
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.context, {"agent_type": "goose"})

    def test_agent_stop_error(self):
        """Test the AgentStopError exception."""
        # Test with minimal parameters
        error = AgentStopError("Test error")
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.context, {})

        # Test with context
        error = AgentStopError(
            message="Test error",
            context={"agent_type": "goose"}
        )
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.context, {"agent_type": "goose"})

    def test_resource_error(self):
        """Test the ResourceError exception."""
        # Test with minimal parameters
        error = ResourceError("Test error")
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.context, {})

        # Test with context
        error = ResourceError(
            message="Test error",
            context={"resource_key": "test_process"}
        )
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.context, {"resource_key": "test_process"})

    def test_health_check_error(self):
        """Test the HealthCheckError exception."""
        # Test with minimal parameters
        error = HealthCheckError("Test error")
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.context, {})

        # Test with context
        error = HealthCheckError(
            message="Test error",
            context={"component": "agent_api"}
        )
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.context, {"component": "agent_api"})

    def test_timeout_error(self):
        """Test the TimeoutError exception."""
        # Test with minimal parameters
        error = TimeoutError("Test error")
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.operation, None)
        self.assertEqual(error.timeout, None)
        self.assertEqual(error.context, {})

        # Test with all parameters
        error = TimeoutError(
            message="Test error",
            operation="get_status",
            timeout=30.0,
            context={"url": "http://localhost:3284/status"}
        )
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.operation, "get_status")
        self.assertEqual(error.timeout, 30.0)
        self.assertEqual(error.context, {"url": "http://localhost:3284/status"})

    def test_event_stream_error(self):
        """Test the EventStreamError exception."""
        # Test with minimal parameters
        error = EventStreamError("Test error")
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.context, {})

        # Test with context
        error = EventStreamError(
            message="Test error",
            context={"url": "http://localhost:3284/events"}
        )
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.context, {"url": "http://localhost:3284/events"})


if __name__ == "__main__":
    unittest.main()
