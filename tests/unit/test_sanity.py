"""Sanity tests to ensure code quality standards are maintained."""

import ast
import logging
from pathlib import Path
from typing import Any

import pytest

# Setup logger
logger = logging.getLogger(__name__)


class ArgumentOrderChecker(ast.NodeVisitor):
    """Check that function arguments are in alphabetical order."""

    def __init__(self) -> None:
        """Initialize the checker."""
        self.violations: list[dict[str, Any]] = []
        self.current_file: Path | None = None

    def visit_functiondef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions to check argument order.

        Args:
            node: The AST node representing a function definition.

        """
        if self.current_file is None:
            return

        # Get function argument names, excluding self and cls
        args = [arg.arg for arg in node.args.args if arg.arg not in {"self", "cls"}]

        # Check if arguments are in alphabetical order
        sorted_args = sorted(args)
        if args != sorted_args:
            self.violations.append(
                {
                    "file": str(self.current_file),
                    "line": node.lineno,
                    "type": "Function definition",
                    "function": node.name,
                    "current_order": args,
                    "expected_order": sorted_args,
                }
            )

        self.generic_visit(node)

    def visit_asyncfunctiondef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions to check argument order.

        Args:
            node: The AST node representing an async function definition.

        """
        if self.current_file is None:
            return

        # Get function argument names, excluding self and cls
        args = [arg.arg for arg in node.args.args if arg.arg not in {"self", "cls"}]

        # Check if arguments are in alphabetical order
        sorted_args = sorted(args)
        if args != sorted_args:
            self.violations.append(
                {
                    "file": str(self.current_file),
                    "line": node.lineno,
                    "type": "Async function definition",
                    "function": node.name,
                    "current_order": args,
                    "expected_order": sorted_args,
                }
            )

        self.generic_visit(node)

    def visit_call(self, node: ast.Call) -> None:
        """Visit function calls to check keyword argument order.

        Args:
            node: The AST node representing a function call.

        """
        if self.current_file is None:
            return

        # Extract keyword argument names
        kwargs = [keyword.arg for keyword in node.keywords if keyword.arg is not None]

        # Check if keyword arguments are in alphabetical order
        if len(kwargs) > 1:
            sorted_kwargs = sorted(kwargs)
            if kwargs != sorted_kwargs:
                # Try to get function name
                func_name = "unknown"
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                self.violations.append(
                    {
                        "file": str(self.current_file),
                        "line": node.lineno,
                        "type": "Function call",
                        "function": func_name,
                        "current_order": kwargs,
                        "expected_order": sorted_kwargs,
                    }
                )

        self.generic_visit(node)

    def check_file(self, file_path: Path) -> None:
        """Check a single Python file for argument ordering violations.

        Args:
            file_path: Path to the Python file to check.

        """
        self.current_file = file_path
        try:
            with file_path.open("r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content)
            self.visit(tree)
        except (OSError, UnicodeDecodeError, SyntaxError) as e:
            logger.warning("Could not parse file %s: %s", file_path, e)

    def check_directory(self, directory: Path) -> None:
        """Check all Python files in a directory for argument ordering violations.

        Args:
            directory: Path to the directory to check.

        """
        for py_file in directory.rglob("*.py"):
            self.check_file(py_file)


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
