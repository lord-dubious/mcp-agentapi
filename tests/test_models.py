#!/usr/bin/env python3
"""
Tests for the models module.

This module contains tests for the data models used in the MCP server,
including enums, dataclasses, and other data structures.
"""

import unittest
from enum import Enum

from src.models import (
    AgentType, AgentStatus, MessageType, ConversationRole,
    Message, AgentInstallStatus, AgentRunningStatus, AgentInfo
)


class TestEnums(unittest.TestCase):
    """Tests for the enum classes."""

    def test_agent_type(self):
        """Test the AgentType enum."""
        # Verify the enum values
        self.assertEqual(AgentType.GOOSE.value, "goose")
        self.assertEqual(AgentType.AIDER.value, "aider")
        self.assertEqual(AgentType.CLAUDE.value, "claude")
        self.assertEqual(AgentType.CODEX.value, "codex")
        self.assertEqual(AgentType.CUSTOM.value, "custom")

        # Test conversion from string
        self.assertEqual(AgentType("goose"), AgentType.GOOSE)
        self.assertEqual(AgentType("aider"), AgentType.AIDER)
        self.assertEqual(AgentType("claude"), AgentType.CLAUDE)
        self.assertEqual(AgentType("codex"), AgentType.CODEX)
        self.assertEqual(AgentType("custom"), AgentType.CUSTOM)

        # Test invalid value
        with self.assertRaises(ValueError):
            AgentType("invalid")

    def test_agent_status(self):
        """Test the AgentStatus enum."""
        # Verify the enum values
        self.assertEqual(AgentStatus.RUNNING.value, "running")
        self.assertEqual(AgentStatus.STABLE.value, "stable")

        # Test conversion from string
        self.assertEqual(AgentStatus("running"), AgentStatus.RUNNING)
        self.assertEqual(AgentStatus("stable"), AgentStatus.STABLE)

        # Test invalid value
        with self.assertRaises(ValueError):
            AgentStatus("invalid")

    def test_message_type(self):
        """Test the MessageType enum."""
        # Verify the enum values
        self.assertEqual(MessageType.USER.value, "user")
        self.assertEqual(MessageType.RAW.value, "raw")

        # Test conversion from string
        self.assertEqual(MessageType("user"), MessageType.USER)
        self.assertEqual(MessageType("raw"), MessageType.RAW)

        # Test invalid value
        with self.assertRaises(ValueError):
            MessageType("invalid")

    def test_conversation_role(self):
        """Test the ConversationRole enum."""
        # Verify the enum values
        self.assertEqual(ConversationRole.USER.value, "user")
        self.assertEqual(ConversationRole.AGENT.value, "agent")

        # Test conversion from string
        self.assertEqual(ConversationRole("user"), ConversationRole.USER)
        self.assertEqual(ConversationRole("agent"), ConversationRole.AGENT)

        # Test invalid value
        with self.assertRaises(ValueError):
            ConversationRole("invalid")

    def test_agent_install_status(self):
        """Test the AgentInstallStatus enum."""
        # Verify the enum values
        self.assertEqual(AgentInstallStatus.UNKNOWN.value, "unknown")
        self.assertEqual(AgentInstallStatus.INSTALLED.value, "installed")
        self.assertEqual(AgentInstallStatus.NOT_INSTALLED.value, "not_installed")
        self.assertEqual(AgentInstallStatus.INSTALLING.value, "installing")
        self.assertEqual(AgentInstallStatus.INSTALL_FAILED.value, "install_failed")

        # Test conversion from string
        self.assertEqual(AgentInstallStatus("unknown"), AgentInstallStatus.UNKNOWN)
        self.assertEqual(AgentInstallStatus("installed"), AgentInstallStatus.INSTALLED)
        self.assertEqual(AgentInstallStatus("not_installed"), AgentInstallStatus.NOT_INSTALLED)
        self.assertEqual(AgentInstallStatus("installing"), AgentInstallStatus.INSTALLING)
        self.assertEqual(AgentInstallStatus("install_failed"), AgentInstallStatus.INSTALL_FAILED)

        # Test invalid value
        with self.assertRaises(ValueError):
            AgentInstallStatus("invalid")

    def test_agent_running_status(self):
        """Test the AgentRunningStatus enum."""
        # Verify the enum values
        self.assertEqual(AgentRunningStatus.UNKNOWN.value, "unknown")
        self.assertEqual(AgentRunningStatus.RUNNING.value, "running")
        self.assertEqual(AgentRunningStatus.STOPPED.value, "stopped")
        self.assertEqual(AgentRunningStatus.STARTING.value, "starting")
        self.assertEqual(AgentRunningStatus.STOPPING.value, "stopping")
        self.assertEqual(AgentRunningStatus.START_FAILED.value, "start_failed")
        self.assertEqual(AgentRunningStatus.STOP_FAILED.value, "stop_failed")

        # Test conversion from string
        self.assertEqual(AgentRunningStatus("unknown"), AgentRunningStatus.UNKNOWN)
        self.assertEqual(AgentRunningStatus("running"), AgentRunningStatus.RUNNING)
        self.assertEqual(AgentRunningStatus("stopped"), AgentRunningStatus.STOPPED)
        self.assertEqual(AgentRunningStatus("starting"), AgentRunningStatus.STARTING)
        self.assertEqual(AgentRunningStatus("stopping"), AgentRunningStatus.STOPPING)
        self.assertEqual(AgentRunningStatus("start_failed"), AgentRunningStatus.START_FAILED)
        self.assertEqual(AgentRunningStatus("stop_failed"), AgentRunningStatus.STOP_FAILED)

        # Test invalid value
        with self.assertRaises(ValueError):
            AgentRunningStatus("invalid")


