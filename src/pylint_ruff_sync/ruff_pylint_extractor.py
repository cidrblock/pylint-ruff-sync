"""Extract ruff-implemented pylint rules from GitHub issue tracking."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path

from pylint_ruff_sync.constants import (
    RUFF_PYLINT_ISSUE_NUMBER,
    RUFF_PYLINT_ISSUE_URL,
    RUFF_REPO,
)
from pylint_ruff_sync.rule import Rule, Rules, RuleSource

# Configure logging
logger = logging.getLogger(__name__)


class RuffPylintExtractor:
    """Extract pylint rules implementation status from ruff."""

    def __init__(self, *, rules: Rules) -> None:
        """Initialize the RuffPylintExtractor with a Rules object.

        Args:
            rules: Rules object to populate with ruff implementation data.

        """
        self.rules = rules
        self.issue_url = RUFF_PYLINT_ISSUE_URL

    def _load_cache(self) -> Rules | None:
        """Load implemented rules from package data as fallback.

        Returns:
            Rules object or None if package data doesn't exist or is invalid.

        """
        try:
            package_data_path = (
                Path(__file__).parent / "data" / "ruff_implemented_rules.json"
            )
            if package_data_path.exists():
                with package_data_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)

                # Handle legacy format (just list of rule codes)
                if isinstance(data, dict) and "implemented_rules" in data:
                    legacy_rules = data["implemented_rules"]
                    if isinstance(legacy_rules, list):
                        # Convert legacy format to new format
                        rules = Rules()
                        for rule_id in legacy_rules:
                            rule = Rule(
                                is_implemented_in_ruff=True,
                                is_in_ruff_issue=True,
                                pylint_id=rule_id,
                                source=RuleSource.RUFF_ISSUE,
                            )
                            rules.add_rule(rule=rule)
                        logger.debug(
                            "Loaded %d rules from legacy package data: %s",
                            len(rules),
                            package_data_path,
                        )
                        return rules

                # Handle new format (Rules dataclass serialized)
                elif isinstance(data, dict) and "rules" in data:
                    rules = Rules.from_dict(data=data)
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

    def _save_cache(self, *, rules: Rules) -> None:
        """Save implemented rules to cache file.

        Args:
            rules: Rules object to cache.

        Note:
            This method is kept for compatibility but does nothing in the simplified
            extractor. Cache management is now handled by RulesCacheManager.

        """
        # This method is now handled by RulesCacheManager
        # Kept for compatibility with get_implemented_rules method

    def _test_github_access(self) -> bool:
        """Test if GitHub CLI is available and authenticated.

        Returns:
            True if GitHub access is available, False otherwise.

        """
        try:
            subprocess.run(
                ["gh", "auth", "status"],  # noqa: S607
                capture_output=True,
                check=True,
                text=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
        else:
            return True

    def _fetch_from_github(self) -> Rules:
        """Fetch the ruff pylint implementation status from GitHub issue.

        Returns:
            Rules object with ruff implementation information.

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
                return Rules()

            # Extract rules information using regex
            rules = Rules()

            # Pattern to match task list items with pylint codes and optional ruff codes
            # Format: - [x] `rule-name` / `E0237` (PLE0237)
            # or - [ ] `rule-name` / `E0237`
            pattern = r"- \[([x ])\] `([^`]*)`\s*/\s*`([A-Z]\d+)`(?:\s*\(([^)]+)\))?"

            for match in re.finditer(pattern, issue_body):
                is_implemented = match.group(1) == "x"
                rule_name = match.group(2)
                pylint_code = match.group(3)
                ruff_code = match.group(4).strip("`") if match.group(4) else ""

                # Validate that it looks like a pylint code (letter followed by digits)
                if re.match(r"^[A-Z]\d+$", pylint_code):
                    rule = Rule(
                        is_implemented_in_ruff=is_implemented,
                        is_in_ruff_issue=True,
                        pylint_id=pylint_code,
                        pylint_name=rule_name,
                        ruff_rule=ruff_code,
                        source=RuleSource.RUFF_ISSUE,  # From ruff GitHub issue
                    )
                    rules.add_rule(rule=rule)
                    logger.debug(
                        "Found rule in issue: %s (%s) - implemented: %s, ruff_rule: %s",
                        pylint_code,
                        rule_name,
                        is_implemented,
                        ruff_code,
                    )

            if not rules:
                msg = "No rules found in issue body"
                raise KeyError(msg)  # noqa: TRY301

            implemented_count = len(rules.filter_implemented_in_ruff())
            logger.info(
                "Found %d rules in ruff issue (%d implemented)",
                len(rules),
                implemented_count,
            )

        except subprocess.CalledProcessError as e:
            logger.exception("GitHub CLI command failed: %s", e.stderr)
            raise
        except (json.JSONDecodeError, KeyError):
            logger.exception("Failed to parse GitHub issue data")
            raise
        else:
            return rules

    def get_implemented_rules(self) -> list[str]:
        """Extract pylint rule codes that have been implemented in ruff.

        Returns:
            List of pylint rule codes that are implemented in ruff.

        """
        rules = self.get_all_ruff_rules()
        return rules.get_implemented_rule_codes()

    def get_all_ruff_rules(self) -> Rules:
        """Get all rules from ruff issue (both implemented and not implemented).

        First tries to fetch from GitHub. If that fails, falls back to cache.

        Returns:
            Rules object containing all ruff-tracked rules.

        """
        # Test GitHub access first
        if not self._test_github_access():
            logger.info("GitHub CLI not available, using cache only")
            cached_rules = self._load_cache()
            if cached_rules is not None:
                logger.info("Using cached data with %d rules", len(cached_rules))
                return cached_rules
            logger.warning("No cache available and GitHub access failed")
            return Rules()

        try:
            # Try to fetch from GitHub first
            rules = self._fetch_from_github()
            logger.info("Successfully fetched %d rules from GitHub", len(rules))
        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to fetch from GitHub: %s", e)
            logger.info("Attempting to use cache fallback...")

            # Fall back to cache
            cached_rules = self._load_cache()
            if cached_rules is not None:
                logger.info("Using cached data with %d rules", len(cached_rules))
                return cached_rules

            # If both fail, return empty Rules object
            logger.warning("No cache available and GitHub fetch failed")
            return Rules()
        else:
            return rules

    def extract(self) -> None:
        """Extract ruff implementation data and update the Rules object.

        Populates the Rules object with ruff implementation metadata for all
        rules that exist in both pylint and ruff.
        """
        ruff_rules = self.get_all_ruff_rules()

        # Create a mapping of ruff rules by pylint_id
        ruff_map = {rule.pylint_id: rule for rule in ruff_rules}

        # Track which ruff rules we successfully matched
        matched_ruff_rules = set()

        # Update existing rules with ruff data, preserving original source
        for rule in self.rules:
            if rule.pylint_id in ruff_map:
                ruff_rule = ruff_map[rule.pylint_id]
                matched_ruff_rules.add(rule.pylint_id)

                # Preserve the original source, only update ruff-specific fields
                rule.is_in_ruff_issue = ruff_rule.is_in_ruff_issue
                rule.is_implemented_in_ruff = ruff_rule.is_implemented_in_ruff
                rule.ruff_rule = ruff_rule.ruff_rule
                # Update name if we have it from ruff but not from pylint
                if not rule.pylint_name and ruff_rule.pylint_name:
                    rule.pylint_name = ruff_rule.pylint_name

            # Special case: useless-suppression should always be enabled
            # Mark it as not implemented by ruff so it appears in enable list
            if rule.pylint_id == "I0021" or rule.pylint_name == "useless-suppression":
                rule.is_implemented_in_ruff = False
                rule.is_in_ruff_issue = False
                rule.ruff_rule = ""

        # Log warnings for ruff rules that don't exist in current pylint
        unmatched_ruff_rules = set(ruff_map.keys()) - matched_ruff_rules
        if unmatched_ruff_rules:
            logger.warning(
                "Found %d rules in ruff issue that don't exist in current pylint",
                len(unmatched_ruff_rules),
            )
            for rule_id in sorted(unmatched_ruff_rules):
                ruff_rule = ruff_map[rule_id]
                logger.debug(
                    "Ruff rule not in pylint: %s (%s) - possibly from plugin or older",
                    rule_id,
                    ruff_rule.pylint_name,
                )

        logger.info(
            "Updated %d pylint rules with ruff data, %d ruff rules had no pylint match",
            len(matched_ruff_rules),
            len(unmatched_ruff_rules),
        )
