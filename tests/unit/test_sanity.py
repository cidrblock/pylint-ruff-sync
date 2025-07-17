"""Sanity tests to ensure code quality standards are maintained."""

import sys
from pathlib import Path

import pytest

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.pylint_ruff_sync.argument_checker import ArgumentOrderChecker


def test_function_arguments_alphabetical_order() -> None:
    """Test that all function definitions have arguments in alphabetical order."""
    checker = ArgumentOrderChecker()

    # Check source code
    src_path = Path("src")
    if src_path.exists():
        checker.check_directory(src_path)

    # Check test code
    tests_path = Path("tests")
    if tests_path.exists():
        checker.check_directory(tests_path)

    # Check scripts
    scripts_path = Path("scripts")
    if scripts_path.exists():
        checker.check_directory(scripts_path)

    # If there are violations, report them and fail
    if checker.violations:
        error_lines = ["Function definition argument ordering violations:"]
        error_lines.extend(
            [
                f"  {violation['file']}:{violation['line']} - "
                f"{violation['type']} '{violation['function']}' - "
                f"args: {violation['current_order']} -> {violation['expected_order']}"
                for violation in checker.violations
            ]
        )

        error_message = "\n".join(error_lines)
        pytest.fail(error_message)


def test_function_calls_alphabetical_kwargs() -> None:
    """Test that all function calls have keyword arguments in alphabetical order."""
    # Create a separate checker for function calls
    checker = ArgumentOrderChecker()

    # Check source code
    src_path = Path("src")
    if src_path.exists():
        checker.check_directory(src_path)

    # Check test code
    tests_path = Path("tests")
    if tests_path.exists():
        checker.check_directory(tests_path)

    # Check scripts
    scripts_path = Path("scripts")
    if scripts_path.exists():
        checker.check_directory(scripts_path)

    # Filter only function call violations
    call_violations = [v for v in checker.violations if v["type"] == "Function call"]

    # If there are call violations, report them and fail
    if call_violations:
        error_lines = ["Function call keyword argument ordering violations:"]
        error_lines.extend(
            [
                f"  {violation['file']}:{violation['line']} - "
                f"call to '{violation['function']}' - "
                f"kwargs: {violation['current_order']} -> {violation['expected_order']}"
                for violation in call_violations
            ]
        )

        error_message = "\n".join(error_lines)
        pytest.fail(error_message)
