#!/usr/bin/env python3
"""Pre-commit hook to check function argument ordering."""

import argparse
import ast
import logging
import sys
from pathlib import Path
from typing import Any

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
        except (OSError, UnicodeDecodeError) as e:
            logger.warning("Could not read file %s: %s", file_path, e)
        except SyntaxError as e:
            logger.warning("Syntax error in file %s: %s", file_path, e)


def main() -> int:
    """Run the pre-commit hook to check function argument ordering.

    Returns:
        Exit code (0 for success, 1 for violations found).

    """
    parser = argparse.ArgumentParser(description="Check function argument ordering")
    parser.add_argument("filenames", help="Filenames to check", nargs="*")
    args = parser.parse_args()

    checker = ArgumentOrderChecker()

    # Check each provided Python file
    for filename in args.filenames:
        file_path = Path(filename)
        if file_path.suffix == ".py":
            checker.check_file(file_path)

    # Report violations
    if checker.violations:
        sys.stderr.write("Function argument ordering violations found:\n")
        for violation in checker.violations:
            sys.stderr.write(
                f"  {violation['file']}:{violation['line']} - "
                f"{violation['type']} '{violation['function']}'\n"
            )
        sys.stderr.write(f"\nTotal violations: {len(checker.violations)}\n")
        sys.stderr.write(
            "Please ensure function arguments are in alphabetical order.\n"
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
