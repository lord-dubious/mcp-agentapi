# Agent API Client

The Agent API client is a robust client for interacting with the Agent API. It provides methods for making requests, handling errors, and processing responses.

## Overview

The Agent API client is implemented in the `src/api_client.py` module. It provides a high-level interface for interacting with the Agent API, including:

- Making HTTP requests with proper error handling and retry logic
- Getting agent status and type
- Getting and sending messages
- Streaming events
- Getting screen content
- Getting the OpenAPI schema

## Usage

### Creating a Client

```python
import httpx
from src.api_client import AgentAPIClient

# Create an HTTP client
http_client = httpx.AsyncClient()

# Create an Agent API client
agent_api_url = "http://localhost:3284"
client = AgentAPIClient(http_client, agent_api_url)
```

### Making Requests

```python
# Make a GET request
status = await client.make_request("status")
print(f"Agent status: {status}")

# Make a POST request
result = await client.make_request("message", method="POST", json_data={
    "content": "Hello, agent!",
    "type": "user"
})
print(f"Message sent: {result}")
```

### Getting Agent Status

```python
# Get the raw status
status_data = await client.get_status()
print(f"Status data: {status_data}")

# Get the status as an enum
status = await client.get_agent_status()
print(f"Agent status: {status}")
```

### Getting Agent Type

```python
# Get the agent type
agent_type = await client.get_agent_type()
print(f"Agent type: {agent_type}")
```

### Getting Messages

```python
# Get all messages
messages_data = await client.get_messages()
print(f"Messages: {messages_data}")

# Get messages as a list of Message objects
messages = await client.get_message_list()
for message in messages:
    print(f"{message.role}: {message.content}")
```

### Sending Messages

```python
# Send a user message
result = await client.send_message("Hello, agent!", "user")
print(f"Message sent: {result}")

# Send a raw message
result = await client.send_message("!help", "raw")
print(f"Raw message sent: {result}")
```

### Getting Screen Content

```python
# Get the current screen content
screen = await client.get_screen()
print(f"Screen content: {screen}")
```

### Streaming Events

```python
# Define a callback function
async def handle_event(event):
    print(f"Received event: {event}")

# Stream events with a callback
async for event in client.stream_events(callback=handle_event):
    # Process events as they arrive
    print(f"Processing event: {event}")
```

### Getting the OpenAPI Schema

```python
# Get the OpenAPI schema
schema = await client.get_openapi_schema()
print(f"OpenAPI schema: {schema}")
```

## Error Handling

The Agent API client provides robust error handling with detailed error messages and context information. It handles various types of errors, including:

- HTTP errors (4xx, 5xx)
- Timeout errors
- Connection errors
- JSON parsing errors
- Unexpected errors

```python
from src.exceptions import AgentAPIError, TimeoutError

try:
    result = await client.make_request("status")
    print(f"Result: {result}")
except AgentAPIError as e:
    print(f"API error: {e}")
    print(f"Status code: {e.status_code}")
    print(f"Response text: {e.response_text}")
    print(f"Context: {e.context}")
except TimeoutError as e:
    print(f"Timeout error: {e}")
    print(f"Operation: {e.operation}")
    print(f"Timeout: {e.timeout}")
    print(f"Context: {e.context}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Retry Logic

The Agent API client implements exponential backoff with jitter for retrying failed requests. It will retry for network errors and specific HTTP status codes (429, 500, 502, 503, 504).

```python
# Make a request with custom retry parameters
result = await client.make_request(
    "status",
    retry_attempts=5,
    retry_for_statuses=[429, 500, 502, 503, 504],
    retry_initial_delay=0.1,
    retry_max_delay=10.0,
    retry_backoff_factor=2.0,
    retry_jitter=0.1
)
```

## Advanced Features

### Custom Headers

```python
# Make a request with custom headers
result = await client.make_request(
    "status",
    headers={
        "X-Custom-Header": "value"
    }
)
```

### Query Parameters

```python
# Make a request with query parameters
result = await client.make_request(
    "status",
    params={
        "param1": "value1",
        "param2": "value2"
    }
)
```

### Timeout Configuration

```python
# Make a request with a custom timeout
result = await client.make_request(
    "status",
    timeout=60.0
)
```

### Event Stream Reconnection

```python
# Stream events with reconnection
async for event in client.stream_events(
    reconnect=True,
    max_reconnect_attempts=10,
    reconnect_initial_delay=1.0,
    reconnect_max_delay=60.0,
    reconnect_backoff_factor=2.0,
    reconnect_jitter=0.1
):
    print(f"Event: {event}")
```

## Implementation Details

### Request Method

The `make_request` method is the core of the Agent API client. It handles making HTTP requests with proper error handling and retry logic.

```python
async def make_request(
    self,
    endpoint: str,
    method: str = "GET",
    json_data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, str]] = None,
    timeout: float = DEFAULT_TIMEOUT,
    retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
    retry_for_statuses: Optional[List[int]] = None,
    retry_initial_delay: float = DEFAULT_RETRY_INITIAL_DELAY,
    retry_max_delay: float = DEFAULT_RETRY_MAX_DELAY,
    retry_backoff_factor: float = DEFAULT_RETRY_BACKOFF_FACTOR,
    retry_jitter: float = DEFAULT_RETRY_JITTER
) -> Dict[str, Any]:
    # Implementation details...
```

### Event Streaming

The `stream_events` method implements the Server-Sent Events (SSE) protocol for streaming events from the Agent API.

```python
async def stream_events(
    self,
    callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
    reconnect: bool = True,
    max_reconnect_attempts: int = MAX_RECONNECT_ATTEMPTS,
    reconnect_initial_delay: float = DEFAULT_RECONNECT_DELAY,
    reconnect_max_delay: float = DEFAULT_RETRY_MAX_DELAY,
    reconnect_backoff_factor: float = DEFAULT_RETRY_BACKOFF_FACTOR,
    reconnect_jitter: float = DEFAULT_RETRY_JITTER,
    last_event_id: Optional[str] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    # Implementation details...
```
