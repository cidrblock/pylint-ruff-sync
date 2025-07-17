"""Message generation for commits and releases using templates."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from string import Template
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pylint_ruff_sync.rule import Rules


class MessageGenerator:
    """Generates commit messages and release notes using templates."""

    def __init__(self, *, data_dir: Path | None = None, rules: Rules) -> None:
        """Initialize the message generator.

        Args:
            rules: Rules instance to use for message generation.
            data_dir: Directory containing template files. Defaults to package data dir.

        """
        self.rules = rules
        if data_dir is None:
            data_dir = Path(__file__).parent / "data"
        self.data_dir = data_dir

    def generate(
        self,
        *,
        rules_to_disable: int,
        rules_to_enable: int,
        unknown_disabled_rules: int,
    ) -> str:
        """Generate dry-run summary message.

        Args:
            rules_to_disable: Number of rules to disable.
            unknown_disabled_rules: Number of unknown disabled rules preserved.
            rules_to_enable: Number of rules to enable.

        Returns:
            Formatted dry-run message.

        """
        return (
            f"DRY RUN: Would update configuration with:\n"
            f"  - Rules to disable: {rules_to_disable}\n"
            f"  - Unknown disabled rules preserved: {unknown_disabled_rules}\n"
            f"  - Rules to enable: {rules_to_enable}"
        )

    def generate_commit_message(
        self,
        *,
        old_rules: Rules | None = None,
    ) -> str:
        """Generate commit message for rule changes.

        Args:
            old_rules: Previous rules state for comparison.

        Returns:
            Formatted commit message.

        """
        template_path = self.data_dir / "commit_message_template.txt"
        template_content = template_path.read_text(encoding="utf-8")
        template = Template(template_content)

        data = self._get_commit_data(old_rules=old_rules)
        return template.substitute(data).strip()

    def generate_release_notes(
        self,
        *,
        old_rules: Rules | None = None,
    ) -> str:
        """Generate release notes for rule changes.

        Args:
            old_rules: Previous rules state for comparison.

        Returns:
            Formatted release notes.

        """
        template_path = self.data_dir / "release_notes_template.txt"
        template_content = template_path.read_text(encoding="utf-8")
        template = Template(template_content)

        data = self._get_release_data(old_rules=old_rules)
        return template.substitute(data).strip()

    def _get_commit_data(
        self,
        *,
        old_rules: Rules | None = None,
    ) -> dict[str, str]:
        """Get data for commit message template.

        Args:
            old_rules: Previous rules state for comparison.

        Returns:
            Dictionary of template variables.

        """
        stats = self.rules.get_statistics()

        if old_rules is None:
            return {
                "added_count": "0",
                "removed_count": "0",
                "total_rules": str(stats["total_rules"]),
                "timestamp": datetime.now(UTC).isoformat(),
            }

        changes = self.rules.get_implementation_changes(old_rules=old_rules)
        return {
            "added_count": str(len(changes["added"])),
            "removed_count": str(len(changes["removed"])),
            "total_rules": str(stats["total_rules"]),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def _get_release_data(
        self,
        *,
        old_rules: Rules | None = None,
    ) -> dict[str, str]:
        """Get data for release notes template.

        Args:
            old_rules: Previous rules state for comparison.

        Returns:
            Dictionary of template variables.

        """
        stats = self.rules.get_statistics()

        if old_rules is None:
            return {
                "total_rules": str(stats["ruff_implemented"]),
                "added_count": "0",
                "removed_count": "0",
                "timestamp": datetime.now(UTC).isoformat(),
                "rule_changes_section": "Initial cache creation.",
            }

        changes = self.rules.get_implementation_changes(old_rules=old_rules)
        rule_changes_section = self._format_rule_changes(
            changes=changes,
        )

        return {
            "total_rules": str(stats["ruff_implemented"]),
            "added_count": str(len(changes["added"])),
            "removed_count": str(len(changes["removed"])),
            "timestamp": datetime.now(UTC).isoformat(),
            "rule_changes_section": rule_changes_section,
        }

    def _format_rule_changes(
        self,
        *,
        changes: dict[str, set[str]],
    ) -> str:
        """Format rule changes for release notes.

        Args:
            changes: Dictionary with 'added' and 'removed' rule sets.

        Returns:
            Formatted rule changes section.

        """
        sections = []

        if changes["added"]:
            sections.append(f"**Newly Implemented ({len(changes['added'])}):**")
            for rule_id in sorted(changes["added"]):
                rule = self.rules.get_by_id(pylint_id=rule_id)
                if rule:
                    sections.append(f"- `{rule_id}` - {rule.pylint_name}")
                else:
                    sections.append(f"- `{rule_id}`")
            sections.append("")

        if changes["removed"]:
            sections.append(f"**No Longer Implemented ({len(changes['removed'])}):**")
            sections.extend(f"- `{rule_id}`" for rule_id in sorted(changes["removed"]))
            sections.append("")

        if not changes["added"] and not changes["removed"]:
            sections.append("No rule implementation changes in this update.")

        return "\n".join(sections)
