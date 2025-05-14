#!/usr/bin/env python3
"""
Tests for the config module.

This module contains tests for the configuration management functionality,
including loading, validation, and API key handling.
"""

import os
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import pytest

from src.config import (
    Config, load_config, save_config, load_from_env, load_from_file,
    TransportType, AgentConfig, AgentType
)
from src.exceptions import ConfigurationError, APIKeyError


class TestAgentConfig(unittest.TestCase):
    """Tests for the AgentConfig class."""

    def test_init(self):
        """Test initialization of AgentConfig."""
        # Test with API key environment variable
        config = AgentConfig(api_key_env="OPENAI_API_KEY")
        self.assertEqual(config.api_key_env, "OPENAI_API_KEY")
        self.assertEqual(config.api_key_provider, "openai")
        self.assertTrue(config.api_key_required)
        self.assertIsNone(config.api_key)
        self.assertFalse(config.api_key_validated)

        # Test without API key environment variable
        config = AgentConfig(api_key_env="")
        self.assertEqual(config.api_key_env, "")
        self.assertIsNone(config.api_key_provider)
        self.assertFalse(config.api_key_required)

    def test_validate_api_key(self):
        """Test API key validation."""
        # Test with no API key required
        config = AgentConfig(api_key_env="")
        self.assertTrue(config.validate_api_key())

        # Test with API key required but not set
        config = AgentConfig(api_key_env="OPENAI_API_KEY")
        with self.assertRaises(APIKeyError):
            config.validate_api_key()

        # Test with valid API key
        config = AgentConfig(api_key_env="OPENAI_API_KEY")
        config.api_key = "sk-" + "a" * 32
        self.assertTrue(config.validate_api_key())
        self.assertTrue(config.api_key_validated)

        # Test with invalid API key format
        config = AgentConfig(api_key_env="OPENAI_API_KEY")
        config.api_key = "invalid-key"
        with self.assertRaises(APIKeyError):
            config.validate_api_key()

    def test_mask_api_key(self):
        """Test API key masking."""
        # Test with no API key
        config = AgentConfig(api_key_env="OPENAI_API_KEY")
        self.assertEqual(config.mask_api_key(), "<not set>")

        # Test with short API key
        config = AgentConfig(api_key_env="OPENAI_API_KEY")
        config.api_key = "short"
        self.assertEqual(config.mask_api_key(), "****")

        # Test with long API key
        config = AgentConfig(api_key_env="OPENAI_API_KEY")
        config.api_key = "sk-" + "a" * 32
        self.assertEqual(config.mask_api_key(), "sk-a...aaaa")


class TestConfig(unittest.TestCase):
    """Tests for the Config class."""

    def test_init(self):
        """Test initialization of Config."""
        # Test with default values
        config = Config()
        self.assertEqual(config.agent_api_url, "http://localhost:3284")
        self.assertFalse(config.auto_start_agent)
        self.assertIsNone(config.agent_type)
        self.assertEqual(config.server.transport, TransportType.STDIO)
        self.assertEqual(config.server.host, "0.0.0.0")
        self.assertEqual(config.server.port, 8080)
        self.assertFalse(config.debug)
        self.assertEqual(config.config_version, "1.0")
        self.assertEqual(config.config_sources, ["defaults"])
        self.assertFalse(config.validated)

        # Test agent configs initialization
        self.assertIn(AgentType.GOOSE, config.agent_configs)
        self.assertIn(AgentType.AIDER, config.agent_configs)
        self.assertIn(AgentType.CLAUDE, config.agent_configs)
        self.assertIn(AgentType.CODEX, config.agent_configs)
        self.assertIn(AgentType.CUSTOM, config.agent_configs)

    def test_get_agent_config(self):
        """Test getting agent configuration."""
        config = Config()

        # Test with valid agent type
        agent_config = config.get_agent_config(AgentType.GOOSE)
        self.assertEqual(agent_config.api_key_env, "GOOGLE_API_KEY")

        # Test with invalid agent type (should return CUSTOM config)
        with patch("src.config.logger.warning") as mock_warning:
            agent_config = config.get_agent_config(AgentType.CUSTOM)
            self.assertEqual(agent_config.api_key_env, "")
            self.assertFalse(agent_config.api_key_required)

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"})
    def test_load_api_keys(self):
        """Test loading API keys from environment."""
        config = Config()

        # Test loading API keys without validation
        results = config.load_api_keys(validate=False)
        self.assertTrue(results[AgentType.GOOSE])
        self.assertEqual(config.agent_configs[AgentType.GOOSE].api_key, "test-key")
        self.assertFalse(config.agent_configs[AgentType.GOOSE].api_key_validated)

        # Test loading API keys with validation (would normally raise an error for invalid keys)
        with patch("src.config.AgentConfig.validate_api_key", return_value=True):
            results = config.load_api_keys(validate=True)
            self.assertTrue(results[AgentType.GOOSE])
            self.assertTrue(config.agent_configs[AgentType.GOOSE].api_key_validated)


