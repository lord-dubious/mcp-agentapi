#!/usr/bin/env python3
"""
Resource manager for the MCP server for Agent API.

This module provides a resource manager for tracking and cleaning up resources
such as processes, tasks, and other resources that need proper cleanup.
"""

import asyncio
import logging
import subprocess
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from contextlib import asynccontextmanager

from .exceptions import ResourceError

# Configure logging
logger = logging.getLogger("mcp-server-agentapi.resource-manager")


class ResourceManager:
    """
    Resource manager for tracking and cleaning up resources.

    This class provides methods for tracking and cleaning up resources
    such as processes, tasks, and other resources that need proper cleanup.
    It ensures that resources are properly cleaned up when they are no longer needed.

    Attributes:
        _processes: Dictionary of tracked processes
        _tasks: Dictionary of tracked asyncio tasks
        _custom_resources: Dictionary of custom resources with cleanup functions
        _lock: Lock for thread-safe access to resources
    """

    def __init__(self):
        """Initialize the resource manager."""
        self._processes: Dict[str, subprocess.Popen] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._custom_resources: Dict[str, Tuple[Any, Callable]] = {}
        self._lock = asyncio.Lock()

    async def register_process(self, key: str, process: subprocess.Popen) -> None:
        """
        Register a process for tracking.

        Args:
            key: Unique identifier for the process
            process: Process to track

        Raises:
            ResourceError: If a process with the same key is already registered
        """
        async with self._lock:
            if key in self._processes:
                raise ResourceError(f"Process with key '{key}' already registered")
            self._processes[key] = process
            logger.debug(f"Registered process '{key}' with PID {process.pid}")

    async def register_task(self, key: str, task: asyncio.Task) -> None:
        """
        Register an asyncio task for tracking.

        Args:
            key: Unique identifier for the task
            task: Task to track

        Raises:
            ResourceError: If a task with the same key is already registered
        """
        async with self._lock:
            if key in self._tasks:
                raise ResourceError(f"Task with key '{key}' already registered")
            self._tasks[key] = task
            logger.debug(f"Registered task '{key}'")

    async def register_custom_resource(
        self, key: str, resource: Any, cleanup_func: Callable
    ) -> None:
        """
        Register a custom resource with a cleanup function.

        Args:
            key: Unique identifier for the resource
            resource: Resource to track
            cleanup_func: Function to call when cleaning up the resource

        Raises:
            ResourceError: If a resource with the same key is already registered
        """
        async with self._lock:
            if key in self._custom_resources:
                raise ResourceError(f"Custom resource with key '{key}' already registered")
            self._custom_resources[key] = (resource, cleanup_func)
            logger.debug(f"Registered custom resource '{key}'")

    async def unregister_process(self, key: str) -> Optional[subprocess.Popen]:
        """
        Unregister a process without stopping it.

        Args:
            key: Unique identifier for the process

        Returns:
            The unregistered process, or None if not found

        Raises:
            ResourceError: If the process is not registered
        """
        async with self._lock:
            if key not in self._processes:
                raise ResourceError(f"Process with key '{key}' not registered")
            process = self._processes.pop(key)
            logger.debug(f"Unregistered process '{key}'")
            return process

    async def unregister_task(self, key: str) -> Optional[asyncio.Task]:
        """
        Unregister a task without cancelling it.

        Args:
            key: Unique identifier for the task

        Returns:
            The unregistered task, or None if not found

        Raises:
            ResourceError: If the task is not registered
        """
        async with self._lock:
            if key not in self._tasks:
                raise ResourceError(f"Task with key '{key}' not registered")
            task = self._tasks.pop(key)
            logger.debug(f"Unregistered task '{key}'")
            return task

    async def unregister_custom_resource(self, key: str) -> Optional[Any]:
        """
        Unregister a custom resource without cleaning it up.

        Args:
            key: Unique identifier for the resource

        Returns:
            The unregistered resource, or None if not found

        Raises:
            ResourceError: If the resource is not registered
        """
        async with self._lock:
            if key not in self._custom_resources:
                raise ResourceError(f"Custom resource with key '{key}' not registered")
            resource, _ = self._custom_resources.pop(key)
            logger.debug(f"Unregistered custom resource '{key}'")
            return resource

    @asynccontextmanager
    async def track_process(self, key: str, process: subprocess.Popen):
        """
        Context manager for tracking a process.

        Args:
            key: Unique identifier for the process
            process: Process to track

        Yields:
            The process being tracked

        Raises:
            ResourceError: If a process with the same key is already registered
        """
        await self.register_process(key, process)
        try:
            yield process
        finally:
            try:
                await self.stop_process(key)
            except ResourceError:
                # Process might have already been unregistered
                pass

    @asynccontextmanager
    async def track_task(self, key: str, task: asyncio.Task):
        """
        Context manager for tracking a task.

        Args:
            key: Unique identifier for the task
            task: Task to track

        Yields:
            The task being tracked

        Raises:
            ResourceError: If a task with the same key is already registered
        """
        await self.register_task(key, task)
        try:
            yield task
        finally:
            try:
                await self.cancel_task(key)
            except ResourceError:
                # Task might have already been unregistered
                pass

    async def stop_process(self, key: str, timeout: float = 5.0) -> None:
        """
        Stop a process and unregister it.

        This method attempts to gracefully terminate the process first, then
        forcefully kills it if it doesn't terminate within the timeout.
        It also handles cleanup of process resources and ensures proper
        unregistration even if errors occur.

        Args:
            key: Unique identifier for the process
            timeout: Timeout in seconds for graceful termination

        Raises:
            ResourceError: If the process is not registered
        """
        process = None

        # First get the process under the lock
        async with self._lock:
            if key not in self._processes:
                raise ResourceError(f"Process with key '{key}' not registered")

            process = self._processes[key]
            logger.info(f"Stopping process '{key}' with PID {process.pid}")

        # Perform the actual termination outside the lock to avoid blocking
        # other operations while waiting for the process to terminate
        if process:
            try:
                # Check if process is still running
                if process.poll() is None:
                    # Try graceful termination first
                    try:
                        logger.debug(f"Attempting graceful termination of process '{key}'")
                        process.terminate()

                        # Wait for the process to terminate with a timeout
                        try:
                            exit_code = process.wait(timeout=timeout)
                            logger.info(f"Process '{key}' terminated gracefully with exit code {exit_code}")
                        except subprocess.TimeoutExpired:
                            # If graceful termination fails, force kill
                            logger.warning(f"Process '{key}' did not terminate gracefully after {timeout}s, forcing...")

                            # Try SIGINT first for a more graceful shutdown
                            if hasattr(subprocess, 'SIGINT'):
                                try:
                                    import signal
                                    process.send_signal(signal.SIGINT)
                                    # Give it a short time to respond to SIGINT
                                    exit_code = process.wait(timeout=2.0)
                                    logger.info(f"Process '{key}' terminated with SIGINT, exit code {exit_code}")
                                except subprocess.TimeoutExpired:
                                    # If SIGINT fails, use SIGKILL
                                    logger.warning(f"Process '{key}' did not respond to SIGINT, using SIGKILL")
                                    process.kill()

                                    # Wait again with a shorter timeout
                                    try:
                                        exit_code = process.wait(timeout=2.0)
                                        logger.info(f"Process '{key}' killed with exit code {exit_code}")
                                    except subprocess.TimeoutExpired:
                                        logger.error(f"Failed to kill process '{key}', it may be zombie or blocked")
                                except Exception as e:
                                    logger.error(f"Error sending SIGINT to process '{key}': {e}")
                                    # Fall back to kill
                                    process.kill()
                            else:
                                # If SIGINT is not available, use kill directly
                                process.kill()

                                # Wait again with a shorter timeout
                                try:
                                    exit_code = process.wait(timeout=2.0)
                                    logger.info(f"Process '{key}' killed with exit code {exit_code}")
                                except subprocess.TimeoutExpired:
                                    logger.error(f"Failed to kill process '{key}', it may be zombie or blocked")
                    except Exception as e:
                        logger.error(f"Error terminating process '{key}': {e}")
                        # Try to force kill as a last resort
                        try:
                            process.kill()
                        except Exception as kill_error:
                            logger.error(f"Error force killing process '{key}': {kill_error}")
                else:
                    logger.info(f"Process '{key}' already terminated with exit code {process.returncode}")

                # Clean up process resources
                try:
                    # Close any open file descriptors
                    if process.stdout:
                        process.stdout.close()
                    if process.stderr:
                        process.stderr.close()
                    if process.stdin:
                        process.stdin.close()
                except Exception as e:
                    logger.warning(f"Error closing process streams for '{key}': {e}")
            except Exception as e:
                logger.error(f"Unexpected error stopping process '{key}': {e}")

            # Finally, remove the process from tracking under the lock
            async with self._lock:
                if key in self._processes:
                    del self._processes[key]
                    logger.debug(f"Process '{key}' unregistered from resource manager")

    async def cancel_task(self, key: str, timeout: float = 5.0) -> None:
        """
        Cancel a task and unregister it.

        Args:
            key: Unique identifier for the task
            timeout: Timeout in seconds for task cancellation

        Raises:
            ResourceError: If the task is not registered
        """
        async with self._lock:
            if key not in self._tasks:
                raise ResourceError(f"Task with key '{key}' not registered")

            task = self._tasks[key]
            logger.info(f"Cancelling task '{key}'")

            # Cancel the task if it's not done
            if not task.done():
                task.cancel()

                # Wait for the task to be cancelled with a timeout
                try:
                    await asyncio.wait_for(asyncio.gather(task, return_exceptions=True), timeout=timeout)
                    logger.info(f"Task '{key}' cancelled")
                except asyncio.TimeoutError:
                    logger.error(f"Failed to cancel task '{key}' within {timeout}s")
            else:
                logger.info(f"Task '{key}' already completed")

            # Remove the task from tracking
            del self._tasks[key]

    async def cleanup_custom_resource(self, key: str) -> None:
        """
        Clean up a custom resource and unregister it.

        Args:
            key: Unique identifier for the resource

        Raises:
            ResourceError: If the resource is not registered
        """
        async with self._lock:
            if key not in self._custom_resources:
                raise ResourceError(f"Custom resource with key '{key}' not registered")

            resource, cleanup_func = self._custom_resources[key]
            logger.info(f"Cleaning up custom resource '{key}'")

            # Call the cleanup function
            try:
                if asyncio.iscoroutinefunction(cleanup_func):
                    await cleanup_func(resource)
                else:
                    cleanup_func(resource)
                logger.info(f"Custom resource '{key}' cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up custom resource '{key}': {e}")

            # Remove the resource from tracking
            del self._custom_resources[key]

    async def cleanup_all(self) -> None:
        """
        Clean up all tracked resources.

        This method stops all processes, cancels all tasks, and cleans up all custom resources.
        It logs any errors that occur during cleanup but continues with the remaining resources.
        """
        logger.info("Cleaning up all resources")

        # Get a snapshot of all resources to avoid modification during iteration
        async with self._lock:
            process_keys = list(self._processes.keys())
            task_keys = list(self._tasks.keys())
            custom_resource_keys = list(self._custom_resources.keys())

        # Clean up processes
        for key in process_keys:
            try:
                await self.stop_process(key)
            except Exception as e:
                logger.error(f"Error stopping process '{key}': {e}")

        # Clean up tasks
        for key in task_keys:
            try:
                await self.cancel_task(key)
            except Exception as e:
                logger.error(f"Error cancelling task '{key}': {e}")

        # Clean up custom resources
        for key in custom_resource_keys:
            try:
                await self.cleanup_custom_resource(key)
            except Exception as e:
                logger.error(f"Error cleaning up custom resource '{key}': {e}")

        logger.info("All resources cleaned up")

    async def get_resource_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the status of all tracked resources.

        Returns:
            Dictionary with the status of all tracked resources
        """
        async with self._lock:
            status = {
                "processes": {},
                "tasks": {},
                "custom_resources": {}
            }

            # Get process status
            for key, process in self._processes.items():
                status["processes"][key] = {
                    "pid": process.pid,
                    "running": process.poll() is None,
                    "returncode": process.returncode
                }

            # Get task status
            for key, task in self._tasks.items():
                status["tasks"][key] = {
                    "done": task.done(),
                    "cancelled": task.cancelled() if task.done() else False,
                    "exception": str(task.exception()) if task.done() and not task.cancelled() and task.exception() else None
                }

            # Get custom resource status
            for key, (resource, _) in self._custom_resources.items():
                status["custom_resources"][key] = {
                    "type": type(resource).__name__
                }

            return status
