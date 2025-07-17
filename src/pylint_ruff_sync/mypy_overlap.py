"""Pylint rules that have overlap with mypy type checking.

This module contains functionality to identify and mark pylint rules that overlap
with mypy type checking functionality. When mypy is used in a project, these rules
may be redundant and can be optionally excluded.

The rule list is based on research from:
- GitHub Issue: https://github.com/astral-sh/ruff/issues/970#issuecomment-1565594417
- Repository: https://github.com/antonagestam/pylint-mypy-overlap

The antonagestam repository manually analyzed pylint rules to determine which
ones have equivalent functionality in mypy when using --strict mode.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pylint_ruff_sync.constants import MYPY_OVERLAP_RULES

if TYPE_CHECKING:
    from pylint_ruff_sync.rule import Rules

# Configure logging
logger = logging.getLogger(__name__)


class MypyOverlapExtractor:
    """Extract and mark pylint rules that overlap with mypy functionality."""

    def __init__(self, rules: Rules) -> None:
        """Initialize the MypyOverlapExtractor with a Rules object.

        Args:
            rules: Rules object to populate with mypy overlap data.

        """
        self.rules = rules

    def extract(self) -> None:
        """Update Rules object with mypy overlap status.

        Marks rules that overlap with mypy functionality by setting
        their is_mypy_overlap attribute to True.

        """
        overlap_count = 0

        for rule in self.rules:
            if rule.pylint_id in MYPY_OVERLAP_RULES:
                rule.is_mypy_overlap = True
                overlap_count += 1
                logger.debug(
                    "Marked rule as mypy overlap: %s (%s)",
                    rule.pylint_id,
                    rule.pylint_name,
                )

        logger.info(
            "Marked %d rules as overlapping with mypy functionality", overlap_count
        )


def get_mypy_overlap_rules() -> set[str]:
    """Get the set of pylint rules that overlap with mypy functionality.

    Returns:
        Set of pylint rule codes that have equivalent functionality in mypy.

    """
    return MYPY_OVERLAP_RULES.copy()


def is_mypy_overlap_rule(rule_code: str) -> bool:
    """Check if a pylint rule code overlaps with mypy functionality.

    Args:
        rule_code: The pylint rule code to check (e.g., "E1101").

    Returns:
        True if the rule overlaps with mypy, False otherwise.

    """
    return rule_code in MYPY_OVERLAP_RULES
