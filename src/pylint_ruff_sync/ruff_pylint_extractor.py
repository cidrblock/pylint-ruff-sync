"""RuffPylintExtractor class definition."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Configure logging
logger = logging.getLogger(__name__)

# GitHub issue URL for ruff pylint implementation tracking
RUFF_PYLINT_ISSUE_URL = "https://github.com/astral-sh/ruff/issues/970"
# GitHub issue number for ruff pylint implementation tracking
RUFF_PYLINT_ISSUE_NUMBER = "970"
# GitHub repository for ruff
RUFF_REPO = "astral-sh/ruff"


@dataclass
class CacheUpdateResult:
    """Result of a cache update operation."""

    rules_added: list[str]
    rules_removed: list[str]
    total_rules: int
    has_changes: bool
    release_notes: str


class RuffPylintExtractor:
    """Extracts pylint rules implemented in ruff from GitHub issue."""

    def __init__(
        self, issue_url: str = RUFF_PYLINT_ISSUE_URL, cache_path: Path | None = None
    ) -> None:
        """Initialize a RuffPylintExtractor instance.

        Args:
            issue_url: The GitHub issue URL to fetch from
            cache_path: Path to cache file for offline usage (fallback to package data)

        """
        self.issue_url = issue_url
        self.cache_path = cache_path

    def _load_cache(self) -> list[str] | None:
        """Load implemented rules from cache file or package data.

        Returns:
            List of implemented rule codes or None if cache doesn't exist or is invalid.

        """
        # Try external cache file first if specified
        if self.cache_path is not None:
            try:
                if self.cache_path.exists():
                    with self.cache_path.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict) and "implemented_rules" in data:
                            rules = data["implemented_rules"]
                            if isinstance(rules, list):
                                logger.info(
                                    "Loaded %d rules from cache: %s",
                                    len(rules),
                                    self.cache_path,
                                )
                                return rules
                    logger.warning("Invalid cache format in %s", self.cache_path)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load cache from %s: %s", self.cache_path, e)

        # Fallback to package data using __file__ approach
        try:
            package_data_path = (
                Path(__file__).parent / "data" / "ruff_implemented_rules.json"
            )
            if package_data_path.exists():
                with package_data_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "implemented_rules" in data:
                        rules = data["implemented_rules"]
                        if isinstance(rules, list):
                            logger.info(
                                "Loaded %d rules from package data",
                                len(rules),
                            )
                            return rules
                logger.warning("Invalid cache format in package data")
            else:
                logger.warning("Package data file not found: %s", package_data_path)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load package data: %s", e)

        return None

    def _save_cache(self, rules: list[str]) -> None:
        """Save implemented rules to cache file.

        Args:
            rules: List of implemented rule codes to cache.

        """
        if self.cache_path is None:
            logger.warning("No cache path specified, cannot save cache")
            return

        try:
            # Ensure cache directory exists
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            cache_data = {
                "implemented_rules": rules,
                "source_url": self.issue_url,
                "last_updated": None,  # Will be set by GitHub action
            }

            with self.cache_path.open("w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, sort_keys=True)

            logger.info("Saved %d rules to cache: %s", len(rules), self.cache_path)
        except OSError as e:
            logger.warning("Failed to save cache to %s: %s", self.cache_path, e)

    def update_cache(self) -> CacheUpdateResult:
        """Fetch latest data from GitHub, compare with existing cache, and update.

        Returns:
            CacheUpdateResult with detailed information about what changed.

        """
        logger.info("Updating cache from %s", self.issue_url)

        # Load existing rules for comparison
        old_rules = self._load_cache() or []
        old_rules_set = set(old_rules)

        # Fetch new rules from GitHub
        new_rules = self._fetch_from_github()
        new_rules_set = set(new_rules)

        # Calculate changes
        rules_added = sorted(new_rules_set - old_rules_set)
        rules_removed = sorted(old_rules_set - new_rules_set)
        has_changes = bool(rules_added or rules_removed)

        # Generate release notes
        release_notes = self._generate_release_notes(
            rules_added=rules_added,
            rules_removed=rules_removed,
            total_rules=len(new_rules),
        )

        # Save updated cache with timestamp only if there were changes
        self._save_cache_with_changes(
            rules=new_rules,
            rules_added=rules_added,
            rules_removed=rules_removed,
            has_changes=has_changes,
            release_notes=release_notes,
        )

        result = CacheUpdateResult(
            rules_added=rules_added,
            rules_removed=rules_removed,
            total_rules=len(new_rules),
            has_changes=has_changes,
            release_notes=release_notes,
        )

        if has_changes:
            logger.info(
                "Cache updated with changes: +%d -%d rules",
                len(rules_added),
                len(rules_removed),
            )
        else:
            logger.info("No changes detected in rule list")

        return result

    def _generate_release_notes(
        self, rules_added: list[str], rules_removed: list[str], total_rules: int
    ) -> str:
        """Generate release notes for the cache update.

        Args:
            rules_added: List of rules that were added.
            rules_removed: List of rules that were removed.
            total_rules: Total number of rules after update.

        Returns:
            Formatted release notes string.

        """
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

        release_notes = f"""## Ruff Implementation Cache Update

