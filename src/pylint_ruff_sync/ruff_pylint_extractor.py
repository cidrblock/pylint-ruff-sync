"""RuffPylintExtractor class definition."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup, Tag
except ImportError:
    sys.exit(1)


# We'll use __file__ approach for package data access for simplicity


# Configure logging
logger = logging.getLogger(__name__)

# GitHub issue URL for ruff pylint implementation tracking
RUFF_PYLINT_ISSUE_URL = "https://github.com/astral-sh/ruff/issues/970"
# Minimum number of code elements expected in an implemented rule list item
MIN_CODE_ELEMENTS = 2


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

    def update_cache(self) -> list[str]:
        """Fetch latest data from GitHub and update cache.

        Returns:
            List of implemented rule codes.

        """
        logger.info("Updating cache from %s", self.issue_url)
        rules = self._fetch_from_github()
        self._save_cache(rules)
        return rules

    def _fetch_from_github(self) -> list[str]:
        """Fetch implemented rules from GitHub issue.

        Returns:
            List of implemented rule codes.

        Raises:
            requests.RequestException: If unable to fetch the GitHub issue.
            Exception: If parsing fails.

        """
        try:
            logger.info(
                "Fetching ruff pylint implementation status from %s", self.issue_url
            )
            response = requests.get(self.issue_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(markup=response.content, features="html.parser")
            li_tags = soup.find_all("li")

            implemented_rules = set()

            for li in li_tags:
                # Only process Tag objects that have attrs and children
                if (
                    isinstance(li, Tag)
                    and hasattr(li, "attrs")
                    and "class" in li.attrs
                    and "task-list-item" in li.attrs["class"]
                ):
                    names = [
                        child.name
                        for child in li.children
                        if hasattr(child, "name") and child.name
                    ]
                    if "input" in names and "code" in names:
                        # Check if the checkbox is checked
                        checked = [
                            child.attrs.get("checked")
                            for child in li.children
                            if hasattr(child, "name")
                            and child.name == "input"
                            and hasattr(child, "attrs")
                            and "checked" in child.attrs
                        ]
                        if checked:
                            codes = [
                                child.text
                                for child in li.children
                                if hasattr(child, "name") and child.name == "code"
                            ]
                            if len(codes) >= MIN_CODE_ELEMENTS:
                                pylint_code = codes[
                                    1
                                ]  # Second code element is the pylint code
                                implemented_rules.add(pylint_code)
                                logger.debug("Found implemented rule: %s", pylint_code)

            logger.info(
                "Found %d implemented pylint rules in ruff", len(implemented_rules)
            )
            return sorted(implemented_rules)

        except requests.RequestException:
            logger.exception("Failed to fetch GitHub issue")
            raise
        except Exception:
            logger.exception("Failed to parse GitHub issue")
            raise

    def extract_implemented_rules(self) -> list[str]:
        """Extract pylint rule codes that have been implemented in ruff.

        First tries to fetch from GitHub. If that fails (e.g., no internet access),
        falls back to cached data.

        Returns:
            List of pylint rule codes that are implemented in ruff.

        Raises:
            requests.RequestException: If unable to fetch from GitHub and no cache
                available.
            Exception: If both GitHub fetch and cache loading fail.

        """
        try:
            # Try to fetch from GitHub first
            rules = self._fetch_from_github()
            # Save to cache for future offline use
            self._save_cache(rules)
        except (requests.RequestException, Exception) as e:
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
        else:
            return rules
