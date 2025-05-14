#!/usr/bin/env python3
"""
Tests for the resource manager module.

This module contains tests for the resource management functionality,
including process, task, and custom resource tracking and cleanup.
"""

import asyncio
import subprocess
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from src.resource_manager import ResourceManager
from src.exceptions import ResourceError


@pytest.fixture
def resource_manager():
    """Create a test resource manager."""
    return ResourceManager()


@pytest.mark.asyncio
async def test_register_process(resource_manager):
    """Test registering a process."""
    # Create a mock process
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.pid = 12345

    # Register the process
    await resource_manager.register_process("test_process", mock_process)

    # Verify that the process was registered
    assert "test_process" in resource_manager._processes
    assert resource_manager._processes["test_process"] == mock_process

    # Test registering a process with the same key
    with pytest.raises(ResourceError):
        await resource_manager.register_process("test_process", mock_process)


@pytest.mark.asyncio
async def test_register_task(resource_manager):
    """Test registering a task."""
    # Create a mock task
    mock_task = MagicMock(spec=asyncio.Task)

    # Register the task
    await resource_manager.register_task("test_task", mock_task)

    # Verify that the task was registered
    assert "test_task" in resource_manager._tasks
    assert resource_manager._tasks["test_task"] == mock_task

    # Test registering a task with the same key
    with pytest.raises(ResourceError):
        await resource_manager.register_task("test_task", mock_task)


@pytest.mark.asyncio
async def test_register_custom_resource(resource_manager):
    """Test registering a custom resource."""
    # Create a mock resource and cleanup function
    mock_resource = MagicMock()
    mock_cleanup = MagicMock()

    # Register the custom resource
    await resource_manager.register_custom_resource("test_resource", mock_resource, mock_cleanup)

    # Verify that the custom resource was registered
    assert "test_resource" in resource_manager._custom_resources
    assert resource_manager._custom_resources["test_resource"] == (mock_resource, mock_cleanup)

    # Test registering a custom resource with the same key
    with pytest.raises(ResourceError):
        await resource_manager.register_custom_resource("test_resource", mock_resource, mock_cleanup)


@pytest.mark.asyncio
async def test_unregister_process(resource_manager):
    """Test unregistering a process."""
    # Create a mock process
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.pid = 12345

    # Register the process
    await resource_manager.register_process("test_process", mock_process)

    # Unregister the process
    result = await resource_manager.unregister_process("test_process")

    # Verify that the process was unregistered
    assert "test_process" not in resource_manager._processes
    assert result == mock_process

    # Test unregistering a process that doesn't exist
    with pytest.raises(ResourceError):
        await resource_manager.unregister_process("test_process")


@pytest.mark.asyncio
async def test_unregister_task(resource_manager):
    """Test unregistering a task."""
    # Create a mock task
    mock_task = MagicMock(spec=asyncio.Task)

    # Register the task
    await resource_manager.register_task("test_task", mock_task)

    # Unregister the task
    result = await resource_manager.unregister_task("test_task")

    # Verify that the task was unregistered
    assert "test_task" not in resource_manager._tasks
    assert result == mock_task

    # Test unregistering a task that doesn't exist
    with pytest.raises(ResourceError):
        await resource_manager.unregister_task("test_task")


@pytest.mark.asyncio
async def test_unregister_custom_resource(resource_manager):
    """Test unregistering a custom resource."""
    # Create a mock resource and cleanup function
    mock_resource = MagicMock()
    mock_cleanup = MagicMock()

    # Register the custom resource
    await resource_manager.register_custom_resource("test_resource", mock_resource, mock_cleanup)

    # Unregister the custom resource
    result = await resource_manager.unregister_custom_resource("test_resource")

    # Verify that the custom resource was unregistered
    assert "test_resource" not in resource_manager._custom_resources
    assert result == mock_resource

    # Test unregistering a custom resource that doesn't exist
    with pytest.raises(ResourceError):
        await resource_manager.unregister_custom_resource("test_resource")


@pytest.mark.asyncio
async def test_track_process(resource_manager):
    """Test tracking a process with a context manager."""
    # Create a mock process
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.pid = 12345

    # Mock the stop_process method
    with patch.object(resource_manager, "stop_process", new_callable=AsyncMock) as mock_stop_process:
        # Use the context manager
        async with resource_manager.track_process("test_process", mock_process) as process:
            # Verify that the process was registered
            assert "test_process" in resource_manager._processes
            assert resource_manager._processes["test_process"] == mock_process
            assert process == mock_process

        # Verify that the process was stopped
        mock_stop_process.assert_called_once_with("test_process")


