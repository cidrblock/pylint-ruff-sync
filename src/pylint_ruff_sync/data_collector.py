"""Data collection manager for pylint-ruff-sync tool."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from pylint_ruff_sync.mypy_overlap import MypyOverlapExtractor
from pylint_ruff_sync.pylint_extractor import PylintExtractor
from pylint_ruff_sync.ruff_pylint_extractor import RuffPylintExtractor
from pylint_ruff_sync.rule import Rules

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class DataCollector:
    """Manages data collection and cache loading for rules.

    Attributes:
        cache_path: Optional path to cache file for rules storage.

    """

    cache_path: Path | None = None

    def _is_github_cli_available(self) -> bool:
        """Check if GitHub CLI is available and working.

        Returns:
            True if gh CLI is available and authenticated, False otherwise.

        """
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],  # noqa: S607
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            logger.debug("GitHub CLI not available or not authenticated")
            return False
        else:
            return not result.returncode

    def _is_pylint_available(self) -> bool:
        """Check if pylint is available.

        Returns:
            True if pylint is available, False otherwise.

        """
        try:
            result = subprocess.run(
                ["pylint", "--version"],  # noqa: S607
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            logger.debug("Pylint not available")
            return False
        else:
            return not result.returncode

    def _is_online_capable(self) -> bool:
        """Check if we have the capabilities to fetch fresh data online.

        Returns:
            True if both GitHub CLI and pylint are available, False otherwise.

        """
        gh_available = self._is_github_cli_available()
        pylint_available = self._is_pylint_available()

        logger.debug("GitHub CLI available: %s", gh_available)
        logger.debug("Pylint available: %s", pylint_available)

        return gh_available and pylint_available

    def collect_fresh_rules(self) -> Rules:
        """Collect fresh rules from pylint and ruff extractors.

        Returns:
            Rules object with fresh data from all sources.

        """
        logger.info("Collecting fresh rules from extractors")

        # Step 1: Initialize empty Rules object
        rules = Rules()

        # Step 2: Extract all pylint rules
        pylint_extractor = PylintExtractor(rules)
        pylint_extractor.extract()
        logger.info("Found %d total pylint rules", len(rules))

        # Step 3: Update with ruff implementation data
        ruff_extractor = RuffPylintExtractor(rules)
        ruff_extractor.extract()

        ruff_implemented_count = len(rules.filter_implemented_in_ruff())
        logger.info("Found %d rules implemented in ruff", ruff_implemented_count)

        # Step 4: Update mypy overlap status
        mypy_extractor = MypyOverlapExtractor(rules)
        mypy_extractor.extract()

        return rules

    def _load_rules_from_cache(self) -> Rules:
        """Load rules from cache.

        Returns:
            Rules object loaded from cache.

        Raises:
            ValueError: If cache loading fails.

        """
        logger.info("Loading rules from cache")

        cache_path = self.cache_path
        if cache_path is None:
            cache_path = Path(__file__).parent / "data" / "ruff_implemented_rules.json"

        try:
            rules = Rules.load_from_cache(cache_path)
            if rules is None:
                msg = f"Cache file not found or invalid: {cache_path}"
                raise ValueError(msg)  # noqa: TRY301

            logger.info("Loaded %d rules from cache", len(rules))

            # Still need to apply mypy overlap to cached rules
            mypy_extractor = MypyOverlapExtractor(rules)
            mypy_extractor.extract()

        except Exception as exc:
            msg = f"Failed to load rules from cache: {exc}"
            raise ValueError(msg) from exc
        else:
            return rules

    def collect_rules(self) -> Rules:
        """Collect rules either fresh from extractors or from cache.

        Returns:
            Rules object containing all rule data.

        """
        if self._is_online_capable():
            logger.info("Online capabilities detected, collecting fresh rules")
            try:
                return self.collect_fresh_rules()
            except (ValueError, subprocess.SubprocessError, OSError) as exc:
                logger.warning(
                    "Failed to collect fresh rules, falling back to cache: %s", exc
                )
                return self._load_rules_from_cache()
        else:
            logger.info("Online capabilities not available, using cache")
            return self._load_rules_from_cache()
