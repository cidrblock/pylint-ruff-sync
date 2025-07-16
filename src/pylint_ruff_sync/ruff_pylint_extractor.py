"""RuffPylintExtractor class definition."""

from __future__ import annotations

import json
import logging
import re
import subprocess

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
        """Initialize the extractor.

        Args:
            issue_url: URL of the GitHub issue tracking ruff pylint implementation.

        """
        self.issue_url = issue_url

    def _fetch_from_github(self) -> list[str]:
        """Fetch implemented rules from GitHub issue using GitHub CLI.

        Returns:
            List of implemented rule codes.

        Raises:
            subprocess.CalledProcessError: If unable to fetch the GitHub issue.
            json.JSONDecodeError: If the JSON response cannot be parsed.
            KeyError: If the expected keys are missing from the response.
            Exception: If parsing fails for other reasons.

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
        """Get the list of pylint rules implemented in ruff.

        Returns:
            List of implemented pylint rule codes.

        Raises:
            subprocess.CalledProcessError: If unable to fetch from GitHub.
            json.JSONDecodeError: If the JSON response cannot be parsed.
            KeyError: If the expected keys are missing from the response.
            Exception: If parsing fails for other reasons.

        """
        return self._fetch_from_github()
