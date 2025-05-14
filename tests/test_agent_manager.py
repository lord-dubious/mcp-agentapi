#!/usr/bin/env python3
"""
Tests for the agent manager module.

This module contains tests for the agent detection, installation, and lifecycle
management functionality.
"""

import asyncio
import subprocess
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
import httpx

from src.agent_manager import (
    AgentManager, AgentInfo, AgentType, AgentInstallStatus, AgentRunningStatus
)
from src.config import Config
from src.exceptions import AgentDetectionError, AgentStartError, AgentStopError, TimeoutError


@pytest.fixture
def config():
    """Create a test configuration."""
    return Config()


@pytest.fixture
def agent_manager(config):
    """Create a test agent manager."""
    return AgentManager(config)


@pytest.mark.asyncio
async def test_initialize_agents(agent_manager):
    """Test initialization of agent information."""
    # Verify that all agent types are initialized
    for agent_type in AgentType:
        assert agent_type in agent_manager.agents
        assert isinstance(agent_manager.agents[agent_type], AgentInfo)
        assert agent_manager.agents[agent_type].agent_type == agent_type
        assert agent_manager.agents[agent_type].install_status == AgentInstallStatus.UNKNOWN
        assert agent_manager.agents[agent_type].running_status == AgentRunningStatus.UNKNOWN


@pytest.mark.asyncio
async def test_check_agent_api_installed(agent_manager):
    """Test checking if Agent API is installed."""
    # Mock the _check_command_exists method
    with patch.object(
        agent_manager, "_check_command_exists", new_callable=AsyncMock
    ) as mock_check_command:
        # Test when Agent API is installed
        mock_check_command.return_value = True
        result = await agent_manager._check_agent_api_installed()
        assert result is True
        mock_check_command.assert_called_once_with("agentapi")

        # Test when Agent API is not installed
        mock_check_command.reset_mock()
        mock_check_command.return_value = False
        result = await agent_manager._check_agent_api_installed()
        assert result is False
        mock_check_command.assert_called_once_with("agentapi")


@pytest.mark.asyncio
async def test_detect_agents(agent_manager):
    """Test detecting available agents."""
    # Mock the necessary methods
    with patch.object(
        agent_manager, "_check_agent_api_installed", new_callable=AsyncMock
    ) as mock_check_api, patch.object(
        agent_manager, "_detect_agent_with_timeout", new_callable=AsyncMock
    ) as mock_detect_agent, patch.object(
        agent_manager.config, "load_api_keys", new_callable=AsyncMock
    ) as mock_load_keys, patch(
        "src.agent_manager.httpx.AsyncClient", new_callable=MagicMock
    ) as mock_client_class:
        # Set up the mocks
        mock_check_api.return_value = True
        mock_load_keys.return_value = {}
        
        # Mock the API client
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock the API client's get_status method
        mock_client.get.return_value = AsyncMock()
        mock_client.get.return_value.status_code = 200
        mock_client.get.return_value.json.return_value = {
            "status": "stable",
            "agentType": "goose"
        }

        # Detect agents
        result = await agent_manager.detect_agents()

        # Verify the result
        assert result == agent_manager.agents
        mock_check_api.assert_called_once()
        mock_load_keys.assert_called_once_with(validate=False)
        assert mock_detect_agent.call_count > 0


@pytest.mark.asyncio
async def test_detect_agent(agent_manager):
    """Test detecting a specific agent."""
    # Mock the necessary methods
    with patch.object(
        agent_manager, "_check_agent_api_installed", new_callable=AsyncMock
    ) as mock_check_api, patch.object(
        agent_manager, "_check_command_exists", new_callable=AsyncMock
    ) as mock_check_command, patch.object(
        agent_manager, "_run_command", new_callable=AsyncMock
    ) as mock_run_command, patch.object(
        agent_manager, "_validate_agent_running", new_callable=AsyncMock
    ) as mock_validate_running:
        # Set up the mocks
        mock_check_api.return_value = True
        mock_check_command.return_value = True
        mock_run_command.return_value = (0, "goose", "")
        mock_validate_running.return_value = True

        # Detect the agent
        await agent_manager._detect_agent(AgentType.GOOSE)

        # Verify the result
        agent_info = agent_manager.agents[AgentType.GOOSE]
        assert agent_info.install_status == AgentInstallStatus.INSTALLED
        assert agent_info.running_status == AgentRunningStatus.RUNNING
        mock_check_api.assert_called_once()
        mock_check_command.assert_called_once_with("goose")
        mock_run_command.assert_called_once()
        mock_validate_running.assert_called_once_with(AgentType.GOOSE)


