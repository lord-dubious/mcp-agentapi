#!/usr/bin/env python3
"""
Event emitter for the MCP server for Agent API.

This module contains the event emitter class for streaming events from the Agent API
to MCP clients as notifications. It includes robust error handling, resource cleanup,
and automatic reconnection with exponential backoff.
"""

import asyncio
import logging
import time
from typing import Any, Optional

import httpx
from mcp.server.fastmcp import FastMCP

from .exceptions import ResourceError
from .constants import SNAPSHOT_INTERVAL, EVENT_BUFFER_SIZE

# Configure logging
logger = logging.getLogger("mcp-server-agentapi.event-emitter")


class EventEmitter:
    """
    Event emitter for sending notifications to clients.

    This class is responsible for streaming events from the Agent API
    and forwarding them to MCP clients as notifications. It includes
    robust error handling, resource cleanup, and automatic reconnection.

    Attributes:
        http_client: HTTP client for making requests
        agent_api_url: URL of the Agent API server
        last_event_id: Last processed event ID
        _stream_task: Background task for streaming events
        _active: Flag indicating if the emitter is active
        _lock: Lock for thread-safe access to resources
        _health_check_task: Task for periodic health checks
        _resource_manager: Optional resource manager for tracking resources
    """
    def __init__(self, http_client: httpx.AsyncClient, agent_api_url: str):
        """
        Initialize the event emitter.

        Args:
            http_client: HTTP client for making requests
            agent_api_url: URL of the Agent API server
        """
        self.http_client = http_client
        self.agent_api_url = agent_api_url.rstrip('/')
        self.last_event_id = 0
        self._stream_task: Optional[asyncio.Task] = None
        self._screen_stream_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._active = True
        self._lock = asyncio.Lock()
        self._resource_manager = None

        # Health metrics
        self._event_count = 0
        self._screen_update_count = 0
        self._error_count = 0
        self._last_event_time = 0
        self._last_screen_update_time = 0
        self._last_health_check = 0

        # Buffer size for events (matches original Agent API)
        self._event_buffer_size = EVENT_BUFFER_SIZE

    async def start_event_stream(self, server: FastMCP) -> None:
        """
        Start listening for events from the Agent API and forward them as MCP notifications.

        This method connects to the Agent API events endpoint and forwards events
        to MCP clients as notifications. It automatically reconnects if the connection
        is lost.

        Args:
            server: The MCP server instance
        """
        # Import here to avoid circular imports
        from .api_client import AgentAPIClient

        # Create an API client
        api_client = AgentAPIClient(self.http_client, self.agent_api_url)

        # Stream events to MCP clients with enhanced error handling
        try:
            await api_client.stream_events_to_mcp(server, self)
        except Exception as e:
            logger.error(f"Event stream failed with error: {e}")
            self._error_count += 1

            # If the emitter is still active, try to restart the stream
            if self._active:
                logger.info("Attempting to restart event stream...")
                await asyncio.sleep(1.0)  # Brief delay before restart
                if self._active:  # Check again after delay
                    self.start_background_stream(server)

    def start_background_stream(self, server: FastMCP) -> asyncio.Task:
        """
        Start the event stream in a background task.

        Args:
            server: The MCP server instance

        Returns:
            The background task
        """
        async def _acquire_lock_and_start():
            async with self._lock:
                if self._stream_task is not None:
                    logger.warning("Event stream task already running, cancelling previous task")
                    self._stream_task.cancel()
                    try:
                        await asyncio.wait_for(self._stream_task, timeout=5.0)
                    except (asyncio.TimeoutError, asyncio.CancelledError):
                        logger.warning("Previous event stream task did not cancel cleanly")

                if not self._active:
                    logger.warning("Event emitter is not active, not starting stream")
                    return None

                self._stream_task = asyncio.create_task(self.start_event_stream(server))
                self._stream_task.add_done_callback(self._on_stream_task_done)

                # Register with resource manager if available
                if self._resource_manager:
                    try:
                        await self._resource_manager.register_task("event_stream", self._stream_task)
                    except ResourceError as e:
                        logger.warning(f"Failed to register event stream task: {e}")

                # Start health check if not already running
                if self._health_check_task is None or self._health_check_task.done():
                    self._health_check_task = asyncio.create_task(self._run_health_checks(server))

                    # Register with resource manager if available
                    if self._resource_manager:
                        try:
                            await self._resource_manager.register_task("event_health_check", self._health_check_task)
                        except ResourceError as e:
                            logger.warning(f"Failed to register health check task: {e}")

                return self._stream_task

        # Create a task for the lock acquisition and stream start
        return asyncio.create_task(_acquire_lock_and_start())

    def _on_stream_task_done(self, task: asyncio.Task) -> None:
        """
        Callback for when the stream task is done.

        Args:
            task: The completed task
        """
        try:
            task.result()
        except asyncio.CancelledError:
            logger.info("Event stream task was cancelled")
        except Exception as e:
            logger.error(f"Event stream task failed with error: {e}")
            self._error_count += 1

            # If the emitter is still active, log the error but don't restart here
            # The health check will handle restarts if needed
            if self._active:
                logger.info("Event stream task will be restarted by health check if needed")

    async def _run_health_checks(self, server: FastMCP) -> None:
        """
        Run periodic health checks on the event stream.

        This method checks the health of the event stream and restarts it if needed.
        It runs in a background task and continues until the emitter is stopped.

        Args:
            server: The MCP server instance
        """
        # Use a multiple of SNAPSHOT_INTERVAL for health checks to align with the original Agent API's timing
        # The original Agent API checks health every 1200 snapshots (30 seconds at 25ms per snapshot)
        check_interval = SNAPSHOT_INTERVAL * 1200  # Check every 30 seconds (1200 * 25ms)
        max_event_age = SNAPSHOT_INTERVAL * 2400   # Maximum age of the last event before considering the stream unhealthy (60s)

        logger.info("Starting event stream health checks")

        while self._active:
            try:
                # Wait for the check interval
                await asyncio.sleep(check_interval)

                if not self._active:
                    logger.info("Event emitter is not active, stopping health checks")
                    break

                # Check if the stream tasks are still running
                stream_task_running = (
                    self._stream_task is not None and
                    not self._stream_task.done()
                )

                screen_stream_task_running = (
                    self._screen_stream_task is not None and
                    not self._screen_stream_task.done()
                )

                # Check if we've received events recently
                current_time = time.time()
                self._last_health_check = current_time
                event_age = current_time - self._last_event_time if self._last_event_time > 0 else float('inf')
                screen_update_age = current_time - self._last_screen_update_time if self._last_screen_update_time > 0 else float('inf')

                # Log health metrics
                logger.debug(
                    f"Stream health check: event_stream={stream_task_running}, "
                    f"screen_stream={screen_stream_task_running}, "
                    f"events={self._event_count}, screen_updates={self._screen_update_count}, "
                    f"errors={self._error_count}, "
                    f"last_event_age={event_age:.1f}s, last_screen_update_age={screen_update_age:.1f}s"
                )

                # Restart the event stream if it's not running or if we haven't received events recently
                if not stream_task_running or (self._last_event_time > 0 and event_age > max_event_age):
                    logger.warning(
                        f"Event stream appears unhealthy: running={stream_task_running}, "
                        f"last_event_age={event_age:.1f}s, restarting..."
                    )

                    # Cancel the current stream task if it exists
                    if self._stream_task is not None:
                        self._stream_task.cancel()
                        try:
                            await asyncio.wait_for(self._stream_task, timeout=5.0)
                        except (asyncio.TimeoutError, asyncio.CancelledError):
                            pass

                    # Start a new stream task
                    self.start_background_stream(server)

                # Restart the screen stream if it's not running (but only if we've received at least one screen update before)
                # We don't restart based on age because screen updates might be infrequent
                if self._last_screen_update_time > 0 and not screen_stream_task_running:
                    logger.warning(
                        f"Screen stream appears unhealthy: running={screen_stream_task_running}, "
                        f"last_screen_update_age={screen_update_age:.1f}s, restarting..."
                    )

                    # Cancel the current screen stream task if it exists
                    if self._screen_stream_task is not None:
                        self._screen_stream_task.cancel()
                        try:
                            await asyncio.wait_for(self._screen_stream_task, timeout=5.0)
                        except (asyncio.TimeoutError, asyncio.CancelledError):
                            pass

                    # Start a new screen stream task
                    self.start_background_screen_stream(server)

            except asyncio.CancelledError:
                logger.info("Health check task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in event stream health check: {e}")
                await asyncio.sleep(5.0)  # Short delay before retrying after error

    def set_resource_manager(self, resource_manager: Any) -> None:
        """
        Set the resource manager for tracking resources.

        Args:
            resource_manager: Resource manager instance
        """
        self._resource_manager = resource_manager

    def record_event_processed(self) -> None:
        """Record that an event was successfully processed."""
        self._event_count += 1
        self._last_event_time = time.time()

    def record_error(self) -> None:
        """Record that an error occurred."""
        self._error_count += 1

    async def start_screen_stream(self, server: FastMCP) -> None:
        """
        Start listening for screen updates from the Agent API and forward them as MCP notifications.

        This method connects to the Agent API internal screen endpoint and forwards screen updates
        to MCP clients as notifications. It automatically reconnects if the connection is lost.

        Args:
            server: The MCP server instance
        """
        # Import here to avoid circular imports
        from .api_client import AgentAPIClient

        # Create an API client
        api_client = AgentAPIClient(self.http_client, self.agent_api_url)

        # Stream screen updates to MCP clients with enhanced error handling
        try:
            await api_client.stream_screen_to_mcp(server, self)
        except Exception as e:
            # Check if it's a 404 error, which means the endpoint is not supported
            if hasattr(e, 'status_code') and getattr(e, 'status_code') == 404:
                logger.info("Screen endpoint not found (404). This endpoint might not be supported by the Agent API.")
                return

            logger.error(f"Screen stream failed with error: {e}")
            self._error_count += 1

            # If the emitter is still active, try to restart the stream
            if self._active:
                logger.info("Attempting to restart screen stream...")
                await asyncio.sleep(1.0)  # Brief delay before restart
                if self._active:  # Check again after delay
                    self.start_background_screen_stream(server)

    def start_background_screen_stream(self, server: FastMCP) -> asyncio.Task:
        """
        Start the screen stream in a background task.

        Args:
            server: The MCP server instance

        Returns:
            The background task
        """
        async def _acquire_lock_and_start():
            async with self._lock:
                if self._screen_stream_task is not None:
                    logger.warning("Screen stream task already running, cancelling previous task")
                    self._screen_stream_task.cancel()
                    try:
                        await asyncio.wait_for(self._screen_stream_task, timeout=5.0)
                    except (asyncio.TimeoutError, asyncio.CancelledError):
                        logger.warning("Previous screen stream task did not cancel cleanly")

                if not self._active:
                    logger.warning("Event emitter is not active, not starting screen stream")
                    return None

                self._screen_stream_task = asyncio.create_task(self.start_screen_stream(server))
                self._screen_stream_task.add_done_callback(self._on_screen_stream_task_done)

                # Register with resource manager if available
                if self._resource_manager:
                    try:
                        await self._resource_manager.register_task("screen_stream", self._screen_stream_task)
                    except ResourceError as e:
                        logger.warning(f"Failed to register screen stream task: {e}")

                return self._screen_stream_task

        # Create a task for the lock acquisition and stream start
        return asyncio.create_task(_acquire_lock_and_start())

    def _on_screen_stream_task_done(self, task: asyncio.Task) -> None:
        """
        Callback for when the screen stream task is done.

        Args:
            task: The completed task
        """
        try:
            task.result()
        except asyncio.CancelledError:
            logger.info("Screen stream task was cancelled")
        except Exception as e:
            # Check if it's a 404 error, which means the endpoint is not supported
            if hasattr(e, 'status_code') and getattr(e, 'status_code') == 404:
                logger.info("Screen endpoint not found (404). This endpoint might not be supported by the Agent API.")
                return

            logger.error(f"Screen stream task failed with error: {e}")
            self._error_count += 1

            # If the emitter is still active, log the error but don't restart here
            # The health check will handle restarts if needed
            if self._active:
                logger.info("Screen stream task will be restarted by health check if needed")

    def record_screen_update_processed(self) -> None:
        """Record that a screen update was successfully processed."""
        self._screen_update_count += 1
        self._last_screen_update_time = time.time()

    async def stop(self) -> None:
        """
        Stop the event stream.

        This method cancels the background tasks and cleans up resources.
        It uses a lock to ensure thread-safety during the stop operation.
        """
        async with self._lock:
            logger.info("Stopping event emitter")
            self._active = False

            # Cancel the health check task
            if self._health_check_task is not None:
                logger.info("Cancelling health check task")
                self._health_check_task.cancel()
                try:
                    await asyncio.wait_for(self._health_check_task, timeout=5.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    logger.warning("Health check task did not cancel cleanly")
                self._health_check_task = None

            # Cancel the stream task
            if self._stream_task is not None:
                logger.info("Cancelling event stream task")
                self._stream_task.cancel()
                try:
                    await asyncio.wait_for(self._stream_task, timeout=5.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    logger.warning("Event stream task did not cancel cleanly")
                self._stream_task = None

            # Cancel the screen stream task
            if self._screen_stream_task is not None:
                logger.info("Cancelling screen stream task")
                self._screen_stream_task.cancel()
                try:
                    await asyncio.wait_for(self._screen_stream_task, timeout=5.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    logger.warning("Screen stream task did not cancel cleanly")
                self._screen_stream_task = None

            # Unregister from resource manager if available
            if self._resource_manager:
                try:
                    if self._stream_task:
                        await self._resource_manager.unregister_task("event_stream")
                    if self._screen_stream_task:
                        await self._resource_manager.unregister_task("screen_stream")
                    if self._health_check_task:
                        await self._resource_manager.unregister_task("event_health_check")
                except ResourceError as e:
                    logger.warning(f"Error unregistering tasks from resource manager: {e}")

            logger.info("Event emitter stopped")
