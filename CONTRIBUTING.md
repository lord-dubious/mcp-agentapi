# Contributing to MCP Agent API

Thank you for considering contributing to the MCP Agent API! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

Please be respectful and considerate of others when contributing to this project. We aim to foster an inclusive and welcoming community.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/mcp-agentapi.git`
3. Set up your development environment:
   ```bash
   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install development dependencies
   pip install uv
   uv pip install -e ".[dev]"
   ```

## Development Workflow

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Make your changes
# ...

# Run tests and quality checks
pytest
black .
isort .
flake8 .
mypy .

# Commit and push
git commit -m "Add your feature"
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Testing

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=mcp_agentapi

# Run a specific test file
pytest tests/test_agent_manager.py
```

## Code Quality

```bash
# Format code with Black
black .

# Sort imports
isort .

# Lint with flake8
flake8 .

# Type checking with mypy
mypy .
```

We use Google-style docstrings for Python code.

## Pull Request Process

1. Ensure all tests pass and code quality checks succeed
2. Update documentation and README.md if necessary
3. Create a pull request with a clear description of your changes
4. Address any feedback from code reviews

## Release Process

Releases are managed by the maintainers. To suggest a release, please open an issue.

## Questions

If you have questions, please open an issue or contact the maintainers.