@pytest.mark.asyncio
async def test_track_task(resource_manager):
    """Test tracking a task with a context manager."""
    # Create a mock task
    mock_task = MagicMock(spec=asyncio.Task)

    # Mock the cancel_task method
    with patch.object(resource_manager, "cancel_task", new_callable=AsyncMock) as mock_cancel_task:
        # Use the context manager
        async with resource_manager.track_task("test_task", mock_task) as task:
            # Verify that the task was registered
            assert "test_task" in resource_manager._tasks
            assert resource_manager._tasks["test_task"] == mock_task
            assert task == mock_task

        # Verify that the task was cancelled
        mock_cancel_task.assert_called_once_with("test_task")


@pytest.mark.asyncio
async def test_stop_process(resource_manager):
    """Test stopping a process."""
    # Create a mock process
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.pid = 12345
    mock_process.poll.return_value = None
    mock_process.wait.return_value = 0

    # Register the process
    await resource_manager.register_process("test_process", mock_process)

    # Stop the process
    await resource_manager.stop_process("test_process")

    # Verify that the process was terminated
    mock_process.terminate.assert_called_once()
    mock_process.wait.assert_called_once()
    assert "test_process" not in resource_manager._processes

    # Test stopping a process that doesn't exist
    with pytest.raises(ResourceError):
        await resource_manager.stop_process("test_process")


@pytest.mark.asyncio
async def test_cancel_task(resource_manager):
    """Test cancelling a task."""
    # Create a mock task
    mock_task = MagicMock(spec=asyncio.Task)
    mock_task.done.return_value = False

    # Register the task
    await resource_manager.register_task("test_task", mock_task)

    # Cancel the task
    await resource_manager.cancel_task("test_task")

    # Verify that the task was cancelled
    mock_task.cancel.assert_called_once()
    assert "test_task" not in resource_manager._tasks

    # Test cancelling a task that doesn't exist
    with pytest.raises(ResourceError):
        await resource_manager.cancel_task("test_task")


@pytest.mark.asyncio
async def test_cleanup_custom_resource(resource_manager):
    """Test cleaning up a custom resource."""
    # Create a mock resource and cleanup function
    mock_resource = MagicMock()
    mock_cleanup = MagicMock()

    # Register the custom resource
    await resource_manager.register_custom_resource("test_resource", mock_resource, mock_cleanup)

    # Clean up the custom resource
    await resource_manager.cleanup_custom_resource("test_resource")

    # Verify that the cleanup function was called
    mock_cleanup.assert_called_once_with(mock_resource)
    assert "test_resource" not in resource_manager._custom_resources

    # Test cleaning up a custom resource that doesn't exist
    with pytest.raises(ResourceError):
        await resource_manager.cleanup_custom_resource("test_resource")


@pytest.mark.asyncio
async def test_cleanup_all(resource_manager):
    """Test cleaning up all resources."""
    # Create mock resources
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.pid = 12345
    mock_task = MagicMock(spec=asyncio.Task)
    mock_resource = MagicMock()
    mock_cleanup = MagicMock()

    # Register the resources
    await resource_manager.register_process("test_process", mock_process)
    await resource_manager.register_task("test_task", mock_task)
    await resource_manager.register_custom_resource("test_resource", mock_resource, mock_cleanup)

    # Mock the cleanup methods
    with patch.object(resource_manager, "stop_process", new_callable=AsyncMock) as mock_stop_process, \
         patch.object(resource_manager, "cancel_task", new_callable=AsyncMock) as mock_cancel_task, \
         patch.object(resource_manager, "cleanup_custom_resource", new_callable=AsyncMock) as mock_cleanup_resource:
        # Clean up all resources
        await resource_manager.cleanup_all()

        # Verify that all cleanup methods were called
        mock_stop_process.assert_called_once_with("test_process")
        mock_cancel_task.assert_called_once_with("test_task")
        mock_cleanup_resource.assert_called_once_with("test_resource")


@pytest.mark.asyncio
async def test_get_resource_status(resource_manager):
    """Test getting resource status."""
    # Create mock resources
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.pid = 12345
    mock_process.poll.return_value = None
    mock_task = MagicMock(spec=asyncio.Task)
    mock_task.done.return_value = False
    mock_task.cancelled.return_value = False
    mock_resource = MagicMock()
    mock_cleanup = MagicMock()

    # Register the resources
    await resource_manager.register_process("test_process", mock_process)
    await resource_manager.register_task("test_task", mock_task)
    await resource_manager.register_custom_resource("test_resource", mock_resource, mock_cleanup)

    # Get resource status
    status = await resource_manager.get_resource_status()

    # Verify the status
    assert "processes" in status
    assert "test_process" in status["processes"]
    assert status["processes"]["test_process"]["pid"] == 12345
    assert status["processes"]["test_process"]["running"] is True

    assert "tasks" in status
    assert "test_task" in status["tasks"]
    assert status["tasks"]["test_task"]["done"] is False
    assert status["tasks"]["test_task"]["cancelled"] is False

    assert "custom_resources" in status
    assert "test_resource" in status["custom_resources"]
    assert status["custom_resources"]["test_resource"]["type"] == mock_resource.__class__.__name__
