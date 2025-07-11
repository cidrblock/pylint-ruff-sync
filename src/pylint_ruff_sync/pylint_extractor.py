"""PylintExtractor class definition."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess

from .pylint_rule import PylintRule

# Configure logging
logger = logging.getLogger(__name__)


class PylintExtractor:
    """Extracts pylint rules from pylint --list-msgs command."""

    def extract_all_rules(self) -> list[PylintRule]:
        """Extract all pylint rules from pylint --list-msgs.

        Returns:
            List of PylintRule objects.

        Raises:
            subprocess.CalledProcessError: If pylint command fails.
            Exception: If parsing fails.

        """
        try:
            logger.info("Extracting pylint rules from 'pylint --list-msgs'")
            # Try to use pylint directly first, then fall back to python -m pylint
            pylint_path = shutil.which("pylint")
            if pylint_path:
                cmd = [pylint_path, "--list-msgs"]
            else:
                # Fall back to python -m pylint (use 'python' instead of sys.executable)
                cmd = ["python", "-m", "pylint", "--list-msgs"]

            result = subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            rules = []

            # Pylint output might be in stdout or stderr, so check both
            output_text = result.stdout
            if not output_text.strip():
                output_text = result.stderr

            for line in output_text.split("\n"):
                stripped_line = line.strip()
                if not stripped_line:
                    continue

                # Match rule header like ":invalid-name (C0103): *%s name "%s"...*"
                rule_match = re.match(
                    pattern=r"^:([a-z-]+)\s+\(([A-Z]\d+)\):\s*\*(.+)\*$",
                    string=stripped_line,
                )
                if rule_match:
                    name, code, description = rule_match.groups()
                    rule = PylintRule(code=code, name=name, description=description)
                    rules.append(rule)
                    logger.debug("Found pylint rule: %s (%s)", code, name)

            logger.info("Found %d total pylint rules", len(rules))

        except subprocess.CalledProcessError:
            logger.exception("Failed to run pylint --list-msgs")
            logger.exception("Make sure pylint is installed and available in PATH")
            raise
        except Exception:
            logger.exception("Failed to parse pylint output")
            raise
        return rules

    def resolve_rule_identifiers(
        self,
        rule_identifiers: list[str],
        all_rules: list[PylintRule],
    ) -> set[str]:
        """Resolve rule identifiers to rule codes.

        Args:
            rule_identifiers: List of rule codes or names to resolve.
            all_rules: List of all available pylint rules.

        Returns:
            Set of resolved rule codes.

        """
        resolved_codes = set()
        name_to_code = {rule.name: rule.code for rule in all_rules}
        valid_codes = {rule.code for rule in all_rules}

        for identifier in rule_identifiers:
            if identifier in valid_codes:
                # Direct code match
                resolved_codes.add(identifier)
            elif identifier in name_to_code:
                # Name match - resolve to code
                resolved_codes.add(name_to_code[identifier])
            else:
                logger.warning("Unknown rule identifier: %s", identifier)

        return resolved_codes
