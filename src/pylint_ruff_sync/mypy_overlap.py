"""Module for handling mypy overlap with pylint rules."""

import logging
from typing import TYPE_CHECKING

from pylint_ruff_sync.constants import MYPY_OVERLAP_RULES

if TYPE_CHECKING:
    from pylint_ruff_sync.rule import Rules


class MypyOverlapExtractor:
    """Extractor for marking rules that overlap with mypy functionality."""

    def __init__(self, *, rules: "Rules") -> None:
        """Initialize the MypyOverlapExtractor.

        Args:
            rules: The Rules object to update with mypy overlap information.

        """
        self.rules = rules

    def extract(self) -> None:
        """Extract and mark mypy overlap rules in the Rules object."""
        logger = logging.getLogger(__name__)

        overlap_count = 0
        for rule in self.rules:
            if rule.pylint_id in MYPY_OVERLAP_RULES:
                rule.is_mypy_overlap = True
                overlap_count += 1
                logger.debug("Marked %s as mypy overlap", rule.pylint_id)

        logger.info("Marked %d rules as mypy overlap", overlap_count)
