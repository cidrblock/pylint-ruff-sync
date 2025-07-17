#!/usr/bin/env python3
"""Pre-commit hook to check function argument ordering."""

import argparse
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pylint_ruff_sync.argument_checker import ArgumentOrderChecker


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
