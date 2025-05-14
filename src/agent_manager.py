#!/usr/bin/env python3
"""
Agent Manager for the MCP server for Agent API.

This module is responsible for detecting, installing, and managing the Agent API
and various agent types. It provides functionality for agent discovery, installation,
and lifecycle management.
"""

import asyncio
import httpx
import logging
import os
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, AsyncIterator
from contextlib import asynccontextmanager

from .config import Config
from .models import AgentType
from .constants import SNAPSHOT_INTERVAL
from .exceptions import (
    AgentDetectionError,
    AgentSwitchError,
    AgentStartError,
    AgentStopError,
    TimeoutError
)

# Configure logging
logger = logging.getLogger("mcp-server-agentapi.agent-manager")


class AgentInstallStatus(str, Enum):
    """Status of agent installation."""
    NOT_INSTALLED = "not_installed"
    INSTALLED = "installed"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class AgentRunningStatus(str, Enum):
    """Status of agent process."""
    RUNNING = "running"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


@dataclass
class AgentInfo:
    """
    Information about an agent.

    Attributes:
        agent_type: Type of the agent
        install_status: Installation status of the agent
        running_status: Running status of the agent
        version: Version of the agent (if available)
        install_path: Path where the agent is installed
        binary_path: Path to the agent binary
        api_key_required: Whether the agent requires an API key
        api_key_set: Whether the API key is set
        process: Process handle if the agent is running
    """
    agent_type: AgentType
    install_status: AgentInstallStatus = AgentInstallStatus.UNKNOWN
    running_status: AgentRunningStatus = AgentRunningStatus.UNKNOWN
    version: Optional[str] = None
    install_path: Optional[Path] = None
    binary_path: Optional[Path] = None
    api_key_required: bool = False
    api_key_set: bool = False
    process: Optional[subprocess.Popen] = None