This release contains an updated cache of pylint rules implemented in Ruff.

**Statistics:**
- Total implemented rules: {total_rules}
- Rules added: +{len(rules_added)}
- Rules removed: -{len(rules_removed)}
- Cache updated: {timestamp}
- Source: https://github.com/astral-sh/ruff/issues/970

**Rule Changes:**
"""

        if rules_added:
            release_notes += f"\n### ✅ Added Rules ({len(rules_added)})\n```\n"
            release_notes += "\n".join(rules_added)
            release_notes += "\n```\n"

        if rules_removed:
            release_notes += f"\n### ❌ Removed Rules ({len(rules_removed)})\n```\n"
            release_notes += "\n".join(rules_removed)
            release_notes += "\n```\n"

        if not rules_added and not rules_removed:
            release_notes += "\nNo rule changes in this update.\n"

        release_notes += """
**Technical Details:**
- Cache file: `src/pylint_ruff_sync/data/ruff_implemented_rules.json`
- This update ensures that the tool works correctly in offline environments like \
precommit.ci
"""

        return release_notes.strip()

    def _save_cache_with_changes(
        self,
        rules: list[str],
        rules_added: list[str],
        rules_removed: list[str],
        *,
        has_changes: bool,
        release_notes: str,
    ) -> None:
        """Save implemented rules to cache file with change tracking.

        Args:
            rules: List of implemented rule codes to cache.
            rules_added: List of rules that were added.
            rules_removed: List of rules that were removed.
            has_changes: Whether there were any changes.
            release_notes: Generated release notes.

        """
        if self.cache_path is None:
            logger.warning("No cache path specified, cannot save cache")
            return

        try:
            # Ensure cache directory exists
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            cache_data: dict[str, Any] = {
                "implemented_rules": rules,
                "source_url": self.issue_url,
                "change_summary": {
                    "rules_added": rules_added,
                    "rules_removed": rules_removed,
                    "total_rules": len(rules),
                    "has_changes": has_changes,
                    "release_notes": release_notes,
                },
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

    def _fetch_from_github(self) -> list[str]:
        """Fetch the ruff pylint implementation status from GitHub issue.

        Returns:
            List of implemented pylint rule codes.

        Raises:
            subprocess.CalledProcessError: If the gh command fails.
            json.JSONDecodeError: If the JSON response cannot be parsed.
            KeyError: If the expected keys are missing from the response.

        """
        logger.info(
            "Fetching ruff pylint implementation status from %s", self.issue_url
        )

        try:
            # Use GitHub CLI to fetch the issue body as JSON
            result = subprocess.run(  # noqa: S603
                [  # noqa: S607
                    "gh",
                    "issue",
                    "view",
                    RUFF_PYLINT_ISSUE_NUMBER,
                    "--repo",
                    RUFF_REPO,
                    "--json",
                    "body",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )

            # Parse the JSON response
            data = json.loads(result.stdout)
            issue_body = data["body"]

            if not issue_body:
                logger.warning("Empty issue body received from GitHub")
                return []

            # Extract implemented rules using regex
            implemented_rules = set()

            # Pattern to match checked task list items with pylint codes
            # Looks for: - [x] `rule-name` / `E0237` (`PLE0237`)
            # Also handles: - [x] `rule-name` /  `R0917` (`PLR0917`) (note: extra space)
            # We want to extract the pylint code (e.g., E0237, R0917)
            pattern = r"- \[x\] `[^`]*` /\s+`([A-Z]\d+)`"

            for match in re.finditer(pattern, issue_body):
                pylint_code = match.group(1)
                # Validate that it looks like a pylint code (letter followed by digits)
                if re.match(r"^[A-Z]\d+$", pylint_code):
                    implemented_rules.add(pylint_code)
                    logger.debug("Found implemented rule: %s", pylint_code)

            rules = sorted(implemented_rules)
            logger.info("Found %d implemented pylint rules in ruff", len(rules))

        except subprocess.CalledProcessError:
            logger.exception("Failed to fetch GitHub issue using GitHub CLI")
            raise

        except (json.JSONDecodeError, KeyError):
            logger.exception("Failed to parse GitHub issue response")
            raise
        else:
            return rules

    def get_implemented_rules(self) -> list[str]:
        """Extract pylint rule codes that have been implemented in ruff.

        First tries to fetch from GitHub. If that fails (e.g., no internet access),
        falls back to cached data.

        Returns:
            List of pylint rule codes that are implemented in ruff.

        Raises:
            subprocess.CalledProcessError: If unable to fetch from GitHub and no cache
                available.
            Exception: If both GitHub fetch and cache loading fail.

        """
        try:
            # Try to fetch from GitHub first
            rules = self._fetch_from_github()
            # Save to cache for future offline use
            self._save_cache(rules)
        except (subprocess.CalledProcessError, Exception) as e:
            logger.warning("Failed to fetch from GitHub: %s", e)
            logger.info("Attempting to use cached data...")

            # Fall back to cache
            cached_rules = self._load_cache()
            if cached_rules is not None:
                logger.info("Using cached data with %d rules", len(cached_rules))
                return cached_rules

            # If both fail, re-raise the original exception
            logger.exception("No cache available and GitHub fetch failed")
            raise

        return rules