class TestMessage(unittest.TestCase):
    """Tests for the Message class."""

    def test_init(self):
        """Test initialization of Message."""
        # Test with minimal parameters
        message = Message(
            id=1,
            content="Hello",
            role=ConversationRole.USER,
            time="2023-01-01T00:00:00Z"
        )
        self.assertEqual(message.id, 1)
        self.assertEqual(message.content, "Hello")
        self.assertEqual(message.role, ConversationRole.USER)
        self.assertEqual(message.time, "2023-01-01T00:00:00Z")

        # Test with string role
        message = Message(
            id=2,
            content="Hi there!",
            role="agent",
            time="2023-01-01T00:00:01Z"
        )
        self.assertEqual(message.id, 2)
        self.assertEqual(message.content, "Hi there!")
        self.assertEqual(message.role, ConversationRole.AGENT)
        self.assertEqual(message.time, "2023-01-01T00:00:01Z")

        # Test with invalid role
        with self.assertRaises(ValueError):
            Message(
                id=3,
                content="Invalid",
                role="invalid",
                time="2023-01-01T00:00:02Z"
            )


class TestAgentInfo(unittest.TestCase):
    """Tests for the AgentInfo class."""

    def test_init(self):
        """Test initialization of AgentInfo."""
        # Test with minimal parameters
        agent_info = AgentInfo(agent_type=AgentType.GOOSE)
        self.assertEqual(agent_info.agent_type, AgentType.GOOSE)
        self.assertEqual(agent_info.install_status, AgentInstallStatus.UNKNOWN)
        self.assertEqual(agent_info.running_status, AgentRunningStatus.UNKNOWN)
        self.assertIsNone(agent_info.process)
        self.assertIsNone(agent_info.command)
        self.assertIsNone(agent_info.version)
        self.assertFalse(agent_info.api_key_set)
        self.assertFalse(agent_info.api_key_valid)

        # Test with all parameters
        agent_info = AgentInfo(
            agent_type=AgentType.AIDER,
            install_status=AgentInstallStatus.INSTALLED,
            running_status=AgentRunningStatus.RUNNING,
            process=None,
            command="aider",
            version="1.0.0",
            api_key_set=True,
            api_key_valid=True
        )
        self.assertEqual(agent_info.agent_type, AgentType.AIDER)
        self.assertEqual(agent_info.install_status, AgentInstallStatus.INSTALLED)
        self.assertEqual(agent_info.running_status, AgentRunningStatus.RUNNING)
        self.assertIsNone(agent_info.process)
        self.assertEqual(agent_info.command, "aider")
        self.assertEqual(agent_info.version, "1.0.0")
        self.assertTrue(agent_info.api_key_set)
        self.assertTrue(agent_info.api_key_valid)


if __name__ == "__main__":
    unittest.main()
