# Changelog

## [Unreleased]

### Added
- Added utility function `convert_to_agent_type` in `src/models.py` for consistent agent type conversion
- Added comprehensive documentation for multi-agent orchestration in `docs/multi_agent_orchestration.md`
- Added examples directory with `mcp_usage_example.py` moved from the root directory
- Added test script `tests/test_cleanup.py` to verify the cleanup changes

### Changed
- Updated CLI module to use the new utility function for agent type conversion
- Improved error handling in agent type conversion
- Updated README.md to include information about multi-agent orchestration
- Updated directory structure in README.md to include the new examples and docs directories

### Removed
- Removed unused imports in `src/main.py` and `src/cli.py`
- Removed commented-out screen streaming code in `src/main.py`
- Moved `mcp_usage_example.py` from the root directory to the examples directory

### Fixed
- Fixed unused imports in `src/main.py` and `src/cli.py`
- Fixed agent type conversion error handling in CLI module

## [1.0.0] - 2025-05-01

### Added
- Initial release of the MCP server for Agent API
- Support for multiple agent types: Goose, Aider, Claude, Codex, and Custom
- Agent detection, installation, and lifecycle management
- Agent configuration management
- Agent communication via the Agent API
- CLI for managing agents and the MCP server
- Support for both stdio and SSE transport modes
- Health monitoring and status reporting
- Event streaming for real-time updates
- Resource tracking and cleanup
- Error handling and logging
- Configuration management with support for environment variables, configuration files, and default values
- Documentation and examples
