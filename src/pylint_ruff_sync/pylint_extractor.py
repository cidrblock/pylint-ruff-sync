"""Extract pylint rules from pylint configuration."""

from __future__ import annotations

import logging
import re
import subprocess

from pylint_ruff_sync.rule import Rule, Rules, RuleSource

# Configure logging
logger = logging.getLogger(__name__)


class PylintExtractor:
    """Extract pylint rules and information."""

    def extract_all_rules(self) -> Rules:
        """Extract all available pylint rules from the configuration.

        Returns:
            Rules object containing all available pylint rules.

        Raises:
            subprocess.CalledProcessError: If pylint command fails.
            Exception: If parsing fails.

        """
        logger.info("Extracting pylint rules from 'pylint --list-msgs'")

        try:
            result = subprocess.run(
                ["pylint", "--list-msgs"],  # noqa: S607
                capture_output=True,
                check=True,
                text=True,
            )

            output_text = result.stdout
            rules = Rules()

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
                    rule = Rule(
                        pylint_id=code,
                        pylint_name=name,
                        description=description,
                        source=RuleSource.PYLINT_LIST,
                    )
                    rules.add_rule(rule)
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
        all_rules: Rules,
    ) -> set[str]:
        """Resolve rule identifiers to rule codes.

        Args:
            rule_identifiers: List of rule codes or names to resolve.
            all_rules: Rules object containing all available pylint rules.

        Returns:
            Set of resolved rule codes.

        """
        resolved_codes = set()

        for identifier in rule_identifiers:
            rule = all_rules.get_by_identifier(identifier)
            if rule:
                resolved_codes.add(rule.pylint_id)
            else:
                logger.warning("Unknown rule identifier: %s", identifier)

        return resolved_codes
