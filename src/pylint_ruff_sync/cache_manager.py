"""Cache management for ruff implemented rules."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)


class RuleExtractor(Protocol):
    """Protocol for rule extractors."""

    @property
    def issue_url(self) -> str:
        """URL of the GitHub issue being tracked.

        Returns:
            The GitHub issue URL.

        """
        ...

    def get_implemented_rules(self) -> list[str]:
        """Get list of implemented rule codes.

        Returns:
            List of implemented rule codes.

        """
        ...


@dataclass
class CacheUpdateResult:
    """Result of a cache update operation.

    Attributes:
        rules_added: List of pylint rule codes that were added.
        rules_removed: List of pylint rule codes that were removed.
        total_rules: Total number of rules after the update.
        has_changes: Whether there were any changes in the rule list.
        release_notes: Formatted release notes describing the changes.
        commit_message: Pre-formatted commit message for git operations.
        version: Version string in YY.MM.DD.HHMMSS format.

    """

    rules_added: list[str]
    rules_removed: list[str]
    total_rules: int
    has_changes: bool
    release_notes: str
    commit_message: str
    version: str


class CacheManager:
    """Manages cache operations and change detection for ruff implemented rules."""

    def __init__(self, cache_path: Path, extractor: RuleExtractor) -> None:
        """Initialize a CacheManager instance.

        Args:
            cache_path: Path to cache file for storing rule list.
            extractor: RuleExtractor instance for fetching rules.

        """
        self.cache_path = cache_path
        self.extractor = extractor

    def _load_cache(self) -> list[str] | None:
        """Load implemented rules from cache file.

        Returns:
            List of implemented rule codes or None if cache doesn't exist or is invalid.

        """
        if not self.cache_path.exists():
            logger.debug("Cache file does not exist: %s", self.cache_path)
            return None

        try:
            with self.cache_path.open("r", encoding="utf-8") as f:
                cache_data = json.load(f)

            if not isinstance(cache_data, dict):
                logger.warning("Cache data is not a dictionary")
                return None

            implemented_rules = cache_data.get("implemented_rules")
            if not isinstance(implemented_rules, list):
                logger.warning("Cache 'implemented_rules' is not a list")
                return None

            if not all(isinstance(rule, str) for rule in implemented_rules):
                logger.warning("Cache contains non-string rule codes")
                return None

            logger.debug(
                "Loaded %d rules from cache: %s",
                len(implemented_rules),
                self.cache_path,
            )
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load cache from %s: %s", self.cache_path, e)
            return None
        else:
            return implemented_rules

    def _save_cache(self, rules: list[str], *, has_changes: bool = False) -> None:
        """Save implemented rules to cache file.

        Args:
            rules: List of implemented rule codes to cache.
            has_changes: Whether there were any changes.

        """
        try:
            # Ensure cache directory exists
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            cache_data: dict[str, Any] = {
                "implemented_rules": rules,
                "source_url": self.extractor.issue_url,
            }

            # Only add timestamp if there were actual changes
            if has_changes:
                cache_data["last_updated"] = datetime.now(UTC).isoformat()

            with self.cache_path.open("w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, sort_keys=True)
                f.write("\n")  # Ensure trailing newline

            logger.info("Saved %d rules to cache: %s", len(rules), self.cache_path)

        except OSError as e:
            logger.warning("Failed to save cache to %s: %s", self.cache_path, e)

    def update_cache(self) -> CacheUpdateResult:
        """Fetch latest data, compare with existing cache, and update.

        Returns:
            CacheUpdateResult with detailed information about what changed.

        """
        # Generate consistent timestamp for this update session
        timestamp = datetime.now(UTC)
        version = timestamp.strftime("%y.%m.%d.%H%M%S")

        logger.info("Updating cache from %s", self.extractor.issue_url)

        # Load existing rules for comparison
        old_rules = self._load_cache() or []
        old_rules_set = set(old_rules)

        # Fetch new rules from extractor
        new_rules = self.extractor.get_implemented_rules()
        new_rules_set = set(new_rules)

        # Calculate changes
        rules_added = sorted(new_rules_set - old_rules_set)
        rules_removed = sorted(old_rules_set - new_rules_set)
        has_changes = bool(rules_added or rules_removed)

        # Note: Message generation now handled by MessageGenerator class
        release_notes = ""
        commit_message = ""

        # Save updated cache
        self._save_cache(rules=new_rules, has_changes=has_changes)

        result = CacheUpdateResult(
            rules_added=rules_added,
            rules_removed=rules_removed,
            total_rules=len(new_rules),
            has_changes=has_changes,
            release_notes=release_notes,
            commit_message=commit_message,
            version=version,
        )

        if has_changes:
            logger.info(
                "Cache updated with changes: +%d -%d rules",
                len(rules_added),
                len(rules_removed),
            )
        else:
            logger.info("No changes detected in rule list")

        logger.info(
            "Cache updated successfully - %s rule changes detected",
            "no" if not has_changes else f"{len(rules_added) + len(rules_removed)}",
        )

        return result
