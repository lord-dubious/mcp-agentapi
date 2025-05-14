#!/usr/bin/env python3
"""
Constants for the MCP server for Agent API.

This module defines constants used throughout the MCP server,
ensuring consistent values across different components.
"""

import time

# Snapshot interval for monitoring and event emission
# This matches the original Agent API's value in agentapi/lib/httpapi/server.go
# "That's about 40 frames per second. It's slightly less because the action of taking a snapshot takes time too."
SNAPSHOT_INTERVAL = 0.025  # 25ms, same as in agentapi/lib/httpapi/server.go

# Event buffer size for the event emitter
# This matches the original Agent API's value in agentapi/lib/httpapi/events.go
EVENT_BUFFER_SIZE = 1024

# Default timeout values
DEFAULT_TIMEOUT = 30.0
DEFAULT_RECONNECT_DELAY = 5.0
MAX_RECONNECT_ATTEMPTS = 5
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_INITIAL_DELAY = 1.0
DEFAULT_RETRY_MAX_DELAY = 30.0
DEFAULT_RETRY_BACKOFF_FACTOR = 2.0
DEFAULT_RETRY_JITTER = 0.1

# User agent for HTTP requests
USER_AGENT = "mcp-agentapi/1.0"

# CORS headers to match the original Agent API
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Accept, Authorization, Content-Type, X-CSRF-Token",
    "Access-Control-Expose-Headers": "Link",
    "Access-Control-Max-Age": "300"
}
