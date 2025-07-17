#!/usr/bin/env python3
"""Pre-commit hook to check function argument ordering."""

import argparse
import ast
import sys
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
        args = [arg.arg for arg in node.args.args if arg.arg not in {"self", "cls"}]

        # Check if arguments are in alphabetical order
        if args != sorted(args):
            self.violations.append(
                {
                    "file": str(self.current_file),
                    "line": node.lineno,
                    "function": node.name,
                    "type": "function_definition",
                }
            )

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions to check argument order."""
        if self.current_file is None:
            return

        # Get function arguments (excluding self, cls, *args, **kwargs)
        args = [arg.arg for arg in node.args.args if arg.arg not in {"self", "cls"}]

        # Check if arguments are in alphabetical order
        if args != sorted(args):
            self.violations.append(
                {
                    "file": str(self.current_file),
                    "line": node.lineno,
                    "function": node.name,
                    "type": "async_function_definition",
                }
            )

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function calls to check keyword argument order."""
        if self.current_file is None:
            return

        # Extract keyword arguments
        kwargs = [
            keyword.arg
            for keyword in node.keywords
            if keyword.arg is not None  # Skip **kwargs
        ]

        # Check if keyword arguments are in alphabetical order
        if len(kwargs) > 1 and kwargs != sorted(kwargs):
            func_name = "unknown"
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            self.violations.append(
                {
                    "file": str(self.current_file),
                    "line": node.lineno,
                    "function": func_name,
                    "type": "function_call",
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
            # Skip files that can't be parsed (e.g., syntax errors)
            pass


def main() -> int:
    """Main function for the pre-commit hook."""
    parser = argparse.ArgumentParser(description="Check function argument ordering")
    parser.add_argument("filenames", nargs="*", help="Filenames to check")
    args = parser.parse_args()

    checker = ArgumentOrderChecker()

    # Check all provided files
    for filename in args.filenames:
        file_path = Path(filename)
        if file_path.suffix == ".py":
            checker.check_file(file_path)

    # Report violations
    if checker.violations:
        print("Function argument ordering violations found:")
        for violation in checker.violations:
            print(
                f"  {violation['file']}:{violation['line']} - "
                f"{violation['type']} '{violation['function']}'"
            )
        print(f"\nTotal violations: {len(checker.violations)}")
        print("Please ensure function arguments are in alphabetical order.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
