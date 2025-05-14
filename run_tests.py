#!/usr/bin/env python3
"""
Test runner for the MCP server.

This script runs the tests for the MCP server using pytest.
It can run all tests or specific test modules, including unit tests and integration tests.

The tests are organized by module and marked with the following markers:
- unit: Unit tests that don't require external dependencies
- integration: Integration tests that require external dependencies
- slow: Tests that take a long time to run

Examples:
    # Run all tests
    ./run_tests.py

    # Run tests in verbose mode
    ./run_tests.py -v

    # Run tests with coverage report
    ./run_tests.py -c

    # Run only unit tests
    ./run_tests.py --unit

    # Run only integration tests
    ./run_tests.py --integration

    # Run a specific test module
    ./run_tests.py tests/test_config.py
"""

import os
import sys
import argparse
import subprocess


def run_tests(test_path=None, verbose=False, coverage=False, markers=None):
    """
    Run the tests using pytest.

    Args:
        test_path: Path to the test module or directory to run
        verbose: Whether to run tests in verbose mode
        coverage: Whether to generate a coverage report
        markers: Test markers to run (e.g., "unit", "integration", "not slow")
    """
    # Ensure we're in the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    # Build the pytest command
    cmd = ["python", "-m", "pytest"]

    # Add options
    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.extend(["--cov=src", "--cov-report=term", "--cov-report=html"])

    if markers:
        cmd.extend(["-m", markers])

    # Add the test path if specified
    if test_path:
        cmd.append(test_path)

    # Run the tests
    print(f"Running tests with command: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    # Return the exit code
    return result.returncode


def main():
    """Parse arguments and run tests."""
    parser = argparse.ArgumentParser(description="Run tests for the MCP server")
    parser.add_argument(
        "test_path",
        nargs="?",
        help="Path to the test module or directory to run"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Run tests in verbose mode"
    )
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Generate a coverage report"
    )
    parser.add_argument(
        "-m", "--markers",
        help="Test markers to run (e.g., 'unit', 'integration', 'not slow')"
    )
    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run only unit tests"
    )
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run only integration tests"
    )

    args = parser.parse_args()

    # Set markers based on arguments
    markers = args.markers
    if args.unit:
        markers = "unit"
    elif args.integration:
        markers = "integration"

    # Run the tests
    exit_code = run_tests(
        test_path=args.test_path,
        verbose=args.verbose,
        coverage=args.coverage,
        markers=markers
    )

    # Exit with the same code as pytest
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
