"""PyprojectUpdater class definition."""

from __future__ import annotations

import logging
import sys
import tomllib
from typing import TYPE_CHECKING, Any

try:
    import tomlkit
except ImportError:
    sys.exit(1)


if TYPE_CHECKING:
    from pathlib import Path

    from .pylint_rule import PylintRule

# Configure logging
logger = logging.getLogger(__name__)


class PyprojectUpdater:
    """Updates pyproject.toml with pylint configuration."""

    def __init__(self, config_file: Path) -> None:
        """Initialize a PyprojectUpdater instance.

        Args:
            config_file: Path to the pyproject.toml file

        """
        self.config_file = config_file

    def read_config(self) -> dict[str, Any]:
        """Read current configuration from pyproject.toml.

        Returns:
            The current configuration dictionary from pyproject.toml, or empty dict
            if file not found.

        Raises:
            Exception: If parsing the configuration file fails.

        """
        try:
            with self.config_file.open("rb") as f:
                config: dict[str, Any] = tomllib.load(f)
                return config
        except FileNotFoundError:
            logger.warning("No pyproject.toml found, creating new configuration")
            return {}
        except Exception:
            logger.exception("Failed to read configuration file")
            raise

    def update_pylint_config(
        self,
        config: dict[str, Any],
        rules_to_enable: set[str],
        existing_disabled: set[str],
        all_rules: list[PylintRule],
    ) -> dict[str, Any]:
        """Update pylint configuration to enable only non-implemented rules.

        Args:
            config: Current configuration dictionary.
            rules_to_enable: Set of rule codes to enable (not implemented in ruff).
            existing_disabled: Set of resolved rule codes that are disabled by user.
            all_rules: List of all pylint rules with their descriptions.

        Returns:
            Updated configuration dictionary.

        """
        # Ensure pylint section exists
        if "tool" not in config:
            config["tool"] = {}
        if "pylint" not in config["tool"]:
            config["tool"]["pylint"] = {}
        if "messages_control" not in config["tool"]["pylint"]:
            config["tool"]["pylint"]["messages_control"] = {}

        # Don't enable rules that are explicitly disabled by the user
        final_enable_rules = rules_to_enable - existing_disabled

        # Update enable list
        if final_enable_rules:
            # Create a dictionary mapping rule codes to their descriptions
            rule_descriptions = {rule.code: rule.description for rule in all_rules}

            # Create a dictionary mapping rule codes to their names for URL generation
            rule_names = {rule.code: rule.name for rule in all_rules}

            # Store the enable list and descriptions for later use by tomlkit
            enable_list = list(final_enable_rules)
            enable_list.sort()
            config["tool"]["pylint"]["messages_control"]["enable"] = enable_list
            config["tool"]["pylint"]["messages_control"]["_enable_descriptions"] = (
                rule_descriptions
            )
            config["tool"]["pylint"]["messages_control"]["_rule_names"] = rule_names

            logger.info(
                "Updated enable list with %d rules (not implemented in ruff)",
                len(final_enable_rules),
            )

            if existing_disabled & rules_to_enable:
                skipped_count = len(existing_disabled & rules_to_enable)
                logger.info(
                    "Skipped enabling %d rules that are explicitly disabled in config",
                    skipped_count,
                )

        # Preserve existing disable list - keep original format (names/codes)
        existing_disabled_raw = (
            config.get("tool", {})
            .get("pylint", {})
            .get("messages_control", {})
            .get("disable", [])
        )
        if existing_disabled_raw:
            disable_list = list(existing_disabled_raw)
            disable_list.sort()
            config["tool"]["pylint"]["messages_control"]["disable"] = disable_list
        else:
            config["tool"]["pylint"]["messages_control"]["disable"] = []

        return config

    def write_config(self, config: dict[str, Any]) -> None:
        """Write updated configuration to pyproject.toml.

        Args:
            config: The configuration dictionary to write to the file.

        Raises:
            Exception: If writing the configuration file fails.

        """
        try:
            # Read the original file with tomlkit to preserve comments and formatting
            if self.config_file.exists():
                with self.config_file.open("r", encoding="utf-8") as f:
                    doc = tomlkit.load(f)
            else:
                doc = tomlkit.document()

            # Update the document with new configuration
            self._update_toml_document(doc, config)

            # Convert to string and post-process to add inline comments
            toml_str = tomlkit.dumps(doc)

            # Post-process to add inline comments if we have enable descriptions
            if (
                "tool" in config
                and "pylint" in config["tool"]
                and "messages_control" in config["tool"]["pylint"]
                and "_enable_descriptions"
                in config["tool"]["pylint"]["messages_control"]
            ):
                descriptions = config["tool"]["pylint"]["messages_control"][
                    "_enable_descriptions"
                ]
                rule_names = config["tool"]["pylint"]["messages_control"].get(
                    "_rule_names", {}
                )
                # Combine descriptions and rule names into a single dict for processing
                combined_data = {
                    **descriptions,
                    "_rule_names": rule_names,
                }
                toml_str = self._add_inline_comments_to_enable_section(
                    toml_str, combined_data
                )

            # Write the updated document back to file
            with self.config_file.open("w", encoding="utf-8") as f:
                f.write(toml_str)
            logger.info("Updated configuration written to %s", self.config_file)
        except Exception:
            logger.exception("Failed to write configuration file")
            raise

    def _add_inline_comments_to_enable_section(
        self, toml_str: str, descriptions: dict[str, str]
    ) -> str:
        """Add inline comments to the enable section using post-processing.

        Args:
            toml_str: The TOML string content
            descriptions: Dictionary mapping rule codes to descriptions

        Returns:
            The TOML string with inline comments added

        """
        lines = toml_str.splitlines()
        new_lines = []
        in_enable_section = False

        # Map rule category codes to URL categories
        category_map = {
            "C": "convention",
            "E": "error",
            "W": "warning",
            "R": "refactor",
            "F": "fatal",
            "I": "info",
        }

        # Get rule names from descriptions (stored as "_rule_names" key)
        rule_names_data: Any = descriptions.get("_rule_names", {})
        rule_names: dict[str, str] = (
            rule_names_data if isinstance(rule_names_data, dict) else {}
        )

        for line in lines:
            stripped = line.strip()

            # Check if we're entering or leaving the enable section
            if stripped == "enable = [":
                in_enable_section = True
                new_lines.append(line)
                continue
            if in_enable_section and stripped == "]":
                in_enable_section = False
                new_lines.append(line)
                continue

            # If we're in the enable section and this line contains a rule code
            if in_enable_section and (
                (stripped.startswith('"') and stripped.endswith('"'))
                or (stripped.startswith('"') and stripped.endswith('",'))
            ):
                # Extract the rule code (remove quotes and comma)
                rule_code = stripped.strip('"').rstrip(",").strip('"')

                # Look up the rule name
                rule_name = rule_names.get(rule_code, "")

                if rule_name and rule_code:
                    # Get category from rule code (first character)
                    category_code = rule_code[0]
                    category = category_map.get(category_code, "error")

                    # Generate URL using the actual rule name
                    url = f"https://pylint.readthedocs.io/en/stable/user_guide/messages/{category}/{rule_name}.html"
                    comment = f"  # {url}"
                    new_lines.append(line + comment)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        return "\n".join(new_lines)

    def _update_toml_document(
        self,
        doc: tomlkit.TOMLDocument,
        config: dict[str, Any],
    ) -> None:
        """Update a tomlkit document with new configuration.

        Args:
            doc: The tomlkit document to update.
            config: The configuration dictionary to apply.

        """
        # Deep update the document with new configuration
        for key, value in config.items():
            if isinstance(value, dict):
                if key not in doc:
                    doc[key] = tomlkit.table()
                # Type narrowing: we know this is a table since we just set it
                table_item = doc[key]
                if isinstance(table_item, tomlkit.items.Table):
                    self._update_toml_table(table_item, value)
            else:
                doc[key] = value

    def _update_toml_table(
        self,
        table: tomlkit.items.Table,
        config: dict[str, Any],
    ) -> None:
        """Update a tomlkit table with new configuration.

        Args:
            table: The tomlkit table to update.
            config: The configuration dictionary to apply.

        """
        for key, value in config.items():
            if key in ("_enable_descriptions", "_rule_names"):
                # Skip the helper keys, they're handled during post-processing
                continue
            if key == "enable" and "_enable_descriptions" in config:
                # Special handling for enable list - create multiline array
                enable_array = tomlkit.array()
                enable_array.multiline(multiline=True)

                # Sort the rule codes to ensure consistent output
                sorted_rules = sorted(value)

                for rule_code in sorted_rules:
                    enable_array.append(tomlkit.string(rule_code))
                table[key] = enable_array
            elif isinstance(value, dict):
                if key not in table:
                    table[key] = tomlkit.table()
                # Type narrowing: we know this is a table since we just set it
                table_item = table[key]
                if isinstance(table_item, tomlkit.items.Table):
                    self._update_toml_table(table_item, value)
            else:
                table[key] = value