@pytest.mark.asyncio
async def test_install_agent(agent_manager):
    """Test installing an agent."""
    # Mock the necessary methods
    with patch.object(
        agent_manager, "_check_agent_api_installed", new_callable=AsyncMock
    ) as mock_check_api, patch.object(
        agent_manager, "install_agent_api", new_callable=AsyncMock
    ) as mock_install_api, patch.object(
        agent_manager, "_install_goose", new_callable=AsyncMock
    ) as mock_install_goose, patch.object(
        agent_manager, "_detect_agent", new_callable=AsyncMock
    ) as mock_detect_agent:
        # Set up the mocks
        mock_check_api.return_value = True
        mock_install_api.return_value = True
        mock_install_goose.return_value = True

        # Install the agent
        result = await agent_manager.install_agent(AgentType.GOOSE)

        # Verify the result
        assert result is True
        mock_check_api.assert_called_once()
        mock_install_api.assert_not_called()
        mock_install_goose.assert_called_once()
        mock_detect_agent.assert_called_once_with(AgentType.GOOSE)

        # Test when Agent API is not installed
        mock_check_api.reset_mock()
        mock_install_api.reset_mock()
        mock_install_goose.reset_mock()
        mock_detect_agent.reset_mock()

        mock_check_api.return_value = False
        mock_install_api.return_value = True

        # Install the agent
        result = await agent_manager.install_agent(AgentType.GOOSE)

        # Verify the result
        assert result is True
        mock_check_api.assert_called_once()
        mock_install_api.assert_called_once()
        mock_install_goose.assert_called_once()
        mock_detect_agent.assert_called_once_with(AgentType.GOOSE)


@pytest.mark.asyncio
async def test_start_agent(agent_manager):
    """Test starting an agent."""
    # Mock the necessary methods
    with patch.object(
        agent_manager, "_validate_agent_running", new_callable=AsyncMock
    ) as mock_validate_running, patch(
        "subprocess.Popen", new_callable=MagicMock
    ) as mock_popen:
        # Set up the mocks
        mock_validate_running.return_value = True
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        # Set up agent info
        agent_info = agent_manager.agents[AgentType.GOOSE]
        agent_info.install_status = AgentInstallStatus.INSTALLED
        agent_info.api_key_set = True

        # Start the agent
        result = await agent_manager.start_agent(AgentType.GOOSE)

        # Verify the result
        assert result == mock_process
        assert agent_info.process == mock_process
        assert agent_info.running_status == AgentRunningStatus.RUNNING
        mock_validate_running.assert_called_once_with(AgentType.GOOSE)
        mock_popen.assert_called_once()

        # Test when agent is not installed
        mock_validate_running.reset_mock()
        mock_popen.reset_mock()

        agent_info.install_status = AgentInstallStatus.NOT_INSTALLED
        agent_info.process = None
        agent_info.running_status = AgentRunningStatus.STOPPED

        # Start the agent (should raise an error)
        with pytest.raises(AgentStartError):
            await agent_manager.start_agent(AgentType.GOOSE)

        # Verify that no process was started
        mock_validate_running.assert_not_called()
        mock_popen.assert_not_called()


@pytest.mark.asyncio
async def test_stop_agent(agent_manager):
    """Test stopping an agent."""
    # Mock the necessary methods
    with patch.object(
        agent_manager, "stop_process", new_callable=AsyncMock
    ) as mock_stop_process:
        # Set up agent info
        agent_info = agent_manager.agents[AgentType.GOOSE]
        agent_info.process = MagicMock()
        agent_info.process.pid = 12345
        agent_info.running_status = AgentRunningStatus.RUNNING

        # Stop the agent
        result = await agent_manager.stop_agent(AgentType.GOOSE)

        # Verify the result
        assert result is True
        assert agent_info.process is None
        assert agent_info.running_status == AgentRunningStatus.STOPPED
        mock_stop_process.assert_called_once()

        # Test when agent is not running
        mock_stop_process.reset_mock()

        agent_info.process = None
        agent_info.running_status = AgentRunningStatus.STOPPED

        # Stop the agent
        result = await agent_manager.stop_agent(AgentType.GOOSE)

        # Verify the result
        assert result is True
        mock_stop_process.assert_not_called()


@pytest.mark.asyncio
async def test_restart_agent(agent_manager):
    """Test restarting an agent."""
    # Mock the necessary methods
    with patch.object(
        agent_manager, "stop_agent", new_callable=AsyncMock
    ) as mock_stop_agent, patch.object(
        agent_manager, "start_agent", new_callable=AsyncMock
    ) as mock_start_agent:
        # Set up the mocks
        mock_stop_agent.return_value = True
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_start_agent.return_value = mock_process

        # Restart the agent
        result = await agent_manager.restart_agent(AgentType.GOOSE)

        # Verify the result
        assert result == mock_process
        mock_stop_agent.assert_called_once_with(AgentType.GOOSE)
        mock_start_agent.assert_called_once_with(AgentType.GOOSE)


@pytest.mark.asyncio
async def test_monitor_agent(agent_manager):
    """Test monitoring an agent."""
    # Mock the necessary methods
    with patch.object(
        agent_manager, "_validate_agent_running", new_callable=AsyncMock
    ) as mock_validate_running, patch.object(
        agent_manager, "restart_agent", new_callable=AsyncMock
    ) as mock_restart_agent, patch(
        "asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        # Set up the mocks
        mock_validate_running.side_effect = [True, False, True]
        mock_restart_agent.return_value = MagicMock()
        
        # Set up to exit after 3 iterations
        mock_sleep.side_effect = [None, None, asyncio.CancelledError()]

        # Monitor the agent
        try:
            await agent_manager.monitor_agent(AgentType.GOOSE, auto_reconnect=True)
        except asyncio.CancelledError:
            pass

        # Verify the calls
        assert mock_validate_running.call_count == 3
        assert mock_restart_agent.call_count == 1
        assert mock_sleep.call_count == 3
