#!/bin/bash
# MCP Inspector wrapper script for agent controller tools
# This script makes it easier to use the MCP Inspector with our agent controller tools

# Default values
DIRECTORY=$(dirname "$(readlink -f "$0")")
TOOL=""
AGENT_TYPE=""
CONTENT=""
MESSAGE_TYPE="user"
ENV_VARS=()

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --tool)
      TOOL="$2"
      shift 2
      ;;
    --agent_type)
      AGENT_TYPE="$2"
      shift 2
      ;;
    --content)
      CONTENT="$2"
      shift 2
      ;;
    --type)
      MESSAGE_TYPE="$2"
      shift 2
      ;;
    --env)
      ENV_VARS+=("--env" "$2")
      shift 2
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --tool TOOL              Tool to run (required)"
      echo "  --agent_type AGENT_TYPE  Agent type for agent-specific tools"
      echo "  --content CONTENT        Message content for send_message tool"
      echo "  --type TYPE              Message type for send_message tool (default: user)"
      echo "  --env KEY=VALUE          Environment variable to set (can be used multiple times)"
      echo "  --help                   Show this help message"
      echo ""
      echo "Available tools:"
      echo "  get_agent_type           Get the type of the agent"
      echo "  list_available_agents    List all available agents"
      echo "  install_agent            Install a specific agent (requires --agent_type)"
      echo "  start_agent              Start a specific agent (requires --agent_type)"
      echo "  stop_agent               Stop a specific agent (requires --agent_type)"
      echo "  restart_agent            Restart a specific agent (requires --agent_type)"
      echo "  get_status               Get the current status of the agent"
      echo "  check_health             Check the health of the MCP server"
      echo "  get_messages             Get all messages in the conversation"
      echo "  send_message             Send a message to the agent (requires --content)"
      echo "  get_screen               Get the current screen content"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Check if tool is provided
if [ -z "$TOOL" ]; then
  echo "Error: --tool is required"
  echo "Use --help for usage information"
  exit 1
fi

# Build the command
CMD="npx @modelcontextprotocol/inspector uv --directory $DIRECTORY ${ENV_VARS[@]} run agent_controller_tools.py $TOOL"

# Add tool-specific arguments
case "$TOOL" in
  install_agent|start_agent|stop_agent|restart_agent)
    if [ -z "$AGENT_TYPE" ]; then
      echo "Error: --agent_type is required for $TOOL tool"
      exit 1
    fi
    CMD="$CMD --agent_type $AGENT_TYPE"
    ;;
  send_message)
    if [ -z "$CONTENT" ]; then
      echo "Error: --content is required for send_message tool"
      exit 1
    fi
    CMD="$CMD --content \"$CONTENT\" --type $MESSAGE_TYPE"
    ;;
esac

# Execute the command
echo "Executing: $CMD"
eval "$CMD"
