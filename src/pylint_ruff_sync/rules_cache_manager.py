"""Cache manager for Rules objects serialization and deserialization."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from pylint_ruff_sync.rule import Rules, RuleSource

if TYPE_CHECKING:
    from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)


class RulesCacheManager:
    """Manages Rules object serialization and deserialization to/from cache files."""

    def __init__(self, cache_path: Path) -> None:
        """Initialize the cache manager.

        Args:
            cache_path: Path to cache file for storing Rules objects.

        """
        self.cache_path = cache_path

    def save_rules(self, rules: Rules) -> None:
        """Save rules to cache file.

        Args:
            rules: Rules object to save.

        Raises:
            OSError: If there's an error creating directories or writing the file.

        """
        logger.debug("Saving rules to cache: %s", self.cache_path)

        # Ensure cache directory exists
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

        # Only include rules from pylint list or ruff issue, not user disable/unknown
        cache_rules = [
            rule
            for rule in rules.rules
            if rule.source in (RuleSource.PYLINT_LIST, RuleSource.RUFF_ISSUE)
        ]

        cache_data = {
            "rules": [rule.to_dict() for rule in cache_rules],
            "metadata": rules.metadata.copy(),
        }

        try:
            with self.cache_path.open("w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, sort_keys=True)
                f.write("\n")  # Ensure trailing newline

            logger.info(
                "Saved %d rules to cache: %s", len(cache_rules), self.cache_path
            )
        except OSError as e:
            logger.warning("Failed to save cache to %s: %s", self.cache_path, e)
            raise

    def load_rules(self) -> Rules | None:
        """Load Rules object from cache file.

        Returns:
            Rules object if successful, None otherwise.

        """
        logger.debug("Loading rules from cache: %s", self.cache_path)

        if not self.cache_path.exists():
            logger.debug("Cache file does not exist: %s", self.cache_path)
            return None

        try:
            with self.cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            rules = Rules.from_dict(data)
            logger.info("Loaded %d rules from cache: %s", len(rules), self.cache_path)
        except (json.JSONDecodeError, OSError, KeyError) as e:
            logger.warning("Failed to load cache from %s: %s", self.cache_path, e)
            return None
        else:
            return rules

    def cache_exists(self) -> bool:
        """Check if cache file exists.

        Returns:
            True if cache file exists, False otherwise.

        """
        return self.cache_path.exists()
