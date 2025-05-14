# Health Check

The Health Check module is responsible for monitoring the health of the MCP server and its components, including the Agent API server, agent processes, and other resources.

## Overview

The Health Check module is implemented in the `src/health_check.py` file. It provides functionality for:

- Checking the health of the Agent API server
- Checking the health of the agent
- Checking resource usage
- Providing overall health status
- Running periodic health checks

## Usage

### Creating a Health Check

```python
import httpx
from src.health_check import HealthCheck
from src.config import Config

# Create a configuration
config = Config()

# Create an HTTP client
http_client = httpx.AsyncClient()

# Create a health check
health_check = HealthCheck(config, http_client)
```

### Starting and Stopping Health Checks

```python
# Start periodic health checks
await health_check.start()

# Stop periodic health checks
await health_check.stop()
```

### Checking Health

```python
# Check health once
health_status = await health_check.check_health()
print(f"Overall health: {health_status['status']}")
print(f"Agent API health: {health_status['agent_api']['status']}")
print(f"Agent health: {health_status['agent']['status']}")
print(f"MCP server health: {health_status['mcp_server']['status']}")
print(f"Resource health: {health_status['resources']['status']}")
```

### Getting Health Status

```python
# Get the current health status
health_status = health_check.get_health_status()
print(f"Overall health: {health_status['status']}")
```

## Health Status

The health status is a dictionary with the following structure:

```python
{
    "status": "healthy" | "unhealthy" | "degraded" | "unknown",
    "agent_api": {
        "status": "healthy" | "unhealthy" | "unknown",
        "last_check": 1234567890.123,
        "response_time": 0.123,
        "error": "Error message" (optional)
    },
    "agent": {
        "status": "healthy" | "unhealthy" | "unknown",
        "last_check": 1234567890.123,
        "type": "goose" | "aider" | "claude" | "codex" | "custom" | None,
        "agent_status": "stable" | "running" | "unknown" (optional),
        "error": "Error message" (optional)
    },
    "mcp_server": {
        "status": "healthy" | "unhealthy" | "unknown",
        "last_check": 1234567890.123,
        "uptime": 123.456,
        "start_time": 1234567890.123
    },
    "resources": {
        "status": "healthy" | "unhealthy" | "unknown",
        "last_check": 1234567890.123,
        "memory_usage": 123456789,
        "cpu_usage": 12.3,
        "error": "Error message" (optional)
    }
}
```

## Implementation Details

### Health Check Task

The Health Check module runs a background task that performs periodic health checks:

```python
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
```

### Checking Agent API Health

The Health Check module checks the health of the Agent API server:

```python
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
```

### Checking Agent Health

The Health Check module checks the health of the agent:

```python
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
```

### Checking Resource Usage

The Health Check module checks resource usage:

```python
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
```

### Overall Health Status

The Health Check module determines the overall health status based on the health of its components:

```python
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
```

## Error Handling

The Health Check module provides detailed error handling:

```python
try:
    agent_api_status = await self._check_agent_api()
    self._health_status["agent_api"] = agent_api_status
except Exception as e:
    logger.error(f"Error checking Agent API health: {e}")
    self._health_status["agent_api"]["status"] = "unhealthy"
    self._health_status["agent_api"]["last_check"] = start_time
    self._health_status["agent_api"]["error"] = str(e)
```
