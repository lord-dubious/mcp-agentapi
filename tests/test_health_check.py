#!/usr/bin/env python3
"""
Tests for the health check module.

This module contains tests for the health check functionality,
including monitoring the health of the MCP server and its components.
"""

import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
import httpx

from src.health_check import HealthCheck
from src.config import Config
from src.exceptions import HealthCheckError


@pytest.fixture
def config():
    """Create a test configuration."""
    config = Config()
    config.agent_api_url = "http://localhost:3284"
    return config


@pytest.fixture
def http_client():
    """Create a test HTTP client."""
    return MagicMock(spec=httpx.AsyncClient)


@pytest.fixture
def health_check(config, http_client):
    """Create a test health check."""
    return HealthCheck(config, http_client)


@pytest.mark.asyncio
async def test_init(config, http_client):
    """Test initialization of HealthCheck."""
    health_check = HealthCheck(config, http_client)
    
    # Verify the initialization
    assert health_check.config == config
    assert health_check.http_client == http_client
    assert health_check.agent_api_url == config.agent_api_url
    assert health_check._health_check_task is None
    assert health_check._last_check_time == 0
    assert health_check._health_status["status"] == "unknown"
    assert health_check._health_status["agent_api"]["status"] == "unknown"
    assert health_check._health_status["agent"]["status"] == "unknown"
    assert health_check._health_status["mcp_server"]["status"] == "unknown"
    assert health_check._health_status["resources"]["status"] == "unknown"
    assert health_check._is_running is False


@pytest.mark.asyncio
async def test_start_stop(health_check):
    """Test starting and stopping health checks."""
    # Mock the _run_health_checks method
    with patch.object(health_check, "_run_health_checks", new_callable=AsyncMock) as mock_run_checks:
        # Start health checks
        await health_check.start()
        
        # Verify that health checks were started
        assert health_check._is_running is True
        assert health_check._health_check_task is not None
        
        # Stop health checks
        await health_check.stop()
        
        # Verify that health checks were stopped
        assert health_check._is_running is False
        assert health_check._health_check_task is None
        
        # Test starting when already running
        health_check._is_running = True
        await health_check.start()
        
        # Verify that health checks were not started again
        assert mock_run_checks.call_count == 1
        
        # Test stopping when not running
        health_check._is_running = False
        await health_check.stop()
        
        # Verify that no error occurred
        assert health_check._health_check_task is None


@pytest.mark.asyncio
async def test_run_health_checks(health_check):
    """Test running health checks."""
    # Mock the check_health method
    with patch.object(health_check, "check_health", new_callable=AsyncMock) as mock_check_health, \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        # Set up the mocks
        mock_check_health.return_value = {"status": "healthy"}
        
        # Set up to exit after 3 iterations
        mock_sleep.side_effect = [None, None, asyncio.CancelledError()]
        
        # Start health checks
        health_check._is_running = True
        
        # Run health checks
        try:
            await health_check._run_health_checks()
        except asyncio.CancelledError:
            pass
        
        # Verify that health checks were run
        assert mock_check_health.call_count == 3
        assert mock_sleep.call_count == 3


@pytest.mark.asyncio
async def test_check_health(health_check):
    """Test checking health."""
    # Mock the component check methods
    with patch.object(health_check, "_check_agent_api", new_callable=AsyncMock) as mock_check_api, \
         patch.object(health_check, "_check_agent", new_callable=AsyncMock) as mock_check_agent, \
         patch.object(health_check, "_check_resources", new_callable=AsyncMock) as mock_check_resources:
        # Set up the mocks
        mock_check_api.return_value = {"status": "healthy", "last_check": time.time()}
        mock_check_agent.return_value = {"status": "healthy", "last_check": time.time()}
        mock_check_resources.return_value = {"status": "healthy", "last_check": time.time()}
        
        # Check health
        result = await health_check.check_health()
        
        # Verify the result
        assert result["status"] == "healthy"
        assert result["agent_api"]["status"] == "healthy"
        assert result["agent"]["status"] == "healthy"
        assert result["mcp_server"]["status"] == "healthy"
        assert result["resources"]["status"] == "healthy"
        mock_check_api.assert_called_once()
        mock_check_agent.assert_called_once()
        mock_check_resources.assert_called_once()
        
        # Test with unhealthy agent API
        mock_check_api.reset_mock()
        mock_check_agent.reset_mock()
        mock_check_resources.reset_mock()
        
        mock_check_api.return_value = {"status": "unhealthy", "last_check": time.time(), "error": "Error"}
        
        # Check health
        result = await health_check.check_health()
        
        # Verify the result
        assert result["status"] == "unhealthy"
        assert result["agent_api"]["status"] == "unhealthy"
        assert result["agent_api"]["error"] == "Error"
        mock_check_api.assert_called_once()
        mock_check_agent.assert_called_once()
        mock_check_resources.assert_called_once()


