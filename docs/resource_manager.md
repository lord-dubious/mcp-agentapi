# Resource Manager

The Resource Manager is responsible for tracking and cleaning up resources such as processes, tasks, and other resources that need proper cleanup.

## Overview

The Resource Manager is implemented in the `src/resource_manager.py` module. It provides functionality for:

- Tracking processes, tasks, and custom resources
- Cleaning up resources when they are no longer needed
- Providing context managers for resource tracking
- Getting resource status information

## Usage

### Creating a Resource Manager

```python
from src.resource_manager import ResourceManager

# Create a resource manager
resource_manager = ResourceManager()
```

### Tracking Processes

```python
import subprocess

# Start a process
process = subprocess.Popen(["ls", "-la"])

# Register the process for tracking
await resource_manager.register_process("ls_process", process)

# Later, stop the process
await resource_manager.stop_process("ls_process")
```

### Using Context Managers

```python
# Start a process and track it with a context manager
async with resource_manager.track_process("ls_process", subprocess.Popen(["ls", "-la"])) as process:
    # Process is automatically stopped when the context exits
    print(f"Process PID: {process.pid}")
```

### Tracking Tasks

```python
import asyncio

# Create a task
task = asyncio.create_task(some_coroutine())

# Register the task for tracking
await resource_manager.register_task("some_task", task)

# Later, cancel the task
await resource_manager.cancel_task("some_task")
```

### Using Task Context Managers

```python
# Create a task and track it with a context manager
async with resource_manager.track_task("some_task", asyncio.create_task(some_coroutine())) as task:
    # Task is automatically cancelled when the context exits
    print(f"Task: {task}")
```

### Tracking Custom Resources

```python
# Create a custom resource
resource = SomeResource()

# Define a cleanup function
def cleanup_resource(resource):
    resource.close()

# Register the custom resource for tracking
await resource_manager.register_custom_resource("some_resource", resource, cleanup_resource)

# Later, clean up the resource
await resource_manager.cleanup_custom_resource("some_resource")
```

### Cleaning Up All Resources

```python
# Clean up all tracked resources
await resource_manager.cleanup_all()
```

### Getting Resource Status

```python
# Get the status of all tracked resources
status = await resource_manager.get_resource_status()
print(f"Processes: {status['processes']}")
print(f"Tasks: {status['tasks']}")
print(f"Custom resources: {status['custom_resources']}")
```

## Resource Types

### Processes

The Resource Manager tracks subprocess.Popen instances:

```python
# Register a process
await resource_manager.register_process("process_key", process)

# Unregister a process without stopping it
process = await resource_manager.unregister_process("process_key")

# Stop a process and unregister it
await resource_manager.stop_process("process_key")
```

### Tasks

The Resource Manager tracks asyncio.Task instances:

```python
# Register a task
await resource_manager.register_task("task_key", task)

# Unregister a task without cancelling it
task = await resource_manager.unregister_task("task_key")

# Cancel a task and unregister it
await resource_manager.cancel_task("task_key")
```

### Custom Resources

The Resource Manager can track any custom resource with a cleanup function:

```python
# Register a custom resource
await resource_manager.register_custom_resource("resource_key", resource, cleanup_func)

# Unregister a custom resource without cleaning it up
resource = await resource_manager.unregister_custom_resource("resource_key")

# Clean up a custom resource and unregister it
await resource_manager.cleanup_custom_resource("resource_key")
```

## Implementation Details

### Process Management

The Resource Manager provides robust process management with graceful termination:

```python
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
    # Implementation details...
```

### Task Management

The Resource Manager provides task management with cancellation and timeout:

```python
async def cancel_task(self, key: str, timeout: float = 5.0) -> None:
    """
    Cancel a task and unregister it.

    Args:
        key: Unique identifier for the task
        timeout: Timeout in seconds for task cancellation

    Raises:
        ResourceError: If the task is not registered
    """
    # Implementation details...
```

### Custom Resource Management

The Resource Manager provides custom resource management with cleanup:

```python
async def cleanup_custom_resource(self, key: str) -> None:
    """
    Clean up a custom resource and unregister it.

    Args:
        key: Unique identifier for the resource

    Raises:
        ResourceError: If the resource is not registered
    """
    # Implementation details...
```

### Context Managers

The Resource Manager provides context managers for resource tracking:

```python
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
    # Implementation details...

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
    # Implementation details...
```

## Error Handling

The Resource Manager provides detailed error handling with custom exceptions:

```python
class ResourceError(Exception):
    """Error with a resource."""
    pass
```

## Thread Safety

The Resource Manager uses asyncio.Lock to ensure thread safety:

```python
def __init__(self):
    """Initialize the resource manager."""
    self._processes: Dict[str, subprocess.Popen] = {}
    self._tasks: Dict[str, asyncio.Task] = {}
    self._custom_resources: Dict[str, Tuple[Any, Callable]] = {}
    self._lock = asyncio.Lock()
```

All methods that modify the resource dictionaries use the lock to ensure thread safety:

```python
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
```