@pytest.mark.asyncio
async def test_load_from_env():
    """Test loading configuration from environment variables."""
    # Test with minimal environment
    with patch.dict(os.environ, {
        "TRANSPORT": "sse",
        "HOST": "127.0.0.1",
        "PORT": "8000",
        "AGENT_API_URL": "http://localhost:4000",
        "AUTO_START_AGENT": "true",
        "AGENT_TYPE": "goose",
        "DEBUG": "true",
        "GOOGLE_API_KEY": "test-key"
    }):
        config = load_from_env()
        assert config.server.transport == TransportType.SSE
        assert config.server.host == "127.0.0.1"
        assert config.server.port == 8000
        assert config.agent_api_url == "http://localhost:4000"
        assert config.auto_start_agent is True
        assert config.agent_type == AgentType.GOOSE
        assert config.debug is True
        assert config.agent_configs[AgentType.GOOSE].api_key == "test-key"
        assert "environment" in config.config_sources


@pytest.mark.asyncio
async def test_load_from_file():
    """Test loading configuration from a file."""
    # Create a temporary config file
    config_data = {
        "agent_api_url": "http://localhost:5000",
        "auto_start_agent": True,
        "agent_type": "claude",
        "server": {
            "transport": "sse",
            "host": "127.0.0.1",
            "port": 9000
        },
        "debug": True,
        "config_version": "1.0"
    }

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json") as temp_file:
        json.dump(config_data, temp_file)
        temp_file.flush()

        # Test loading from the file
        config = load_from_file(temp_file.name)
        assert config.agent_api_url == "http://localhost:5000"
        assert config.auto_start_agent is True
        assert config.agent_type == AgentType.CLAUDE
        assert config.server.transport == TransportType.SSE
        assert config.server.host == "127.0.0.1"
        assert config.server.port == 9000
        assert config.debug is True
        assert f"file:{temp_file.name}" in config.config_sources


@pytest.mark.asyncio
async def test_save_config():
    """Test saving configuration to a file."""
    config = Config()
    config.agent_api_url = "http://localhost:6000"
    config.auto_start_agent = True
    config.agent_type = AgentType.AIDER
    config.server.transport = TransportType.SSE
    config.server.host = "127.0.0.1"
    config.server.port = 7000
    config.debug = True

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json") as temp_file:
        # Save the config
        success = save_config(config, temp_file.name)
        assert success is True

        # Read the saved config
        temp_file.seek(0)
        saved_data = json.load(temp_file)
        assert saved_data["agent_api_url"] == "http://localhost:6000"
        assert saved_data["auto_start_agent"] is True
        assert saved_data["agent_type"] == "aider"
        assert saved_data["server"]["transport"] == "sse"
        assert saved_data["server"]["host"] == "127.0.0.1"
        assert saved_data["server"]["port"] == 7000
        assert saved_data["debug"] is True


if __name__ == "__main__":
    unittest.main()
