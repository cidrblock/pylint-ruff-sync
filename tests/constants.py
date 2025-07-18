"""Shared test constants for pylint-ruff-sync tests."""

from __future__ import annotations

# Constants for toml-sort mocking
TOML_SORT_MIN_ARGS = 4

# We're mocking with exactly 6 rules, 3 implemented in ruff, 3 not implemented
EXPECTED_RULES_COUNT = 6
EXPECTED_IMPLEMENTED_RULES_COUNT = 3

# Expected number of mock rules for testing
EXPECTED_MOCK_RULES_COUNT = 6
