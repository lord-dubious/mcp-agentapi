#!/usr/bin/env python3
"""
Health check module for the MCP server for Agent API.

This module provides health check functionality for monitoring the health of
the MCP server and its components, including the Agent API server, agent processes,
and other resources.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .exceptions import HealthCheckError
from .models import AgentType
from .config import Config
from .constants import SNAPSHOT_INTERVAL

# Configure logging
logger = logging.getLogger("mcp-server-agentapi.health-check")


class HealthCheck:
    """
    Health check for the MCP server.

    This class provides methods for checking the health of the MCP server
    and its components, including the Agent API server, agent processes,
    and other resources.

    Attributes:
        config: Configuration object
        http_client: HTTP client for making requests
        agent_api_url: URL of the Agent API server
        _health_check_task: Background task for periodic health checks
        _last_check_time: Time of the last health check
        _health_status: Current health status
    """

    def __init__(self, config: Config, http_client: httpx.AsyncClient):
        """
        Initialize the health check.

        Args:
            config: Configuration object
            http_client: HTTP client for making requests
        """
        self.config = config
        self.http_client = http_client
        self.agent_api_url = config.agent_api_url
        self._health_check_task: Optional[asyncio.Task] = None
        self._last_check_time = 0
        self._health_status: Dict[str, Any] = {
            "status": "unknown",
            "agent_api": {
                "status": "unknown",
                "last_check": 0,
                "response_time": 0,
            },
            "agent": {
                "type": None,
                "status": "unknown",
                "last_check": 0,
            },
            "mcp_server": {
                "status": "unknown",
                "last_check": 0,
                "uptime": 0,
                "start_time": time.time(),
            },
            "resources": {
                "status": "unknown",
                "last_check": 0,
                "memory_usage": 0,
                "cpu_usage": 0,
            },
        }
        # Use a multiple of SNAPSHOT_INTERVAL for health checks to align with the original Agent API's timing
        # The original Agent API checks health every 1200 snapshots (30 seconds at 25ms per snapshot)
        self._check_interval = SNAPSHOT_INTERVAL * 1200  # 30 seconds (1200 * 25ms)
        self._is_running = False
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """
        Start periodic health checks.

        This method starts a background task that performs periodic health checks
        on the MCP server and its components.
        """
        async with self._lock:
            if self._is_running:
                logger.warning("Health check is already running")
                return

            self._is_running = True
            self._health_check_task = asyncio.create_task(self._run_health_checks())
            logger.info("Health check started")

    async def stop(self) -> None:
        """
        Stop periodic health checks.

        This method stops the background task that performs periodic health checks.
        """
        async with self._lock:
            if not self._is_running:
                logger.warning("Health check is not running")
                return

            self._is_running = False
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
                self._health_check_task = None
            logger.info("Health check stopped")

    async def _run_health_checks(self) -> None:
        """
        Run periodic health checks.

        This method runs health checks on the MCP server and its components
        at regular intervals.
        """
        while self._is_running:
            try:
                await self.check_health()
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                logger.info("Health check task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in health check: {e}")
                await asyncio.sleep(5)  # Short delay before retrying after error

    async def check_health(self) -> Dict[str, Any]:
        """
        Check the health of the MCP server and its components.

        This method checks the health of the Agent API server, agent processes,
        and other resources, and updates the health status.

        Returns:
            Dictionary with health status information
        """
        start_time = time.time()
        self._last_check_time = start_time

        # Update MCP server status
        self._health_status["mcp_server"]["last_check"] = start_time
        self._health_status["mcp_server"]["uptime"] = start_time - self._health_status["mcp_server"]["start_time"]
        self._health_status["mcp_server"]["status"] = "healthy"

        # Check Agent API status
        try:
            agent_api_status = await self._check_agent_api()
            self._health_status["agent_api"] = agent_api_status
        except Exception as e:
            logger.error(f"Error checking Agent API health: {e}")
            self._health_status["agent_api"]["status"] = "unhealthy"
            self._health_status["agent_api"]["last_check"] = start_time
            self._health_status["agent_api"]["error"] = str(e)

        # Check agent status
        try:
            agent_status = await self._check_agent()
            self._health_status["agent"] = agent_status
        except Exception as e:
            logger.error(f"Error checking agent health: {e}")
            self._health_status["agent"]["status"] = "unhealthy"
            self._health_status["agent"]["last_check"] = start_time
            self._health_status["agent"]["error"] = str(e)

        # Check resource usage
        try:
            resource_status = await self._check_resources()
            self._health_status["resources"] = resource_status
        except Exception as e:
            logger.error(f"Error checking resource usage: {e}")
            self._health_status["resources"]["status"] = "unknown"
            self._health_status["resources"]["last_check"] = start_time
            self._health_status["resources"]["error"] = str(e)

        # Update overall status
        if (self._health_status["agent_api"]["status"] == "healthy" and
                self._health_status["agent"]["status"] == "healthy" and
                self._health_status["mcp_server"]["status"] == "healthy"):
            self._health_status["status"] = "healthy"
        elif (self._health_status["agent_api"]["status"] == "unhealthy" or
                self._health_status["agent"]["status"] == "unhealthy"):
            self._health_status["status"] = "unhealthy"
        else:
            self._health_status["status"] = "degraded"

        # Log health status
        logger.debug(f"Health check completed: {self._health_status['status']}")
        return self._health_status

    async def _check_agent_api(self) -> Dict[str, Any]:
        """
        Check the health of the Agent API server.

        This method checks if the Agent API server is running and responding
        to requests.

        Returns:
            Dictionary with Agent API health status information
        """
        start_time = time.time()
        status = {
            "status": "unknown",
            "last_check": start_time,
            "response_time": 0,
        }

        try:
            # Make a request to the Agent API status endpoint
            url = f"{self.agent_api_url.rstrip('/')}/status"
            response = await self.http_client.get(url, timeout=5.0)
            end_time = time.time()
            status["response_time"] = end_time - start_time

            if response.status_code == 200:
                status["status"] = "healthy"
                status["response"] = response.json()
            else:
                status["status"] = "unhealthy"
                status["error"] = f"Unexpected status code: {response.status_code}"
        except httpx.TimeoutException:
            status["status"] = "unhealthy"
            status["error"] = "Request timed out"
        except Exception as e:
            status["status"] = "unhealthy"
            status["error"] = str(e)

        return status

    async def _check_agent(self) -> Dict[str, Any]:
        """
        Check the health of the agent.

        This method checks if the agent is running and responding to requests.

        Returns:
            Dictionary with agent health status information
        """
        start_time = time.time()
        status = {
            "status": "unknown",
            "last_check": start_time,
            "type": None,
        }

        try:
            # Make a request to the Agent API status endpoint
            url = f"{self.agent_api_url.rstrip('/')}/status"
            response = await self.http_client.get(url, timeout=5.0)

            if response.status_code == 200:
                data = response.json()
                agent_type = data.get("agentType", "unknown")
                agent_status = data.get("status", "unknown")

                status["type"] = agent_type
                status["agent_status"] = agent_status

                # Agent API returns "running" or "stable" as status values
                if agent_status == "stable":
                    status["status"] = "healthy"
                elif agent_status == "running":
                    status["status"] = "healthy"  # Agent is running and processing a request
                else:
                    status["status"] = "unknown"
                    status["error"] = f"Unknown agent status: {agent_status}"
            else:
                status["status"] = "unhealthy"
                status["error"] = f"Unexpected status code: {response.status_code}"
        except Exception as e:
            status["status"] = "unhealthy"
            status["error"] = str(e)

        return status

    async def _check_resources(self) -> Dict[str, Any]:
        """
        Check resource usage.

        This method checks the resource usage of the MCP server and its components.

        Returns:
            Dictionary with resource usage information
        """
        # In a real implementation, we would check CPU, memory, disk usage, etc.
        # For now, we'll just return a placeholder
        return {
            "status": "healthy",
            "last_check": time.time(),
            "memory_usage": 0,
            "cpu_usage": 0,
        }

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get the current health status.

        Returns:
            Dictionary with health status information
        """
        return self._health_status
