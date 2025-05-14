#!/usr/bin/env python3
"""
Data models for the MCP server for Agent API.

This module contains the data models and enums used throughout the MCP server.
"""

from dataclasses import dataclass
from enum import Enum


class AgentType(str, Enum):
    """Agent types as defined in the Agent API."""
    CLAUDE = "claude"
    GOOSE = "goose"
    AIDER = "aider"
    CODEX = "codex"
    CUSTOM = "custom"


class MessageType(str, Enum):
    """Message types as defined in the Agent API."""
    USER = "user"
    RAW = "raw"


class ConversationRole(str, Enum):
    """Conversation roles as defined in the Agent API."""
    USER = "user"
    AGENT = "agent"


class AgentStatus(str, Enum):
    """Agent status values as defined in the Agent API."""
    RUNNING = "running"
    STABLE = "stable"


class EventType(str, Enum):
    """Event types as defined in the Agent API."""
    MESSAGE_UPDATE = "message_update"
    STATUS_CHANGE = "status_change"
    SCREEN_UPDATE = "screen_update"


@dataclass
class Message:
    """Message model based on Agent API schema."""
    id: int
    content: str
    role: ConversationRole
    time: str


@dataclass
class MessageUpdateBody:
    """Message update event body."""
    id: int
    role: ConversationRole
    message: str
    time: str


@dataclass
class StatusChangeBody:
    """Status change event body."""
    status: AgentStatus


@dataclass
class ScreenUpdateBody:
    """Screen update event body."""
    screen: str


def convert_to_agent_type(agent_type_str: str) -> AgentType:
    """
    Convert a string to an AgentType enum value.

    Args:
        agent_type_str: String representation of the agent type

    Returns:
        AgentType enum value

    Raises:
        ValueError: If the string is not a valid agent type
    """
    try:
        return AgentType(agent_type_str.lower())
    except ValueError as e:
        valid_types = ", ".join([t.value for t in AgentType])
        raise ValueError(f"Invalid agent type: {agent_type_str}. Valid types are: {valid_types}") from e

