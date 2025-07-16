"""RuffPylintExtractor class definition."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

# GitHub issue URL for ruff pylint implementation tracking
RUFF_PYLINT_ISSUE_URL = "https://github.com/astral-sh/ruff/issues/970"
# GitHub issue number for ruff pylint implementation tracking
RUFF_PYLINT_ISSUE_NUMBER = "970"
# GitHub repository for ruff
RUFF_REPO = "astral-sh/ruff"


class RuffPylintExtractor:
    """Extracts pylint rules implemented in ruff from GitHub issue."""

    def __init__(self, issue_url: str = RUFF_PYLINT_ISSUE_URL) -> None:
        """Initialize a RuffPylintExtractor instance.

        Args:
            issue_url: The GitHub issue URL to fetch from

        """
        self.issue_url = issue_url

    def _load_cache(self) -> list[str] | None:
        """Load implemented rules from package data as fallback.

        Returns:
            List of implemented rule codes or None if package data doesn't exist or is
            invalid.

        """
        # Load from package data using __file__ approach
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
                            logger.debug(
                                "Loaded %d rules from package data: %s",
                                len(rules),
                                package_data_path,
                            )
                            return rules
            logger.warning("Invalid package data format in %s", package_data_path)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(
                "Failed to load package data from %s: %s", package_data_path, e
            )

        return None

    def _save_cache(self, rules: list[str]) -> None:
        """Save implemented rules to cache file.

        Args:
            rules: List of implemented rule codes to cache (unused in simplified
                version).

        Note:
            This method is kept for compatibility but does nothing in the simplified
            extractor. Cache management is now handled by CacheManager.

        """
        # This method is now handled by CacheManager
        # Kept for compatibility with get_implemented_rules method

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
                check=True,
                text=True,
            )

            issue_data = json.loads(result.stdout)
            issue_body = issue_data["body"]

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

            if not rules:
                msg = "No implemented rules found in issue body"
                raise KeyError(msg)  # noqa: TRY301

            logger.info("Found %d implemented pylint rules in ruff", len(rules))
        except subprocess.CalledProcessError as e:
            logger.exception("GitHub CLI command failed: %s", e.stderr)
            raise

        except (json.JSONDecodeError, KeyError):
            logger.exception("Failed to parse GitHub issue response")
            raise
        else:
            return rules

    def get_implemented_rules(self) -> list[str]:
        """Extract pylint rule codes that have been implemented in ruff.

        First tries to fetch from GitHub. If that fails (e.g., no internet access),
        falls back to package data.

        Returns:
            List of pylint rule codes that are implemented in ruff.

        Raises:
            subprocess.CalledProcessError: If unable to fetch from GitHub and no package
                data available.
            Exception: If both GitHub fetch and package data loading fail.

        """
        try:
            # Try to fetch from GitHub first
            rules = self._fetch_from_github()
            logger.info("Found %d implemented pylint rules in ruff", len(rules))
        except (subprocess.CalledProcessError, Exception) as e:
            logger.warning("Failed to fetch from GitHub: %s", e)
            logger.info("Attempting to use package data fallback...")

            # Fall back to package data
            cached_rules = self._load_cache()
            if cached_rules is not None:
                logger.info("Using package data with %d rules", len(cached_rules))
                return cached_rules

            # If both fail, re-raise the original exception
            logger.exception("No package data available and GitHub fetch failed")
            raise
        else:
            return rules
