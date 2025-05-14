#!/usr/bin/env python3
"""
Pytest configuration and fixtures.

This module contains fixtures and configuration for pytest.
"""

import asyncio
import os
import sys
from unittest.mock import MagicMock, AsyncMock

import pytest
import httpx

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import Config
from src.models import AgentType
from src.agent_manager import AgentManager
from src.resource_manager import ResourceManager
from src.health_check import HealthCheck
from src.context import AgentAPIContext


@pytest.fixture
def event_loop():
    """Create an event loop for tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def config():
    """Create a test configuration."""
    config = Config()
    config.agent_api_url = "http://localhost:3284"
    config.agent_type = AgentType.GOOSE
    return config


@pytest.fixture
def http_client():
    """Create a mock HTTP client."""
    return MagicMock(spec=httpx.AsyncClient)


@pytest.fixture
def resource_manager():
    """Create a test resource manager."""
    return ResourceManager()


@pytest.fixture
def agent_manager(config, resource_manager):
    """Create a test agent manager."""
    return AgentManager(config, resource_manager)


@pytest.fixture
def health_check(config, http_client):
    """Create a test health check."""
    return HealthCheck(config, http_client)


@pytest.fixture
def app_context(config, http_client, agent_manager, resource_manager, health_check):
    """Create a test application context."""
    context = AgentAPIContext()
    context.config = config
    context.http_client = http_client
    context.agent_manager = agent_manager
    context.resource_manager = resource_manager
    context.health_check = health_check
    context.agent_api_url = config.agent_api_url
    context.agent_type = config.agent_type
    return context


@pytest.fixture
def mock_http_response():
    """Create a mock HTTP response."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = {"status": "stable"}
    return response


@pytest.fixture
def mock_process():
    """Create a mock subprocess.Popen instance."""
    process = MagicMock(spec=subprocess.Popen)
    process.pid = 12345
    process.poll.return_value = None
    process.wait.return_value = 0
    return process


@pytest.fixture
def mock_task():
    """Create a mock asyncio.Task instance."""
    task = MagicMock(spec=asyncio.Task)
    task.done.return_value = False
    task.cancelled.return_value = False
    return task
