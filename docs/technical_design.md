# Technical Design Document

This document provides a detailed technical design for the MCP Agent API server, including class diagrams, sequence diagrams, and implementation details.

## 1. Class Structure

### 1.1 Core Classes

```
┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│ FastMCP           │     │ AgentAPIContext   │     │ AgentManager      │
├───────────────────┤     ├───────────────────┤     ├───────────────────┤
│ - name            │     │ - config          │     │ - config          │
│ - description     │     │ - agent_manager   │     │ - agents          │
│ - lifespan        │     │ - api_client      │     │ - current_agent   │
├───────────────────┤     ├───────────────────┤     ├───────────────────┤
│ + run_stdio_async │     │ + get_agent_type  │     │ + detect_agents   │
│ + run_sse_async   │     │ + switch_agent    │     │ + start_agent     │
│ + add_tool        │     │ + health_check    │     │ + stop_agent      │
└───────────────────┘     └───────────────────┘     └───────────────────┘
        │                          │                         │
        │                          │                         │
        ▼                          ▼                         ▼
┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│ Tool              │     │ AgentAPIClient    │     │ Agent             │
├───────────────────┤     ├───────────────────┤     ├───────────────────┤
│ - name            │     │ - url             │     │ - type            │
│ - description     │     │ - session         │     │ - process         │
│ - parameters      │     ├───────────────────┤     │ - config          │
├───────────────────┤     │ + send_message    │     ├───────────────────┤
│ + __call__        │     │ + get_screen      │     │ + start           │
└───────────────────┘     │ + check_health    │     │ + stop            │
                          └───────────────────┘     └───────────────────┘
```

### 1.2 Data Models

```
┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│ Config            │     │ AgentType         │     │ MessageType       │
├───────────────────┤     ├───────────────────┤     ├───────────────────┤
│ - agent_api_url   │     │ GOOSE             │     │ TEXT              │
│ - auto_start_agent│     │ AIDER             │     │ IMAGE             │
│ - agent_type      │     │ CLAUDE            │     │ FILE              │
│ - server          │     │ CODEX             │     │ SYSTEM            │
│ - debug           │     │ CUSTOM            │     │ ERROR             │
└───────────────────┘     └───────────────────┘     └───────────────────┘
```

## 2. Sequence Diagrams

### 2.1 Server Startup

```
┌─────────┐     ┌─────────┐     ┌─────────────┐     ┌────────────┐
│ Main    │     │ FastMCP │     │ AgentAPI    │     │ Agent      │
│         │     │         │     │ Context     │     │ Manager    │
└────┬────┘     └────┬────┘     └──────┬──────┘     └─────┬──────┘
     │                │                 │                  │
     │ run()          │                 │                  │
     │───────────────>│                 │                  │
     │                │                 │                  │
     │                │ create_context  │                  │
     │                │────────────────>│                  │
     │                │                 │                  │
     │                │                 │ detect_agents    │
     │                │                 │─────────────────>│
     │                │                 │                  │
     │                │                 │<─────────────────│
     │                │                 │                  │
     │                │                 │ start_agent      │
     │                │                 │─────────────────>│
     │                │                 │                  │
     │                │                 │<─────────────────│
     │                │                 │                  │
     │                │<────────────────│                  │
     │                │                 │                  │
     │                │ run_transport   │                  │
     │                │────────────────>│                  │
     │                │                 │                  │
     │<───────────────│                 │                  │
     │                │                 │                  │
```

### 2.2 Tool Execution

```
┌─────────┐     ┌─────────┐     ┌─────────────┐     ┌────────────┐     ┌─────────┐
│ MCP     │     │ FastMCP │     │ Tool        │     │ AgentAPI   │     │ Agent   │
│ Client  │     │         │     │             │     │ Client     │     │ API     │
└────┬────┘     └────┬────┘     └──────┬──────┘     └─────┬──────┘     └────┬────┘
     │                │                 │                  │                 │
     │ call_tool      │                 │                  │                 │
     │───────────────>│                 │                  │                 │
     │                │                 │                  │                 │
     │                │ execute_tool    │                  │                 │
     │                │────────────────>│                  │                 │
     │                │                 │                  │                 │
     │                │                 │ send_message     │                 │
     │                │                 │─────────────────>│                 │
     │                │                 │                  │                 │
     │                │                 │                  │ send_message    │
     │                │                 │                  │────────────────>│
     │                │                 │                  │                 │
     │                │                 │                  │<────────────────│
     │                │                 │                  │                 │
     │                │                 │<─────────────────│                 │
     │                │                 │                  │                 │
     │                │<────────────────│                  │                 │
     │                │                 │                  │                 │
     │<───────────────│                 │                  │                 │
     │                │                 │                  │                 │
```

## 3. Implementation Details

### 3.1 MCP Server Implementation

The MCP server is implemented using the FastMCP framework from the MCP SDK. It provides the following tools:

- **send_message**: Send a message to the agent
- **get_screen_content**: Get the current screen content from the agent
- **check_health**: Check the health of the agent and the Agent API
- **list_available_agents**: List all available agents
- **get_agent_type**: Get the current active agent
- **switch_agent**: Switch to a different agent
- **start_agent**: Start a specific agent
- **stop_agent**: Stop a specific agent
- **restart_agent**: Restart a specific agent

### 3.2 Agent Manager Implementation

The Agent Manager is responsible for detecting and managing agents. It uses the following strategies:

1. **Agent Detection**:
   - Check for installed executables (e.g., `goose`, `aider`)
   - Check for installed Python packages (e.g., `aider-chat`)
   - Check for installed Node.js packages (e.g., `@anthropic-ai/claude-code`)

2. **Agent Lifecycle Management**:
   - Start agents using subprocess
   - Monitor agent processes
   - Restart agents if they crash
   - Stop agents gracefully

3. **Agent Configuration**:
   - Load agent-specific configuration
   - Set environment variables for agents
   - Configure agent command-line arguments

### 3.3 Agent API Client Implementation

The Agent API Client communicates with the Agent API using HTTP requests. It provides the following functionality:

1. **Message Handling**:
   - Send messages to agents
   - Receive messages from agents
   - Handle different message types (text, image, file, system, error)

2. **Screen Content**:
   - Get the current screen content from agents
   - Parse screen content into a structured format

3. **Health Monitoring**:
   - Check the health of agents
   - Check the health of the Agent API
   - Report health status to the MCP server

### 3.4 Context Management Implementation

The context management system uses the MCP SDK's lifespan management to ensure proper resource cleanup. It provides:

1. **Lifespan Management**:
   - Initialize resources when the server starts
   - Clean up resources when the server stops
   - Handle exceptions during resource initialization and cleanup

2. **Shared State**:
   - Share state between tools and resources
   - Provide access to the agent manager and API client
   - Store configuration and runtime state

3. **Configuration Management**:
   - Load configuration from file
   - Override configuration with command-line arguments
   - Save configuration changes

## 4. Error Handling

The MCP server uses standardized error handling to ensure consistent error responses:

1. **Exception Hierarchy**:
   - **MCPServerError**: Base exception class for all MCP server errors
   - **AgentAPIError**: Error from the Agent API
   - **AgentError**: Error from the agent
   - **ConfigurationError**: Error in the configuration
   - **ValidationError**: Error in the input validation

2. **Error Response Format**:
   - **error**: The main error message
   - **error_type**: The type of error
   - **status_code**: The HTTP status code
   - **detail**: Optional detailed error information
   - **context**: Optional dictionary with additional error context

3. **Error Handling Functions**:
   - **handle_exception**: Convert exceptions to standardized error responses
   - **create_error_response**: Create standardized error responses
