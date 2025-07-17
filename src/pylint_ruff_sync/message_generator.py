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

    def __init__(self, data_dir: Path | None = None) -> None:
        """Initialize the message generator.

        Args:
            data_dir: Directory containing template files. Defaults to package data dir.

        """
        if data_dir is None:
            data_dir = Path(__file__).parent / "data"
        self.data_dir = data_dir

    def generate_commit_message(
        self,
        rules: Rules,
        *,
        old_rules: Rules | None = None,
    ) -> str:
        """Generate commit message for rule changes.

        Args:
            rules: Current rules state.
            old_rules: Previous rules state for comparison.

        Returns:
            Formatted commit message.

        """
        template_path = self.data_dir / "commit_message_template.txt"
        template_content = template_path.read_text(encoding="utf-8")
        template = Template(template_content)

        data = self._get_commit_data(rules=rules, old_rules=old_rules)
        return template.substitute(data).strip()

    def generate_release_notes(
        self,
        rules: Rules,
        *,
        old_rules: Rules | None = None,
    ) -> str:
        """Generate release notes for rule changes.

        Args:
            rules: Current rules state.
            old_rules: Previous rules state for comparison.

        Returns:
            Formatted release notes.

        """
        template_path = self.data_dir / "release_notes_template.txt"
        template_content = template_path.read_text(encoding="utf-8")
        template = Template(template_content)

        data = self._get_release_data(rules=rules, old_rules=old_rules)
        return template.substitute(data).strip()

    def _get_commit_data(
        self,
        *,
        rules: Rules,
        old_rules: Rules | None = None,
    ) -> dict[str, str]:
        """Get data for commit message template.

        Args:
            rules: Current rules state.
            old_rules: Previous rules state for comparison.

        Returns:
            Dictionary of template variables.

        """
        stats = rules.get_statistics()

        if old_rules is None:
            return {
                "added_count": "0",
                "removed_count": "0",
                "total_rules": str(stats["total_rules"]),
                "timestamp": datetime.now(UTC).isoformat(),
            }

        changes = rules.get_implementation_changes(old_rules=old_rules)
        return {
            "added_count": str(len(changes["added"])),
            "removed_count": str(len(changes["removed"])),
            "total_rules": str(stats["total_rules"]),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def _get_release_data(
        self,
        *,
        rules: Rules,
        old_rules: Rules | None = None,
    ) -> dict[str, str]:
        """Get data for release notes template.

        Args:
            rules: Current rules state.
            old_rules: Previous rules state for comparison.

        Returns:
            Dictionary of template variables.

        """
        stats = rules.get_statistics()

        if old_rules is None:
            return {
                "total_rules": str(stats["ruff_implemented"]),
                "added_count": "0",
                "removed_count": "0",
                "timestamp": datetime.now(UTC).isoformat(),
                "rule_changes_section": "Initial cache creation.",
            }

        changes = rules.get_implementation_changes(old_rules=old_rules)
        rule_changes_section = self._format_rule_changes(
            rules=rules,
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
        rules: Rules,
        changes: dict[str, set[str]],
    ) -> str:
        """Format rule changes for release notes.

        Args:
            rules: Current rules state.
            changes: Dictionary with 'added' and 'removed' rule sets.

        Returns:
            Formatted rule changes section.

        """
        sections = []

        if changes["added"]:
            sections.append(f"**Newly Implemented ({len(changes['added'])}):**")
            for rule_id in sorted(changes["added"]):
                rule = rules.get_by_id(rule_id)
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
