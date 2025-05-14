# Contributing to MCP Server for Agent API

Thank you for considering contributing to the MCP Server for Agent API! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

Please be respectful and considerate of others when contributing to this project. We aim to foster an inclusive and welcoming community.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/mcp-server-agentapi.git`
3. Create a virtual environment: `python -m venv venv`
4. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`
5. Install development dependencies: `pip install -e ".[dev]"`

## Development Workflow

1. Create a new branch for your feature or bugfix: `git checkout -b feature/your-feature-name`
2. Make your changes
3. Run the tests: `pytest`
4. Format your code: `black .` and `isort .`
5. Run the linter: `flake8 .`
6. Run type checking: `mypy .`
7. Commit your changes: `git commit -m "Add your feature"`
8. Push to your fork: `git push origin feature/your-feature-name`
9. Create a pull request

## Testing

We use pytest for testing. To run the tests:

```bash
pytest
```

To run tests with coverage:

```bash
pytest --cov=mcp_server_agentapi
```

## Code Style

We follow the Black code style. Please format your code using Black before submitting a pull request:

```bash
black .
```

We also use isort to sort imports:

```bash
isort .
```

## Type Checking

We use mypy for type checking. Please run mypy before submitting a pull request:

```bash
mypy .
```

## Documentation

Please update the documentation when adding or modifying features. We use Google-style docstrings for Python code.

## Pull Request Process

1. Ensure your code passes all tests, linting, and type checking
2. Update the documentation if necessary
3. Update the README.md if necessary
4. Create a pull request with a clear description of the changes
5. Wait for a maintainer to review your pull request

## Release Process

Releases are managed by the maintainers. If you would like to suggest a release, please open an issue.

## Questions?

If you have any questions, please open an issue or contact the maintainers.