@pytest.mark.asyncio
async def test_check_agent_api(health_check):
    """Test checking Agent API health."""
    # Mock the HTTP client
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "stable"}
    health_check.http_client.get.return_value = mock_response
    
    # Check Agent API health
    result = await health_check._check_agent_api()
    
    # Verify the result
    assert result["status"] == "healthy"
    assert "response_time" in result
    assert result["response"] == {"status": "stable"}
    health_check.http_client.get.assert_called_once_with(
        "http://localhost:3284/status",
        timeout=5.0
    )
    
    # Test with error response
    health_check.http_client.get.reset_mock()
    mock_response.status_code = 500
    
    # Check Agent API health
    result = await health_check._check_agent_api()
    
    # Verify the result
    assert result["status"] == "unhealthy"
    assert "error" in result
    health_check.http_client.get.assert_called_once()
    
    # Test with timeout
    health_check.http_client.get.reset_mock()
    health_check.http_client.get.side_effect = httpx.TimeoutException("Timeout")
    
    # Check Agent API health
    result = await health_check._check_agent_api()
    
    # Verify the result
    assert result["status"] == "unhealthy"
    assert result["error"] == "Request timed out"
    health_check.http_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_check_agent(health_check):
    """Test checking agent health."""
    # Mock the HTTP client
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "stable", "agentType": "goose"}
    health_check.http_client.get.return_value = mock_response
    
    # Check agent health
    result = await health_check._check_agent()
    
    # Verify the result
    assert result["status"] == "healthy"
    assert result["type"] == "goose"
    assert result["agent_status"] == "stable"
    health_check.http_client.get.assert_called_once_with(
        "http://localhost:3284/status",
        timeout=5.0
    )
    
    # Test with running status
    health_check.http_client.get.reset_mock()
    mock_response.json.return_value = {"status": "running", "agentType": "goose"}
    
    # Check agent health
    result = await health_check._check_agent()
    
    # Verify the result
    assert result["status"] == "healthy"
    assert result["type"] == "goose"
    assert result["agent_status"] == "running"
    health_check.http_client.get.assert_called_once()
    
    # Test with unknown status
    health_check.http_client.get.reset_mock()
    mock_response.json.return_value = {"status": "unknown", "agentType": "goose"}
    
    # Check agent health
    result = await health_check._check_agent()
    
    # Verify the result
    assert result["status"] == "unknown"
    assert result["type"] == "goose"
    assert result["agent_status"] == "unknown"
    assert "error" in result
    health_check.http_client.get.assert_called_once()
    
    # Test with error response
    health_check.http_client.get.reset_mock()
    mock_response.status_code = 500
    
    # Check agent health
    result = await health_check._check_agent()
    
    # Verify the result
    assert result["status"] == "unhealthy"
    assert "error" in result
    health_check.http_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_check_resources(health_check):
    """Test checking resource usage."""
    # Check resource usage
    result = await health_check._check_resources()
    
    # Verify the result
    assert result["status"] == "healthy"
    assert "last_check" in result
    assert "memory_usage" in result
    assert "cpu_usage" in result


def test_get_health_status(health_check):
    """Test getting health status."""
    # Set up the health status
    health_check._health_status = {
        "status": "healthy",
        "agent_api": {"status": "healthy"},
        "agent": {"status": "healthy"},
        "mcp_server": {"status": "healthy"},
        "resources": {"status": "healthy"}
    }
    
    # Get health status
    result = health_check.get_health_status()
    
    # Verify the result
    assert result == health_check._health_status
    assert result["status"] == "healthy"
    assert result["agent_api"]["status"] == "healthy"
    assert result["agent"]["status"] == "healthy"
    assert result["mcp_server"]["status"] == "healthy"
    assert result["resources"]["status"] == "healthy"
