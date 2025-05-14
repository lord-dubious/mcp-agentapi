#!/bin/bash
# Build script for the MCP server for Agent API

set -e

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Installing..."
    pip install uv
fi

# Clean build artifacts
echo "Cleaning build artifacts..."
rm -rf build/ dist/ *.egg-info/

# Build the package
echo "Building the package..."
uv pip build .

echo "Build complete. Artifacts are in the dist/ directory."
echo "To install the package, run: uv pip install dist/*.whl"
