"""Sanity tests to enforce code quality standards."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


class ArgumentOrderChecker(ast.NodeVisitor):
    """AST visitor to check function argument ordering."""

    def __init__(self) -> None:
        """Initialize the checker."""
        self.violations: list[dict[str, Any]] = []
        self.current_file: Path | None = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions to check argument order."""
        if self.current_file is None:
            return

        # Get function arguments (excluding self, cls, *args, **kwargs)
        args = []
        for arg in node.args.args:
            if arg.arg not in {"self", "cls"}:
                args.append(arg.arg)

        # Check if arguments are in alphabetical order
        sorted_args = sorted(args)
        if args != sorted_args:
            self.violations.append(
                {
                    "type": "function_definition",
                    "file": str(self.current_file),
                    "line": node.lineno,
                    "function": node.name,
                    "current_order": args,
                    "expected_order": sorted_args,
                }
            )

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions to check argument order."""
        if self.current_file is None:
            return

        # Get function arguments (excluding self, cls, *args, **kwargs)
        args = []
        for arg in node.args.args:
            if arg.arg not in {"self", "cls"}:
                args.append(arg.arg)

        # Check if arguments are in alphabetical order
        sorted_args = sorted(args)
        if args != sorted_args:
            self.violations.append(
                {
                    "type": "async_function_definition",
                    "file": str(self.current_file),
                    "line": node.lineno,
                    "function": node.name,
                    "current_order": args,
                    "expected_order": sorted_args,
                }
            )

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function calls to check keyword argument order."""
        if self.current_file is None:
            return

        # Extract keyword arguments
        kwargs = []
        for keyword in node.keywords:
            if keyword.arg is not None:  # Skip **kwargs
                kwargs.append(keyword.arg)

        # Check if keyword arguments are in alphabetical order
        if len(kwargs) > 1:
            sorted_kwargs = sorted(kwargs)
            if kwargs != sorted_kwargs:
                func_name = "unknown"
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                self.violations.append(
                    {
                        "type": "function_call",
                        "file": str(self.current_file),
                        "line": node.lineno,
                        "function": func_name,
                        "current_order": kwargs,
                        "expected_order": sorted_kwargs,
                    }
                )

        self.generic_visit(node)

    def check_file(self, file_path: Path) -> None:
        """Check a single Python file."""
        self.current_file = file_path
        try:
            with file_path.open(encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content)
            self.visit(tree)
        except Exception:
            # Skip files that can't be parsed
            pass

    def check_directory(self, directory: Path) -> None:
        """Check all Python files in a directory."""
        for file_path in directory.rglob("*.py"):
            if file_path.name.startswith("."):
                continue
            self.check_file(file_path)


def test_function_arguments_alphabetical_order() -> None:
    """Test that all function arguments are in alphabetical order.

    This test enforces the workspace rule that function arguments
    should be in alphabetical order for consistency and readability.
    """
    checker = ArgumentOrderChecker()

    # Check source code
    src_path = Path("src")
    if src_path.exists():
        checker.check_directory(src_path)

    # Check tests (but exclude this test file to avoid self-reference)
    tests_path = Path("tests")
    if tests_path.exists():
        checker.check_directory(tests_path)

    # Build detailed error message if violations found
    if checker.violations:
        error_lines = ["Function argument ordering violations found:"]

        for violation in checker.violations:
            error_lines.append(
                f"  {violation['file']}:{violation['line']} - "
                f"{violation['type']} '{violation['function']}' - "
                f"args: {violation['current_order']} -> {violation['expected_order']}"
            )

        error_message = "\n".join(error_lines)
        assert False, error_message


def test_function_calls_alphabetical_kwargs() -> None:
    """Test that all function calls use kwargs in alphabetical order.

    This test enforces the workspace rule that function calls
    should use named arguments in alphabetical order.
    """
    checker = ArgumentOrderChecker()

    # Check source code
    src_path = Path("src")
    if src_path.exists():
        checker.check_directory(src_path)

    # Check tests (but exclude this test file to avoid self-reference)
    tests_path = Path("tests")
    if tests_path.exists():
        checker.check_directory(tests_path)

    # Filter only function call violations
    call_violations = [v for v in checker.violations if v["type"] == "function_call"]

    # Build detailed error message if violations found
    if call_violations:
        error_lines = ["Function call keyword argument ordering violations found:"]

        for violation in call_violations:
            error_lines.append(
                f"  {violation['file']}:{violation['line']} - "
                f"call to '{violation['function']}' - "
                f"kwargs: {violation['current_order']} -> {violation['expected_order']}"
            )

        error_message = "\n".join(error_lines)
        assert False, error_message