class AgentManager:
    """
    Agent Manager for detecting, installing, and managing agents.

    This class is responsible for discovering available agents, handling their
    installation, and managing their lifecycle (start, stop, restart, status).
    It uses asyncio locks to ensure thread-safety for concurrent operations.

    Attributes:
        config: Configuration object
        agents: Dictionary of agent information by agent type
        _agent_locks: Dictionary of locks for each agent type
        _global_lock: Lock for operations that affect multiple agents
        _operation_timeouts: Dictionary of timeout values for different operations
    """

    def __init__(self, config: Config):
        """
        Initialize the Agent Manager.

        Args:
            config: Configuration object
        """
        self.config = config
        self.agents: Dict[AgentType, AgentInfo] = {}

        # Create locks for thread-safe operations
        self._agent_locks: Dict[AgentType, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()
        self._operation_locks: Dict[str, asyncio.Lock] = {
            "detect": asyncio.Lock(),
            "install": asyncio.Lock(),
            "start": asyncio.Lock(),
            "stop": asyncio.Lock(),
            "restart": asyncio.Lock(),
            "switch": asyncio.Lock(),
            "monitor": asyncio.Lock(),
        }

        # Define operation timeouts (in seconds)
        self._operation_timeouts = {
            "start": 30,
            "stop": 10,
            "detect": 15,
            "install": 120,
            "switch": 45,
            "restart": 60,
            "monitor_check": 5,
            "process_wait": 5,
            "validation": 10,
            "command_run": 30,
        }

        # Track active operations for monitoring
        self._active_operations: Dict[str, Dict[str, Any]] = {}

        # Initialize agents
        self._initialize_agents()

    @asynccontextmanager
    async def _track_operation(self, operation_type: str, agent_type: Optional[AgentType] = None) -> AsyncIterator[None]:
        """
        Context manager for tracking operations with timeouts and proper cleanup.

        This context manager tracks the start and end time of operations, ensures
        proper cleanup of resources, and provides thread safety through locks.

        Args:
            operation_type: Type of operation (e.g., "start", "stop", "detect")
            agent_type: Optional agent type for agent-specific operations

        Yields:
            None

        Raises:
            TimeoutError: If the operation times out
            ConcurrencyError: If there's a concurrency issue
        """
        operation_id = f"{operation_type}_{agent_type.value if agent_type else 'global'}_{int(time.time())}"
        operation_lock = self._operation_locks.get(operation_type)
        agent_lock = self._agent_locks.get(agent_type) if agent_type else None

        # Track operation start
        self._active_operations[operation_id] = {
            "type": operation_type,
            "agent_type": agent_type,
            "start_time": time.time(),
            "status": "starting"
        }

        # Acquire operation-type lock first to prevent too many concurrent operations of the same type
        if operation_lock:
            await operation_lock.acquire()

        # Then acquire agent-specific lock if needed
        if agent_lock:
            await agent_lock.acquire()

        try:
            # Update operation status
            self._active_operations[operation_id]["status"] = "running"

            # Yield control back to the caller
            yield

            # Update operation status on successful completion
            self._active_operations[operation_id]["status"] = "completed"
            self._active_operations[operation_id]["end_time"] = time.time()

        except Exception as e:
            # Update operation status on error
            self._active_operations[operation_id]["status"] = "failed"
            self._active_operations[operation_id]["end_time"] = time.time()
            self._active_operations[operation_id]["error"] = str(e)

            # Re-raise the exception
            raise

        finally:
            # Release locks in reverse order
            if agent_lock and agent_lock.locked():
                agent_lock.release()

            if operation_lock and operation_lock.locked():
                operation_lock.release()

            # Clean up operation tracking after a delay
            asyncio.create_task(self._cleanup_operation(operation_id))

    async def _cleanup_operation(self, operation_id: str) -> None:
        """
        Clean up operation tracking after a delay.

        Args:
            operation_id: ID of the operation to clean up
        """
        # Wait a bit before cleaning up to allow for logging and debugging
        await asyncio.sleep(60)

        # Remove the operation from tracking
        if operation_id in self._active_operations:
            del self._active_operations[operation_id]

    def _initialize_agents(self) -> None:
        """Initialize agent information and locks for all supported agent types."""
        for agent_type in AgentType:
            self.agents[agent_type] = AgentInfo(agent_type=agent_type)
            self._agent_locks[agent_type] = asyncio.Lock()

    async def detect_agents(self) -> Dict[AgentType, AgentInfo]:
        """
        Detect available agents on the system.

        This method checks if the Agent API and various agent types are installed
        and available on the system. It uses a global lock to ensure thread-safety
        during the detection process.

        Returns:
            Dictionary of agent information by agent type

        Raises:
            TimeoutError: If the detection operation times out
            AgentDetectionError: If there's an error during detection
        """
        # Use a timeout for the entire detection operation
        timeout = self._operation_timeouts["detect"]

        # Use our operation tracking context manager
        async with self._track_operation("detect"):
            try:
                # First, check if Agent API is installed
                agent_api_installed = await self._check_agent_api_installed()

                if not agent_api_installed:
                    logger.warning("Agent API is not installed. Agents may not work correctly.")
                    # Continue with detection anyway, as we might be able to install Agent API later

                # Load API keys from environment
                self.config.load_api_keys(validate=False)

                # First, check if any agent is already running via Agent API
                # This is a quick check to see if we can connect to the Agent API
                try:
                    # Import here to avoid circular imports
                    from .api_client import AgentAPIClient

                    # Create a temporary HTTP client
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        # Create an API client
                        api_client = AgentAPIClient(client, self.config.agent_api_url)

                        # Try to get the status
                        try:
                            status = await api_client.get_status()
                            if status:
                                logger.info(f"Agent API is running with status: {status}")

                                # Try to determine the agent type
                                agent_type_str = status.get("agentType", "").lower()
                                if agent_type_str:
                                    # Find the matching agent type
                                    for agent_enum in AgentType:
                                        if agent_enum.value.lower() == agent_type_str:
                                            logger.info(f"Detected running agent: {agent_enum.value}")

                                            # Update agent info
                                            agent_info = self.agents[agent_enum]
                                            agent_info.install_status = AgentInstallStatus.INSTALLED
                                            agent_info.running_status = AgentRunningStatus.RUNNING
                                            agent_info.version = status.get("version", "Unknown")
                                            self.agents[agent_enum] = agent_info
                                            break
                                    else:
                                        # If we couldn't find a matching agent type, assume it's custom
                                        logger.info(f"Detected running agent of unknown type: {agent_type_str}")
                                        agent_info = self.agents[AgentType.CUSTOM]
                                        agent_info.install_status = AgentInstallStatus.INSTALLED
                                        agent_info.running_status = AgentRunningStatus.RUNNING
                                        agent_info.version = status.get("version", "Unknown")
                                        self.agents[AgentType.CUSTOM] = agent_info
                                else:
                                    # If no agent type is specified, try to determine it from other sources
                                    try:
                                        detected_type = await api_client.get_agent_type()
                                        if detected_type:
                                            logger.info(f"Detected running agent type from API: {detected_type}")

                                            # Find the matching agent type
                                            for agent_enum in AgentType:
                                                if agent_enum.value.lower() == detected_type.lower():
                                                    logger.info(f"Detected running agent: {agent_enum.value}")

                                                    # Update agent info
                                                    agent_info = self.agents[agent_enum]
                                                    agent_info.install_status = AgentInstallStatus.INSTALLED
                                                    agent_info.running_status = AgentRunningStatus.RUNNING
                                                    agent_info.version = status.get("version", "Unknown")
                                                    self.agents[agent_enum] = agent_info
                                                    break
                                            else:
                                                # If we couldn't find a matching agent type, assume it's custom
                                                logger.info(f"Detected running agent of custom type: {detected_type}")
                                                agent_info = self.agents[AgentType.CUSTOM]
                                                agent_info.install_status = AgentInstallStatus.INSTALLED
                                                agent_info.running_status = AgentRunningStatus.RUNNING
                                                agent_info.version = status.get("version", "Unknown")
                                                self.agents[AgentType.CUSTOM] = agent_info
                                    except Exception as e:
                                        logger.debug(f"Error getting agent type: {e}")

                                        # If we couldn't determine the agent type, check if Goose is configured
                                        if self.config.agent_type == AgentType.GOOSE:
                                            logger.info("Assuming running agent is Goose based on configuration")
                                            agent_info = self.agents[AgentType.GOOSE]
                                            agent_info.install_status = AgentInstallStatus.INSTALLED
                                            agent_info.running_status = AgentRunningStatus.RUNNING
                                            agent_info.version = status.get("version", "Unknown")
                                            self.agents[AgentType.GOOSE] = agent_info
                        except Exception as e:
                            logger.debug(f"Error getting status from Agent API: {e}")
                except Exception as e:
                    logger.debug(f"Error checking if Agent API is running: {e}")

                # Check each agent type with individual timeouts
                detection_tasks = []
                for agent_type in AgentType:
                    # Skip detection if we already determined this agent is running
                    if self.agents[agent_type].running_status == AgentRunningStatus.RUNNING:
                        logger.info(f"Skipping detection for {agent_type.value} as it's already running")
                        continue

                    task = asyncio.create_task(self._detect_agent_with_timeout(agent_type))
                    detection_tasks.append(task)

                # Wait for all detection tasks to complete with a timeout
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*detection_tasks, return_exceptions=True),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    logger.error(f"Agent detection timed out after {timeout} seconds")
                    # Cancel any remaining tasks
                    for task in detection_tasks:
                        if not task.done():
                            task.cancel()
                    raise TimeoutError(f"Agent detection timed out after {timeout} seconds")

                # Log detection results
                installed_agents = [
                    agent_type.value for agent_type, info in self.agents.items()
                    if info.install_status == AgentInstallStatus.INSTALLED
                ]
                running_agents = [
                    agent_type.value for agent_type, info in self.agents.items()
                    if info.running_status == AgentRunningStatus.RUNNING
                ]

                logger.info(f"Detected installed agents: {', '.join(installed_agents) if installed_agents else 'None'}")
                logger.info(f"Detected running agents: {', '.join(running_agents) if running_agents else 'None'}")

                return self.agents
            except asyncio.TimeoutError:
                logger.error(f"Agent detection timed out after {timeout} seconds")
                raise TimeoutError(f"Agent detection timed out after {timeout} seconds")
            except Exception as e:
                logger.error(f"Error detecting agents: {e}")
                raise AgentDetectionError(f"Error detecting agents: {e}")

    async def _detect_agent_with_timeout(self, agent_type: AgentType) -> None:
        """
        Detect an agent with a timeout.

        Args:
            agent_type: The agent type to detect

        Raises:
            TimeoutError: If the detection operation times out
        """
        try:
            # Use the agent-specific lock for thread safety
            async with self._agent_locks[agent_type]:
                # Set a timeout for the detection operation
                timeout = self._operation_timeouts["detect"] / 2  # Use half the global timeout

                # Create a task for the detection operation
                detection_task = asyncio.create_task(self._detect_agent(agent_type))

                # Wait for the task to complete with a timeout
                await asyncio.wait_for(detection_task, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Detection of agent {agent_type.value} timed out after {timeout} seconds")
            # Update agent info to reflect the timeout
            agent_info = self.agents[agent_type]
            agent_info.install_status = AgentInstallStatus.UNKNOWN
            agent_info.running_status = AgentRunningStatus.UNKNOWN
            self.agents[agent_type] = agent_info

    async def _check_agent_api_installed(self) -> bool:
        """
        Check if Agent API is installed.

        Returns:
            True if Agent API is installed, False otherwise
        """
        # First check if agentapi command is available in PATH
        if not await self._check_command_exists("agentapi"):
            logger.warning("Agent API command not found in PATH")
            return False

        # For now, just assume it's installed if the command exists
        # This is because the --version command might not output anything
        # but the command still works
        logger.info("Agent API command found in PATH")
        return True

    async def _detect_agent(self, agent_type: AgentType) -> None:
        """
        Detect if a specific agent is installed and available through Agent API.

        This method checks if the agent can be used with Agent API by verifying:
        1. If Agent API is installed
        2. If the required API keys are set
        3. If the agent can be started with Agent API

        Args:
            agent_type: Type of agent to detect
        """
        agent_info = self.agents[agent_type]
        agent_config = self.config.get_agent_config(agent_type)

        # First, check if Agent API is installed
        if not await self._check_agent_api_installed():
            logger.warning("Agent API is not installed. Cannot detect agents properly.")
            agent_info.install_status = AgentInstallStatus.NOT_INSTALLED
            self.agents[agent_type] = agent_info
            return

        # Check if API key is required and set
        agent_info.api_key_required = bool(agent_config.api_key_env)

        # Check for API keys in environment variables
        if agent_type == AgentType.GOOSE:
            agent_info.api_key_set = bool(agent_config.api_key or os.environ.get("GOOGLE_API_KEY"))
        elif agent_type == AgentType.AIDER:
            agent_info.api_key_set = bool(agent_config.api_key or os.environ.get("OPENAI_API_KEY"))
        elif agent_type == AgentType.CLAUDE:
            agent_info.api_key_set = bool(agent_config.api_key or os.environ.get("ANTHROPIC_API_KEY"))
        elif agent_type == AgentType.CODEX:
            agent_info.api_key_set = bool(agent_config.api_key or os.environ.get("OPENAI_API_KEY"))
        else:
            agent_info.api_key_set = bool(agent_config.api_key)

        # Check if the agent binary is available
        # For Agent API, we need to check if the underlying agent is available
        binary_name = agent_type.value
        binary_path = shutil.which(binary_name)

        if binary_path:
            agent_info.binary_path = Path(binary_path)
            logger.info(f"Found agent binary: {binary_path}")
        else:
            logger.info(f"Agent binary {binary_name} not found in PATH, but may still work with Agent API")

        # Try to verify agent compatibility with Agent API
        try:
            # Use agentapi to check if the agent is supported
            # The command format is: agentapi server -- <agent> --help
            # This won't actually start the server but will check if the agent is recognized
            check_cmd = ["agentapi", "server", "--help"]
            result = await self._run_command(check_cmd)

            if result[0] == 0:
                # Check if this agent type is mentioned in the help output
                help_output = result[1].lower()
                agent_name = agent_type.value.lower()

                if agent_name in help_output or f"-- {agent_name}" in help_output:
                    logger.info(f"Agent {agent_type.value} is supported by Agent API")

                    # If the agent binary exists or API key is set, mark as installed
                    if binary_path or agent_info.api_key_set:
                        if agent_info.api_key_required and not agent_info.api_key_set:
                            logger.warning(f"Agent {agent_type.value} requires API key but none is set")
                            agent_info.install_status = AgentInstallStatus.PARTIAL
                        else:
                            agent_info.install_status = AgentInstallStatus.INSTALLED
                            logger.info(f"Agent {agent_type.value} is installed and ready to use with Agent API")
                    else:
                        agent_info.install_status = AgentInstallStatus.PARTIAL
                        logger.warning(f"Agent {agent_type.value} is supported but may require additional setup")
                else:
                    logger.warning(f"Agent {agent_type.value} may not be supported by Agent API")
                    agent_info.install_status = AgentInstallStatus.PARTIAL
            else:
                # Command failed
                logger.warning(f"Failed to verify Agent API compatibility: {result[2]}")
                agent_info.install_status = AgentInstallStatus.PARTIAL
        except Exception as e:
            logger.warning(f"Error verifying Agent API compatibility: {e}")
            agent_info.install_status = AgentInstallStatus.PARTIAL

        # Check if the agent is already running via Agent API
        if await self._validate_agent_running(agent_type):
            logger.info(f"Agent {agent_type.value} is already running via Agent API")
            agent_info.running_status = AgentRunningStatus.RUNNING

            # If this is Goose and we're connected to the Agent API, mark it as installed
            if agent_type == AgentType.GOOSE and agent_info.running_status == AgentRunningStatus.RUNNING:
                logger.info("Marking Goose as installed since it's running")
                agent_info.install_status = AgentInstallStatus.INSTALLED
                agent_info.version = "Running via Agent API"
        else:
            agent_info.running_status = AgentRunningStatus.STOPPED

        # Update agent info in the dictionary
        self.agents[agent_type] = agent_info

    async def install_agent_api(self) -> bool:
        """
        Install Agent API.

        Returns:
            True if installation was successful, False otherwise
        """
        logger.info("Installing Agent API...")

        # Determine the installation method based on the platform
        system = platform.system().lower()

        if system == "linux":
            return await self._install_agent_api_linux()
        elif system == "darwin":
            return await self._install_agent_api_macos()
        elif system == "windows":
            return await self._install_agent_api_windows()
        else:
            logger.error(f"Unsupported platform: {system}")
            return False

    async def _install_agent_api_linux(self) -> bool:
        """
        Install Agent API on Linux.

        Returns:
            True if installation was successful, False otherwise
        """
        try:
            # Try to install using go
            if await self._check_command_exists("go"):
                logger.info("Installing Agent API using Go...")
                result = await self._run_command(["go", "install", "github.com/coder/agentapi@latest"])
                if result[0] == 0:
                    logger.info("Agent API installed successfully using Go")
                    return True
                else:
                    logger.warning(f"Failed to install Agent API using Go: {result[2]}")

            # Try to download the latest release
            logger.info("Downloading Agent API binary...")
            # This is a simplified version - in a real implementation, we would:
            # 1. Fetch the latest release URL from GitHub API
            # 2. Download the appropriate binary for the platform
            # 3. Make it executable and move it to a directory in PATH

            # For now, we'll just show a message
            logger.info("Please install Agent API manually from https://github.com/coder/agentapi/releases")
            return False
        except Exception as e:
            logger.error(f"Error installing Agent API: {e}")
            return False

    async def _install_agent_api_macos(self) -> bool:
        """
        Install Agent API on macOS.

        Returns:
            True if installation was successful, False otherwise
        """
        # Similar to Linux installation but with macOS-specific adjustments
        return await self._install_agent_api_linux()

    async def _install_agent_api_windows(self) -> bool:
        """
        Install Agent API on Windows.

        Returns:
            True if installation was successful, False otherwise
        """
        try:
            # Try to install using go
            if await self._check_command_exists("go"):
                logger.info("Installing Agent API using Go...")
                result = await self._run_command(["go", "install", "github.com/coder/agentapi@latest"])
                if result[0] == 0:
                    logger.info("Agent API installed successfully using Go")
                    return True
                else:
                    logger.warning(f"Failed to install Agent API using Go: {result[2]}")

            # For Windows, we would download the .exe and add it to PATH
            logger.info("Please install Agent API manually from https://github.com/coder/agentapi/releases")
            return False
        except Exception as e:
            logger.error(f"Error installing Agent API: {e}")
            return False

    async def install_agent(self, agent_type: AgentType) -> bool:
        """
        Install a specific agent.

        Args:
            agent_type: Type of agent to install

        Returns:
            True if installation was successful, False otherwise
        """
        logger.info(f"Installing agent: {agent_type.value}")

        # Check if Agent API is installed first
        if not await self._check_agent_api_installed():
            logger.warning("Agent API is not installed. Installing it first...")
            if not await self.install_agent_api():
                logger.error("Failed to install Agent API. Cannot proceed with agent installation.")
                return False

        # Install the specific agent
        if agent_type == AgentType.GOOSE:
            return await self._install_goose()
        elif agent_type == AgentType.AIDER:
            return await self._install_aider()
        elif agent_type == AgentType.CLAUDE:
            return await self._install_claude()
        elif agent_type == AgentType.CODEX:
            return await self._install_codex()
        else:
            logger.warning(f"Installation not supported for agent type: {agent_type.value}")
            return False

    async def _install_goose(self) -> bool:
        """
        Install Goose agent using the official installation script.

        Returns:
            True if installation was successful, False otherwise
        """
        try:
            # Check if curl and bash are available
            if not await self._check_command_exists("curl") or not await self._check_command_exists("bash"):
                logger.error("curl or bash is not available. Cannot install Goose.")
                return False

            # Install Goose using the official installation script
            logger.info("Installing Goose using the official installation script...")

            # Use the recommended installation command with CONFIGURE=false to prevent automatic configuration
            install_cmd = ["bash", "-c", "curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh | CONFIGURE=false bash"]
            install_result = await self._run_command(install_cmd)

            if install_result[0] == 0:
                logger.info("Goose installed successfully")
                # Update agent info
                await self._detect_agent(AgentType.GOOSE)
                return True
            else:
                logger.error(f"Failed to install Goose: {install_result[2]}")
                return False
        except Exception as e:
            logger.error(f"Error installing Goose: {e}")
            return False

    async def _install_aider(self) -> bool:
        """
        Install Aider agent.

        Returns:
            True if installation was successful, False otherwise
        """
        try:
            # Check if pip is available
            if not await self._check_command_exists("pip"):
                logger.error("pip is not available. Cannot install Aider.")
                return False

            # Install Aider using pip
            logger.info("Installing Aider...")
            result = await self._run_command(["pip", "install", "aider-chat"])

            if result[0] == 0:
                logger.info("Aider installed successfully")
                # Update agent info
                await self._detect_agent(AgentType.AIDER)
                return True
            else:
                logger.error(f"Failed to install Aider: {result[2]}")
                return False
        except Exception as e:
            logger.error(f"Error installing Aider: {e}")
            return False

    async def _install_claude(self) -> bool:
        """
        Install Claude agent.

        Returns:
            True if installation was successful, False otherwise
        """
        try:
            # Check if npm is available
            if not await self._check_command_exists("npm"):
                logger.error("npm is not available. Cannot install Claude.")
                return False

            # Install Claude using npm
            logger.info("Installing Claude using npm...")
            result = await self._run_command(["npm", "install", "-g", "@anthropic-ai/claude-code"])

            if result[0] == 0:
                logger.info("Claude installed successfully")
                # Update agent info
                await self._detect_agent(AgentType.CLAUDE)
                return True
            else:
                logger.error(f"Failed to install Claude: {result[2]}")
                return False
        except Exception as e:
            logger.error(f"Error installing Claude: {e}")
            return False

    async def _install_codex(self) -> bool:
        """
        Install Codex agent.

        Returns:
            True if installation was successful, False otherwise
        """
        try:
            # Check if npm is available
            if not await self._check_command_exists("npm"):
                logger.error("npm is not available. Cannot install Codex.")
                return False

            # Install Codex using npm
            logger.info("Installing Codex using npm...")
            result = await self._run_command(["npm", "install", "-g", "@openai/codex"])

            if result[0] == 0:
                logger.info("Codex installed successfully")
                # Update agent info
                await self._detect_agent(AgentType.CODEX)
                return True
            else:
                logger.error(f"Failed to install Codex: {result[2]}")
                return False
        except Exception as e:
            logger.error(f"Error installing Codex: {e}")
            return False

    async def start_agent(self, agent_type: AgentType) -> Optional[subprocess.Popen]:
        """
        Start an agent with the Agent API.

        This method starts the specified agent and validates that it's running correctly.
        It uses a lock to ensure thread-safety during the start operation.

        Args:
            agent_type: Type of agent to start

        Returns:
            Process handle if the agent was started successfully, None otherwise

        Raises:
            AgentStartError: If there's an error starting the agent
            TimeoutError: If the start operation times out
        """
        timeout = self._operation_timeouts["start"]

        # Use our operation tracking context manager
        async with self._track_operation("start", agent_type):
                logger.info(f"Starting agent: {agent_type.value}")

                # Check if the agent is installed
                agent_info = self.agents.get(agent_type)
                if not agent_info or agent_info.install_status != AgentInstallStatus.INSTALLED:
                    error_msg = f"Agent {agent_type.value} is not installed"
                    logger.error(error_msg)
                    raise AgentStartError(error_msg)

                # Check if the agent is already running
                if agent_info.running_status == AgentRunningStatus.RUNNING and agent_info.process:
                    if agent_info.process.poll() is None:  # Double-check process is actually running
                        logger.warning(f"Agent {agent_type.value} is already running")
                        return agent_info.process
                    else:
                        # Process has terminated but state wasn't updated
                        logger.warning(f"Agent {agent_type.value} process has terminated unexpectedly, restarting")
                        agent_info.process = None
                        agent_info.running_status = AgentRunningStatus.STOPPED

                # Get agent configuration
                agent_config = self.config.get_agent_config(agent_type)

                # Check if API key is required but not set
                if agent_info.api_key_required and not agent_info.api_key_set:
                    # For Goose, check if GOOGLE_API_KEY is set in the environment
                    if agent_type == AgentType.GOOSE and os.environ.get("GOOGLE_API_KEY"):
                        logger.info("Found GOOGLE_API_KEY in environment, using it for Goose")
                        agent_info.api_key_set = True
                    # For Aider, check if OPENAI_API_KEY is set in the environment
                    elif agent_type == AgentType.AIDER and os.environ.get("OPENAI_API_KEY"):
                        logger.info("Found OPENAI_API_KEY in environment, using it for Aider")
                        agent_info.api_key_set = True
                    # For Claude, check if ANTHROPIC_API_KEY is set in the environment
                    elif agent_type == AgentType.CLAUDE and os.environ.get("ANTHROPIC_API_KEY"):
                        logger.info("Found ANTHROPIC_API_KEY in environment, using it for Claude")
                        agent_info.api_key_set = True
                    else:
                        error_msg = f"API key is required for {agent_type.value} but not set in {agent_config.api_key_env}"
                        logger.error(error_msg)
                        raise AgentStartError(error_msg)

                # Prepare command to start the agent with Agent API
                cmd = ["agentapi", "server", "--"]

                # Add the agent type as the first argument after --
                if agent_type == AgentType.GOOSE:
                    cmd.append("goose")

                    # Add model parameter if specified
                    if agent_config.model:
                        cmd.extend(["--model", agent_config.model])

                    # Add config file parameter if specified
                    if "config_file" in agent_config.additional_args and agent_config.additional_args["config_file"]:
                        cmd.extend(["--config", agent_config.additional_args["config_file"]])

                elif agent_type == AgentType.AIDER:
                    cmd.append("aider")

                    # Get additional arguments for Aider
                    model = agent_config.model or "deepseek"
                    api_key = agent_config.api_key

                    # Add model parameter
                    cmd.extend(["--model", model])

                    # Add API key parameter if available
                    if api_key and "api_key_param" in agent_config.additional_args:
                        cmd.extend([agent_config.additional_args["api_key_param"], f"{model}={api_key}"])

                    # Add config file parameter if specified
                    if "config_file" in agent_config.additional_args and agent_config.additional_args["config_file"]:
                        cmd.extend(["--config", agent_config.additional_args["config_file"]])

                elif agent_type == AgentType.CLAUDE:
                    cmd.append("claude")

                    # Add model parameter if specified
                    if agent_config.model:
                        cmd.extend(["--model", agent_config.model])

                    # Add config file parameter if specified
                    if "config_file" in agent_config.additional_args and agent_config.additional_args["config_file"]:
                        cmd.extend(["--config", agent_config.additional_args["config_file"]])

                elif agent_type == AgentType.CODEX:
                    cmd.append("codex")

                    # Add model parameter if specified
                    if agent_config.model:
                        cmd.extend(["--model", agent_config.model])

                    # Add provider parameter if specified
                    if "provider" in agent_config.additional_args and agent_config.additional_args["provider"]:
                        cmd.extend(["--provider", agent_config.additional_args["provider"]])

                    # Add approval mode parameter (default to suggest for safety)
                    cmd.extend(["--approval-mode", "suggest"])

                else:
                    cmd.append("custom")

                # Log the full command for debugging
                logger.debug(f"Starting agent with command: {' '.join(cmd)}")

                # Start the agent
                try:
                    # Create a copy of the current environment
                    env = os.environ.copy()

                    # Ensure API keys are set in the environment
                    if agent_type == AgentType.GOOSE and agent_config.api_key:
                        env["GOOGLE_API_KEY"] = agent_config.api_key
                    elif agent_type == AgentType.AIDER and agent_config.api_key:
                        # Aider supports multiple API providers
                        env["OPENAI_API_KEY"] = agent_config.api_key
                        # If using a different model provider, set the appropriate environment variable
                        if agent_config.model and "deepseek" in agent_config.model.lower():
                            env["DEEPSEEK_API_KEY"] = agent_config.api_key
                        elif agent_config.model and "claude" in agent_config.model.lower():
                            env["ANTHROPIC_API_KEY"] = agent_config.api_key
                    elif agent_type == AgentType.CLAUDE and agent_config.api_key:
                        env["ANTHROPIC_API_KEY"] = agent_config.api_key
                    elif agent_type == AgentType.CODEX and agent_config.api_key:
                        # Codex supports multiple API providers
                        provider = agent_config.additional_args.get("provider", "openai").lower()
                        if provider == "openai":
                            env["OPENAI_API_KEY"] = agent_config.api_key
                        elif provider == "anthropic":
                            env["ANTHROPIC_API_KEY"] = agent_config.api_key
                        elif provider == "gemini":
                            env["GEMINI_API_KEY"] = agent_config.api_key
                        elif provider == "deepseek":
                            env["DEEPSEEK_API_KEY"] = agent_config.api_key
                        elif provider == "openrouter":
                            env["OPENROUTER_API_KEY"] = agent_config.api_key
                        elif provider == "ollama":
                            env["OLLAMA_API_KEY"] = agent_config.api_key
                        elif provider == "mistral":
                            env["MISTRAL_API_KEY"] = agent_config.api_key
                        elif provider == "xai":
                            env["XAI_API_KEY"] = agent_config.api_key
                        elif provider == "groq":
                            env["GROQ_API_KEY"] = agent_config.api_key
                        elif provider == "arceeai":
                            env["ARCEEAI_API_KEY"] = agent_config.api_key
                        else:
                            # For custom providers, set a generic environment variable
                            env[f"{provider.upper()}_API_KEY"] = agent_config.api_key

                    # Log the environment variables being used (masked for security)
                    masked_env = {k: v[:4] + "..." + v[-4:] if k.endswith("_API_KEY") and len(v) > 8 else v
                                 for k, v in env.items() if k.endswith("_API_KEY")}
                    logger.info(f"Starting agent with API keys: {masked_env}")

                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        bufsize=1,
                        env=env  # Pass the environment to the child process
                    )

                    # Wait for the server to start with a timeout
                    logger.info(f"Waiting for Agent API server to start (timeout: {timeout}s)...")

                    # Use adaptive waiting with validation
                    start_time = time.time()
                    max_wait_time = timeout
                    wait_interval = 1.0  # Start with 1 second interval

                    while time.time() - start_time < max_wait_time:
                        # Check if process is still running
                        if process.poll() is not None:
                            stderr_output = process.stderr.read() if process.stderr else "No error output available"
                            error_msg = f"Agent process terminated unexpectedly with code {process.returncode}: {stderr_output}"
                            logger.error(error_msg)
                            raise AgentStartError(error_msg)

                        # Try to validate the agent is responding
                        if await self._validate_agent_running(agent_type):
                            break

                        # Wait before checking again
                        await asyncio.sleep(wait_interval)
                        # Increase wait interval slightly for exponential backoff
                        wait_interval = min(wait_interval * 1.5, 5.0)  # Cap at 5 seconds
                    else:
                        # Timeout reached without successful validation
                        process.terminate()  # Clean up the process
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()

                        error_msg = f"Timed out waiting for agent {agent_type.value} to start after {max_wait_time} seconds"
                        logger.error(error_msg)
                        raise TimeoutError(error_msg)

                    # Update agent info
                    agent_info.process = process
                    agent_info.running_status = AgentRunningStatus.RUNNING
                    self.agents[agent_type] = agent_info

                    logger.info(f"Agent {agent_type.value} started with PID {process.pid}")
                    return process
                except (AgentStartError, TimeoutError) as e:
                    # Re-raise these specific exceptions
                    raise
                except Exception as e:
                    error_msg = f"Error starting agent {agent_type.value}: {e}"
                    logger.error(error_msg)
                    raise AgentStartError(error_msg)

    async def _validate_agent_running(self, agent_type: AgentType) -> bool:
        """
        Validate that an agent is running and responding via Agent API.

        This method performs multiple checks to verify that the agent is running:
        1. Check the status endpoint to verify the agent is responding
        2. Verify the agent type matches the expected type
        3. Try to get messages to confirm the API is fully functional
        4. Check content of messages for agent-specific patterns
        5. Perform a basic connectivity test as a last resort

        Args:
            agent_type: The agent type to validate

        Returns:
            True if the agent is running and responding, False otherwise
        """
        try:
            # Import here to avoid circular imports
            from .api_client import AgentAPIClient

            # Create a temporary HTTP client with a short timeout and proper retry logic
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Create an API client
                api_client = AgentAPIClient(client, self.config.agent_api_url)

                # Track validation steps for better debugging
                validation_steps = {
                    "status_endpoint": False,
                    "agent_type_match": False,
                    "messages_endpoint": False,
                    "message_content_match": False,
                    "agent_type_api_match": False,
                    "basic_connectivity": False
                }

                # Method 1: Check status endpoint (most reliable method)
                try:
                    status = await api_client.get_status()
                    validation_steps["status_endpoint"] = True

                    # Verify the agent type matches if possible
                    agent_type_str = status.get("agentType", "").lower()
                    expected_type = agent_type.value.lower()

                    # Check for exact match or partial match (some agents may report differently)
                    if agent_type_str:
                        if agent_type_str == expected_type or expected_type in agent_type_str:
                            validation_steps["agent_type_match"] = True
                            logger.info(f"Agent type match: expected {expected_type}, got {agent_type_str}")
                        else:
                            # If we're checking for a specific agent but found a different one running
                            # Log the mismatch but continue with other validation methods
                            logger.info(f"Agent type mismatch: expected {expected_type}, got {agent_type_str}")

                            # If we're checking for a specific agent but found a different one running,
                            # we'll continue with other validation methods but note the mismatch
                            if self.config.agent_type == agent_type:
                                # If the configured agent type matches what we're checking for,
                                # we'll be more lenient with validation
                                logger.info(f"Configured agent type {agent_type.value} matches requested type")
                                validation_steps["agent_type_match"] = True

                    # Check if the agent is responding with a valid status
                    agent_status = status.get("status", "")
                    if agent_status in ["stable", "running"]:
                        logger.info(f"Agent validated as running with status: {agent_status}")

                        # If no agent type was specified in the status, try to determine it from other sources
                        if not agent_type_str:
                            # Try to get the agent type from the API client
                            try:
                                detected_agent_type = await api_client.get_agent_type()
                                if detected_agent_type and detected_agent_type.lower() == expected_type:
                                    validation_steps["agent_type_api_match"] = True
                                    logger.info(f"Agent type match from API client: {detected_agent_type}")
                            except Exception as e:
                                logger.debug(f"Error getting agent type from API client: {e}")

                        # If we got a valid status and the agent type matches or wasn't specified,
                        # we can consider this a successful validation
                        if validation_steps["agent_type_match"] or validation_steps["agent_type_api_match"]:
                            return True

                        # If the configured agent type matches what we're checking for,
                        # we'll be more lenient with validation
                        if self.config.agent_type == agent_type:
                            logger.info(f"Assuming agent is {agent_type.value} based on configuration")
                            return True
                except Exception as e:
                    logger.debug(f"Status check failed: {e}")
                    # Continue with other validation methods

                # Method 2: Try to get messages and analyze their content
                try:
                    messages = await api_client.get_messages()
                    if messages is not None:
                        validation_steps["messages_endpoint"] = True
                        logger.info(f"Agent validated as running (messages endpoint working)")

                        # Try to determine agent type from message content
                        if "messages" in messages and messages["messages"]:
                            # Agent-specific patterns to look for in messages
                            agent_patterns = {
                                AgentType.CLAUDE: [
                                    "claude", "anthropic", "assistant", "claude-3", "claude-2",
                                    "claude-instant", "claude-sonnet", "claude-haiku"
                                ],
                                AgentType.GOOSE: [
                                    "goose", "google", "gemini", "bard", "palm", "block's ai assistant",
                                    "( o)>", "(o )>"
                                ],
                                AgentType.AIDER: [
                                    "aider", "coding assistant", "git", "repo", "repository", "commit",
                                    "v0.", "tokens:", "main model:", "weak model:"
                                ],
                                AgentType.CODEX: [
                                    "codex", "openai", "gpt", "code assistant", "davinci", "code-davinci",
                                    "code interpreter"
                                ],
                                AgentType.CUSTOM: []  # No specific patterns for custom agents
                            }

                            # Check the last few messages for agent-specific patterns
                            for msg in reversed(messages["messages"]):
                                if msg.get("role") == "agent" and msg.get("content"):
                                    content = msg.get("content", "").lower()

                                    # Check for patterns specific to the expected agent type
                                    patterns = agent_patterns.get(agent_type, [])
                                    for pattern in patterns:
                                        if pattern in content:
                                            validation_steps["message_content_match"] = True
                                            logger.info(f"Agent type match from message content pattern: {pattern}")
                                            return True

                                    # Also check if the expected type appears directly in the content
                                    if expected_type in content:
                                        validation_steps["message_content_match"] = True
                                        logger.info(f"Agent type match from message content: {expected_type}")
                                        return True

                        # If the configured agent type matches what we're checking for,
                        # we'll be more lenient with validation
                        if self.config.agent_type == agent_type:
                            logger.info(f"Assuming agent is {agent_type.value} based on configuration")
                            return True

                        # If messages endpoint works but we couldn't confirm the agent type,
                        # we'll still consider it running if we're not looking for a specific agent
                        # or if we're in a lenient validation mode
                        if agent_type == AgentType.CUSTOM:
                            return True
                except Exception as e:
                    logger.debug(f"Messages check failed: {e}")
                    # Continue with other validation methods

                # Method 3: Try to get agent type directly
                try:
                    detected_type = await api_client.get_agent_type()
                    if detected_type:
                        logger.info(f"Detected agent type from API: {detected_type}")
                        if detected_type.lower() == expected_type:
                            validation_steps["agent_type_api_match"] = True
                            return True

                        # If the configured agent type matches what we're checking for,
                        # we'll be more lenient with validation
                        if self.config.agent_type == agent_type:
                            logger.info(f"Assuming agent is {agent_type.value} based on configuration")
                            return True
                except Exception as e:
                    logger.debug(f"Agent type check failed: {e}")
                    # Continue with other validation methods

                # Method 4: Check if the server responds to any request (basic connectivity)
                try:
                    response = await client.get(f"{self.config.agent_api_url}/")
                    if response.status_code < 500:  # Any response that's not a server error
                        validation_steps["basic_connectivity"] = True
                        logger.info(f"Agent API server is responding with status code {response.status_code}")

                        # If the configured agent type matches what we're checking for,
                        # we'll be more lenient with validation
                        if self.config.agent_type == agent_type:
                            logger.info(f"Assuming agent is {agent_type.value} based on configuration and connectivity")
                            return True

                        # If we at least got a response, but other checks failed, consider it partially running
                        # This is a fallback for when the API is starting up or has issues
                        return validation_steps["status_endpoint"] or validation_steps["messages_endpoint"]
                except Exception as e:
                    logger.debug(f"Basic connectivity check failed: {e}")

                # Log detailed validation results for debugging
                logger.warning(
                    f"Agent validation failed for {agent_type.value}. "
                    f"Validation steps: {validation_steps}"
                )
                return False
        except Exception as e:
            logger.debug(f"Agent validation failed with error: {e}")
            return False

    async def stop_agent(self, agent_type: AgentType) -> bool:
        """
        Stop a running agent.

        This method stops the specified agent and ensures it's properly terminated.
        It uses a lock to ensure thread-safety during the stop operation.

        Args:
            agent_type: Type of agent to stop

        Returns:
            True if the agent was stopped successfully, False otherwise

        Raises:
            AgentStopError: If there's an error stopping the agent
            TimeoutError: If the stop operation times out
        """
        timeout = self._operation_timeouts["stop"]

        # Use our operation tracking context manager
        async with self._track_operation("stop", agent_type):
                logger.info(f"Stopping agent: {agent_type.value}")

                # Check if the agent is running
                agent_info = self.agents.get(agent_type)
                if not agent_info:
                    logger.warning(f"No information available for agent {agent_type.value}")
                    return False

                if agent_info.running_status != AgentRunningStatus.RUNNING or not agent_info.process:
                    logger.warning(f"Agent {agent_type.value} is not running")

                    # Clean up any stale process reference
                    if agent_info.process and agent_info.process.poll() is not None:
                        agent_info.process = None
                        agent_info.running_status = AgentRunningStatus.STOPPED
                        self.agents[agent_type] = agent_info

                    return False

                # Stop the agent
                try:
                    # First try graceful termination
                    logger.info(f"Attempting graceful termination of agent {agent_type.value}...")
                    agent_info.process.terminate()

                    # Wait for the process to terminate with a timeout
                    try:
                        exit_code = agent_info.process.wait(timeout=timeout)
                        logger.info(f"Agent {agent_type.value} terminated with exit code {exit_code}")
                    except subprocess.TimeoutExpired:
                        # If graceful termination fails, force kill
                        logger.warning(f"Agent {agent_type.value} did not terminate gracefully after {timeout}s, forcing...")
                        agent_info.process.kill()

                        # Wait again with a shorter timeout
                        try:
                            exit_code = agent_info.process.wait(timeout=3)
                            logger.info(f"Agent {agent_type.value} killed with exit code {exit_code}")
                        except subprocess.TimeoutExpired:
                            error_msg = f"Failed to kill agent {agent_type.value} process"
                            logger.error(error_msg)
                            raise AgentStopError(error_msg)

                    # Update agent info
                    agent_info.process = None
                    agent_info.running_status = AgentRunningStatus.STOPPED
                    self.agents[agent_type] = agent_info

                    # Verify the agent is actually stopped
                    if await self._validate_agent_running(agent_type):
                        error_msg = f"Agent {agent_type.value} is still responding after stop attempt"
                        logger.error(error_msg)
                        raise AgentStopError(error_msg)

                    logger.info(f"Agent {agent_type.value} stopped successfully")
                    return True
                except (AgentStopError, TimeoutError) as e:
                    # Re-raise these specific exceptions
                    raise
                except Exception as e:
                    error_msg = f"Error stopping agent {agent_type.value}: {e}"
                    logger.error(error_msg)
                    raise AgentStopError(error_msg)

    async def restart_agent(self, agent_type: AgentType) -> Optional[subprocess.Popen]:
        """
        Restart an agent.

        This method stops and then starts the specified agent, ensuring proper cleanup
        and initialization. It uses a lock to ensure thread-safety during the restart operation.

        Args:
            agent_type: Type of agent to restart

        Returns:
            Process handle if the agent was restarted successfully, None otherwise

        Raises:
            AgentStartError: If there's an error starting the agent
            AgentStopError: If there's an error stopping the agent
            TimeoutError: If the restart operation times out
        """
        # Use our operation tracking context manager
        async with self._track_operation("restart", agent_type):
                logger.info(f"Restarting agent: {agent_type.value}")

                # Get current agent status
                agent_info = self.agents.get(agent_type)
                if not agent_info:
                    error_msg = f"No information available for agent {agent_type.value}"
                    logger.error(error_msg)
                    raise AgentSwitchError(error_msg)

                # Stop the agent if it's running
                if agent_info.running_status == AgentRunningStatus.RUNNING:
                    try:
                        await self.stop_agent(agent_type)
                    except Exception as e:
                        error_msg = f"Failed to stop agent {agent_type.value} during restart: {e}"
                        logger.error(error_msg)
                        raise AgentSwitchError(error_msg)

                # Wait a short time to ensure clean shutdown
                await asyncio.sleep(1)

                # Start the agent
                try:
                    process = await self.start_agent(agent_type)
                    if not process:
                        error_msg = f"Failed to start agent {agent_type.value} during restart"
                        logger.error(error_msg)
                        raise AgentSwitchError(error_msg)

                    logger.info(f"Agent {agent_type.value} restarted successfully")
                    return process
                except Exception as e:
                    error_msg = f"Failed to start agent {agent_type.value} during restart: {e}"
                    logger.error(error_msg)
                    raise AgentSwitchError(error_msg)

    async def get_agent_status(self, agent_type: AgentType) -> Tuple[AgentInstallStatus, AgentRunningStatus]:
        """
        Get the status of an agent.

        This method checks the current status of the specified agent, including
        both installation status and running status. It uses a lock to ensure
        thread-safety during the status check.

        Args:
            agent_type: Type of agent to check

        Returns:
            Tuple of (install_status, running_status)

        Raises:
            AgentDetectionError: If there's an error detecting the agent status
            TimeoutError: If the status check operation times out
        """
        try:
            # Use the agent-specific lock for thread safety
            async with self._agent_locks[agent_type]:
                # Update agent info with a timeout
                try:
                    # Set a timeout for the detection operation
                    timeout = self._operation_timeouts["detect"] / 2  # Use half the global timeout
                    detection_task = asyncio.create_task(self._detect_agent(agent_type))
                    await asyncio.wait_for(detection_task, timeout=timeout)
                except asyncio.TimeoutError:
                    logger.warning(f"Detection of agent {agent_type.value} timed out during status check")
                    # Continue with potentially stale information

                agent_info = self.agents.get(agent_type)
                if not agent_info:
                    return AgentInstallStatus.UNKNOWN, AgentRunningStatus.UNKNOWN

                # Check if the process is still running
                if agent_info.process:
                    if agent_info.process.poll() is None:
                        # Process is running, but also validate API is responding
                        if await self._validate_agent_running(agent_type):
                            agent_info.running_status = AgentRunningStatus.RUNNING
                        else:
                            logger.warning(f"Agent {agent_type.value} process is running but API is not responding")
                            agent_info.running_status = AgentRunningStatus.UNKNOWN
                    else:
                        logger.warning(f"Agent {agent_type.value} process has terminated unexpectedly")
                        agent_info.running_status = AgentRunningStatus.STOPPED
                        agent_info.process = None
                        self.agents[agent_type] = agent_info

                return agent_info.install_status, agent_info.running_status
        except Exception as e:
            logger.error(f"Error getting status for agent {agent_type.value}: {e}")
            raise AgentDetectionError(f"Error getting status for agent {agent_type.value}: {e}")

    async def monitor_agent(self, agent_type: AgentType, auto_reconnect: bool = True) -> None:
        """
        Monitor an agent process and optionally reconnect if it crashes.

        This method continuously monitors the specified agent and automatically
        restarts it if it crashes (when auto_reconnect is True). It uses adaptive
        monitoring intervals and proper error handling.

        Args:
            agent_type: Type of agent to monitor
            auto_reconnect: Whether to automatically reconnect if the agent crashes
        """
        logger.info(f"Starting monitoring for agent {agent_type.value}")

        # Initialize monitoring parameters
        # Use SNAPSHOT_INTERVAL for high-frequency monitoring when agent is running well
        # This matches the original Agent API's monitoring interval
        check_interval = SNAPSHOT_INTERVAL * 200  # Start with 5 seconds (200 * 25ms)
        consecutive_failures = 0
        max_failures = 5
        backoff_factor = 1.5
        max_interval = 60.0  # Maximum interval of 1 minute

        monitoring_task_active = True

        while monitoring_task_active:
            try:
                # Get current status with proper error handling
                try:
                    _, running_status = await self.get_agent_status(agent_type)

                    # Reset failure counter on successful status check
                    consecutive_failures = 0
                except Exception as e:
                    logger.warning(f"Error checking status for agent {agent_type.value}: {e}")
                    consecutive_failures += 1
                    running_status = AgentRunningStatus.UNKNOWN

                # If the agent is not running and auto-reconnect is enabled, try to restart it
                if running_status != AgentRunningStatus.RUNNING and auto_reconnect:
                    logger.warning(f"Agent {agent_type.value} is not running. Attempting to restart...")

                    try:
                        process = await self.start_agent(agent_type)
                        if process:
                            logger.info(f"Agent {agent_type.value} restarted successfully with PID {process.pid}")
                            # Reset check interval after successful restart
                            check_interval = 5.0
                            consecutive_failures = 0
                        else:
                            logger.error(f"Failed to restart agent {agent_type.value}")
                            consecutive_failures += 1
                    except Exception as e:
                        logger.error(f"Error restarting agent {agent_type.value}: {e}")
                        consecutive_failures += 1

                # If too many consecutive failures, increase check interval with exponential backoff
                if consecutive_failures > 0:
                    check_interval = min(check_interval * backoff_factor, max_interval)
                    logger.warning(f"Increasing check interval to {check_interval:.1f}s after {consecutive_failures} consecutive failures")

                # If too many consecutive failures, stop monitoring
                if consecutive_failures >= max_failures:
                    logger.error(f"Stopping monitoring for agent {agent_type.value} after {consecutive_failures} consecutive failures")
                    monitoring_task_active = False
                    break

                # Wait before checking again
                await asyncio.sleep(check_interval)

            except asyncio.CancelledError:
                logger.info(f"Monitoring task for agent {agent_type.value} cancelled")
                monitoring_task_active = False
                break
            except Exception as e:
                logger.error(f"Unexpected error in monitoring task for agent {agent_type.value}: {e}")
                consecutive_failures += 1
                # Use a short sleep interval before retrying after an unexpected error
                await asyncio.sleep(1)

        logger.info(f"Monitoring task for agent {agent_type.value} stopped")

    async def _check_command_exists(self, command: str) -> bool:
        """
        Check if a command exists in the system PATH.

        Args:
            command: Command to check

        Returns:
            True if the command exists, False otherwise
        """
        return shutil.which(command) is not None

    async def switch_agent(self, agent_type: AgentType) -> Optional[subprocess.Popen]:
        """
        Switch to a different agent.

        This method stops any currently running agent and starts the specified agent.
        It uses a global lock to ensure thread-safety during the switch operation.

        Args:
            agent_type: Type of agent to switch to

        Returns:
            Process handle if the agent was started successfully, None otherwise

        Raises:
            AgentSwitchError: If there's an error switching to the agent
            TimeoutError: If the switch operation times out
        """
        # Use our operation tracking context manager
        async with self._track_operation("switch", agent_type):
            logger.info(f"Switching to agent: {agent_type.value}")

            # Check if the agent is installed
            agent_info = self.agents.get(agent_type)
            if not agent_info or agent_info.install_status != AgentInstallStatus.INSTALLED:
                error_msg = f"Agent {agent_type.value} is not installed"
                logger.error(error_msg)
                raise AgentSwitchError(error_msg)

            # Find any currently running agent
            running_agent = None
            for current_type, info in self.agents.items():
                if (info.running_status == AgentRunningStatus.RUNNING and
                    info.process and info.process.poll() is None):
                    running_agent = current_type
                    break

            # If the requested agent is already running, just return its process
            if running_agent == agent_type:
                logger.info(f"Agent {agent_type.value} is already running")
                return agent_info.process

            # Stop the currently running agent if any
            if running_agent:
                logger.info(f"Stopping currently running agent: {running_agent.value}")
                try:
                    await self.stop_agent(running_agent)
                except Exception as e:
                    error_msg = f"Failed to stop current agent {running_agent.value}: {e}"
                    logger.error(error_msg)
                    raise AgentSwitchError(error_msg)

            # Wait a short time to ensure clean shutdown
            await asyncio.sleep(1)

            # Start the requested agent
            try:
                process = await self.start_agent(agent_type)
                if not process:
                    error_msg = f"Failed to start agent {agent_type.value}"
                    logger.error(error_msg)
                    raise AgentSwitchError(error_msg)

                logger.info(f"Successfully switched to agent {agent_type.value}")
                return process
            except Exception as e:
                error_msg = f"Error starting agent {agent_type.value} during switch: {e}"
                logger.error(error_msg)
                raise AgentSwitchError(error_msg)

    async def _run_command(self, command: List[str]) -> Tuple[int, str, str]:
        """
        Run a command and return its output.

        Args:
            command: Command to run as a list of strings

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            text=True
        )

        stdout, stderr = await process.communicate()
        return process.returncode, stdout, stderr
