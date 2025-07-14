"""RuffPylintExtractor class definition."""

from __future__ import annotations

import logging
import sys

try:
    import requests
    from bs4 import BeautifulSoup, Tag
except ImportError:
    sys.exit(1)

# Configure logging
logger = logging.getLogger(__name__)

# GitHub issue URL for ruff pylint implementation tracking
RUFF_PYLINT_ISSUE_URL = "https://github.com/astral-sh/ruff/issues/970"
# Minimum number of code elements expected in an implemented rule list item
MIN_CODE_ELEMENTS = 2


class RuffPylintExtractor:
    """Extracts pylint rules implemented in ruff from GitHub issue."""

    def __init__(self, issue_url: str = RUFF_PYLINT_ISSUE_URL) -> None:
        """Initialize a RuffPylintExtractor instance.

        Args:
            issue_url: The GitHub issue URL to fetch from

        """
        self.issue_url = issue_url

    def extract_implemented_rules(self) -> list[str]:
        """Extract pylint rule codes that have been implemented in ruff.

        Returns:
            Set of pylint rule codes that are implemented in ruff.

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

        except requests.RequestException:
            logger.exception("Failed to fetch GitHub issue")
            raise
        except Exception:
            logger.exception("Failed to parse GitHub issue")
            raise
        return sorted(implemented_rules)
