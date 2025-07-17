"""Rule and Rules dataclasses for structured rule management."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class RuleSource(Enum):
    """Source of rule information."""

    PYLINT_LIST = "pylint_list"
    RUFF_ISSUE = "ruff_issue"
    USER_DISABLE = "user_disable"
    UNKNOWN = "unknown"


@dataclass
class Rule:
    """Data structure for a single pylint rule with all metadata.

    Attributes:
        pylint_id: The pylint rule ID (e.g., 'C0103')
        pylint_name: The pylint rule name (e.g., 'invalid-name')
        description: Rule description
        is_in_ruff_issue: Whether this rule is listed in the ruff tracking issue
        is_implemented_in_ruff: Whether this rule is implemented in ruff
        is_mypy_overlap: Whether this rule overlaps with mypy functionality
        ruff_rule: Corresponding ruff rule code if available
        pylint_docs_url: URL to pylint documentation for this rule
        source: Source where this rule was discovered
        pylint_category: Category from rule ID (C/E/W/R/I/F)
        user_comment: User comment from disable list

    """

    pylint_id: str
    pylint_name: str = ""
    description: str = ""
    is_in_ruff_issue: bool = False
    is_implemented_in_ruff: bool = False
    is_mypy_overlap: bool = False
    ruff_rule: str = ""
    pylint_docs_url: str = ""
    source: RuleSource = RuleSource.UNKNOWN
    pylint_category: str = ""
    user_comment: str = ""

    # Map rule category codes to URL categories
    CATEGORY_MAP: ClassVar[dict[str, str]] = {
        "C": "convention",
        "E": "error",
        "W": "warning",
        "R": "refactor",
        "I": "info",
        "F": "fatal",
    }

    def __post_init__(self) -> None:
        """Post-initialization processing."""
        # Extract category from pylint_id if not set
        if not self.pylint_category and self.pylint_id:
            self.pylint_category = self.pylint_id[0] if self.pylint_id else ""

        # Generate pylint docs URL if not set
        if not self.pylint_docs_url and self.pylint_id and self.pylint_name:
            category_name = self.CATEGORY_MAP.get(self.pylint_category, "")
            if category_name:
                self.pylint_docs_url = (
                    f"https://pylint.readthedocs.io/en/stable/user_guide/messages/"
                    f"{category_name}/{self.pylint_name}.html"
                )

    @property
    def code(self) -> str:
        """Backward compatibility property for rule_id.

        Returns:
            The rule ID (same as pylint_id).

        """
        return self.pylint_id

    @property
    def name(self) -> str:
        """Backward compatibility property for name.

        Returns:
            The rule name (same as pylint_name).

        """
        return self.pylint_name

    def should_be_enabled_in_pylint(self) -> bool:
        """Check if this rule should be enabled in pylint.

        A rule should be enabled in pylint if:
        - It's not implemented in ruff (ruff would handle it)
        - It doesn't overlap with mypy (mypy would handle it)

        Returns:
            True if rule should be enabled in pylint.

        """
        return not self.is_implemented_in_ruff and not self.is_mypy_overlap

    def should_be_kept_disabled(self, *, explicitly_enabled: bool = False) -> bool:
        """Check if this rule should be kept in the disable list.

        Args:
            explicitly_enabled: Whether the rule is explicitly enabled by user.

        Returns:
            True if rule should be kept disabled.

        """
        if explicitly_enabled:
            return False

        # Keep disabled if it would otherwise be enabled
        return self.should_be_enabled_in_pylint()

    def to_dict(self) -> dict[str, Any]:
        """Convert rule to dictionary for serialization.

        Returns:
            Dictionary representation of the rule.

        """
        return {
            "pylint_id": self.pylint_id,
            "pylint_name": self.pylint_name,
            "description": self.description,
            "is_in_ruff_issue": self.is_in_ruff_issue,
            "is_implemented_in_ruff": self.is_implemented_in_ruff,
            "is_mypy_overlap": self.is_mypy_overlap,
            "ruff_rule": self.ruff_rule,
            "pylint_docs_url": self.pylint_docs_url,
            "source": self.source.value,
            "pylint_category": self.pylint_category,
            "user_comment": self.user_comment,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Rule:
        """Create rule from dictionary.

        Args:
            data: Dictionary representation of the rule.

        Returns:
            Rule instance.

        """
        # Convert source string back to enum
        source_str = data.get("source", "unknown")
        try:
            source = RuleSource(source_str)
        except ValueError:
            source = RuleSource.UNKNOWN

        return cls(
            pylint_id=data.get("pylint_id", ""),
            pylint_name=data.get("pylint_name", ""),
            description=data.get("description", ""),
            is_in_ruff_issue=data.get("is_in_ruff_issue", False),
            is_implemented_in_ruff=data.get("is_implemented_in_ruff", False),
            is_mypy_overlap=data.get("is_mypy_overlap", False),
            ruff_rule=data.get("ruff_rule", ""),
            pylint_docs_url=data.get("pylint_docs_url", ""),
            source=source,
            pylint_category=data.get("pylint_category", ""),
            user_comment=data.get("user_comment", ""),
        )


@dataclass
class Rules:
    """Collection of Rule objects with filtering and management methods.

    Attributes:
        rules: List of Rule objects
        metadata: Additional metadata about the rule collection

    """

    rules: list[Rule] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Post-initialization processing."""
        # Ensure rules are sorted by pylint_id
        self.rules.sort(key=lambda r: r.pylint_id)

    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the collection.

        Args:
            rule: Rule to add.

        """
        self.rules.append(rule)
        # Re-sort after adding
        self.rules.sort(key=lambda r: r.pylint_id)

    def update_rule(self, updated_rule: Rule) -> None:
        """Update an existing rule or add if not found.

        Args:
            updated_rule: Rule with updated information.

        """
        for i, rule in enumerate(self.rules):
            if rule.pylint_id == updated_rule.pylint_id:
                self.rules[i] = updated_rule
                return
        # If not found, add as new rule
        self.add_rule(updated_rule)

    def get_by_id(self, pylint_id: str) -> Rule | None:
        """Get rule by pylint ID.

        Args:
            pylint_id: The pylint rule ID to find.

        Returns:
            Rule if found, None otherwise.

        """
        for rule in self.rules:
            if rule.pylint_id == pylint_id:
                return rule
        return None

    def get_by_name(self, pylint_name: str) -> Rule | None:
        """Get rule by pylint name.

        Args:
            pylint_name: The pylint rule name to find.

        Returns:
            Rule if found, None otherwise.

        """
        for rule in self.rules:
            if rule.pylint_name == pylint_name:
                return rule
        return None

    def get_by_identifier(self, identifier: str) -> Rule | None:
        """Get rule by ID or name.

        Args:
            identifier: The pylint rule ID or name to find.

        Returns:
            Rule if found, None otherwise.

        """
        # Try by ID first
        rule = self.get_by_id(identifier)
        if rule:
            return rule
        # Try by name
        return self.get_by_name(identifier)

    def filter_implemented_in_ruff(self) -> Rules:
        """Get rules that are implemented in ruff.

        Returns:
            New Rules instance with only ruff-implemented rules.

        """
        filtered_rules = [r for r in self.rules if r.is_implemented_in_ruff]
        return Rules(rules=filtered_rules, metadata=self.metadata.copy())

    def filter_not_implemented_in_ruff(self) -> Rules:
        """Get rules that are NOT implemented in ruff.

        Returns:
            New Rules instance with only non-ruff-implemented rules.

        """
        filtered_rules = [r for r in self.rules if not r.is_implemented_in_ruff]
        return Rules(rules=filtered_rules, metadata=self.metadata.copy())

    def filter_mypy_overlap(self) -> Rules:
        """Get rules that overlap with mypy.

        Returns:
            New Rules instance with only mypy overlap rules.

        """
        filtered_rules = [r for r in self.rules if r.is_mypy_overlap]
        return Rules(rules=filtered_rules, metadata=self.metadata.copy())

    def filter_not_mypy_overlap(self) -> Rules:
        """Get rules that do NOT overlap with mypy.

        Returns:
            New Rules instance with only non-mypy overlap rules.

        """
        filtered_rules = [r for r in self.rules if not r.is_mypy_overlap]
        return Rules(rules=filtered_rules, metadata=self.metadata.copy())

    def filter_by_source(self, source: RuleSource) -> Rules:
        """Get rules from a specific source.

        Args:
            source: Source to filter by.

        Returns:
            New Rules instance with only rules from the specified source.

        """
        filtered_rules = [r for r in self.rules if r.source == source]
        return Rules(rules=filtered_rules, metadata=self.metadata.copy())

    def filter_by_category(self, category: str) -> Rules:
        """Get rules from a specific category.

        Args:
            category: Category to filter by (C/E/W/R/I/F).

        Returns:
            New Rules instance with only rules from the specified category.

        """
        filtered_rules = [r for r in self.rules if r.pylint_category == category]
        return Rules(rules=filtered_rules, metadata=self.metadata.copy())

    def get_optimized_disable_list(
        self,
        *,
        current_disabled: set[str],
        current_enabled: set[str],
        disable_mypy_overlap: bool = False,
    ) -> tuple[list[Rule], list[str]]:
        """Generate optimized disable list.

        Args:
            current_disabled: Set of currently disabled rule identifiers.
            current_enabled: Set of currently enabled rule identifiers.
            disable_mypy_overlap: If True, include mypy overlap rules.

        Returns:
            Tuple of (rules_to_disable, unknown_disabled_rules).

        """
        rules_to_disable = []
        unknown_disabled_rules = []

        for disabled_item in current_disabled:
            if disabled_item == "all":
                continue  # "all" is handled separately

            # Find the rule for this disabled item
            rule = self.get_by_identifier(disabled_item)

            if rule is None:
                # Unknown rule - keep it in disable list
                unknown_disabled_rules.append(disabled_item)
                continue

            # Check if this rule is explicitly enabled (takes precedence)
            explicitly_enabled = (
                rule.pylint_id in current_enabled or rule.pylint_name in current_enabled
            )

            # Check if rule should be kept disabled considering mypy overlap
            should_enable = not rule.is_implemented_in_ruff and (
                disable_mypy_overlap or not rule.is_mypy_overlap
            )

            if not explicitly_enabled and should_enable:
                # Keep disabled if it would otherwise be enabled
                rules_to_disable.append(rule)

        return rules_to_disable, unknown_disabled_rules

    def get_rules_to_enable(
        self,
        *,
        current_disabled: set[str],
        current_enabled: set[str],
        disable_mypy_overlap: bool = False,
    ) -> list[Rule]:
        """Generate list of rules to enable.

        Args:
            current_disabled: Set of currently disabled rule identifiers.
            current_enabled: Set of currently enabled rule identifiers.
            disable_mypy_overlap: If True, include mypy overlap rules.

        Returns:
            List of rules to enable.

        """
        rules_to_enable = []

        for rule in self.rules:
            # Check if rule should be enabled, considering mypy overlap flag
            should_enable = not rule.is_implemented_in_ruff and (
                disable_mypy_overlap or not rule.is_mypy_overlap
            )

            if not should_enable:
                continue

            # Check if rule is explicitly enabled (takes precedence over disable)
            explicitly_enabled = (
                rule.pylint_id in current_enabled or rule.pylint_name in current_enabled
            )

            # Check if rule is disabled (by ID or name)
            disabled_by_id = rule.pylint_id in current_disabled
            disabled_by_name = rule.pylint_name in current_disabled

            if explicitly_enabled or (not disabled_by_id and not disabled_by_name):
                # Enable if: explicitly enabled OR not disabled at all
                rules_to_enable.append(rule)

        return rules_to_enable

    def update_mypy_overlap_status(self, mypy_overlap_rules: set[str]) -> None:
        """Update mypy overlap status for all rules.

        Args:
            mypy_overlap_rules: Set of rule IDs that overlap with mypy.

        """
        for rule in self.rules:
            rule.is_mypy_overlap = rule.pylint_id in mypy_overlap_rules

    def get_statistics(self) -> dict[str, Any]:
        """Get comprehensive statistics about the rules.

        Returns:
            Dictionary with various statistics.

        """
        total_rules = len(self.rules)
        ruff_implemented = len(self.filter_implemented_in_ruff())
        mypy_overlap = len(self.filter_mypy_overlap())
        should_enable = len([r for r in self.rules if r.should_be_enabled_in_pylint()])

        # Count by category
        categories: dict[str, int] = {}
        for rule in self.rules:
            cat = rule.pylint_category
            categories[cat] = categories.get(cat, 0) + 1

        # Count by source
        sources: dict[str, int] = {}
        for rule in self.rules:
            source = rule.source.value
            sources[source] = sources.get(source, 0) + 1

        return {
            "total_rules": total_rules,
            "ruff_implemented": ruff_implemented,
            "mypy_overlap": mypy_overlap,
            "should_enable_in_pylint": should_enable,
            "categories": categories,
            "sources": sources,
            "ruff_coverage_percent": round((ruff_implemented / total_rules) * 100, 1)
            if total_rules
            else 0,
            "mypy_overlap_percent": round((mypy_overlap / total_rules) * 100, 1)
            if total_rules
            else 0,
        }

    def get_implementation_changes(
        self,
        *,
        old_rules: Rules,
    ) -> dict[str, set[str]]:
        """Get changes in rule implementation between two rule sets.

        Args:
            old_rules: Previous Rules state for comparison.

        Returns:
            Dictionary with 'added' and 'removed' sets of rule IDs.

        """
        old_implemented = set(old_rules.get_implemented_rule_codes())
        new_implemented = set(self.get_implemented_rule_codes())

        return {
            "added": new_implemented - old_implemented,
            "removed": old_implemented - new_implemented,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the rules collection.

        """
        return {
            "rules": [rule.to_dict() for rule in self.rules],
            "metadata": self.metadata.copy(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Rules:
        """Create Rules from dictionary.

        Args:
            data: Dictionary representation.

        Returns:
            Rules instance.

        """
        rules = [Rule.from_dict(rule_data) for rule_data in data.get("rules", [])]
        metadata = data.get("metadata", {})
        return cls(rules=rules, metadata=metadata)

    def save_to_cache(self, cache_path: Path) -> None:
        """Save rules to cache file.

        Args:
            cache_path: Path to cache file.

        """
        # Ensure cache directory exists
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        # Only include rules from pylint list or ruff issue, not user disable/unknown
        cache_rules = [
            rule
            for rule in self.rules
            if rule.source in (RuleSource.PYLINT_LIST, RuleSource.RUFF_ISSUE)
        ]

        cache_data = {
            "rules": [rule.to_dict() for rule in cache_rules],
            "metadata": self.metadata.copy(),
        }

        with cache_path.open("w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2, sort_keys=True)
            f.write("\n")  # Ensure trailing newline

    @classmethod
    def load_from_cache(cls, cache_path: Path) -> Rules | None:
        """Load rules from cache file.

        Args:
            cache_path: Path to cache file.

        Returns:
            Rules instance if successful, None otherwise.

        """
        if not cache_path.exists():
            return None

        try:
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except (json.JSONDecodeError, OSError, KeyError):
            return None

    def get_implemented_rule_codes(self) -> list[str]:
        """Get list of rule codes that are implemented in ruff.

        Returns:
            Sorted list of rule codes implemented in ruff.

        """
        return sorted(
            [rule.pylint_id for rule in self.rules if rule.is_implemented_in_ruff]
        )

    def __len__(self) -> int:
        """Return number of rules."""
        return len(self.rules)

    def __iter__(self) -> Iterator[Rule]:
        """Iterate over rules."""
        return iter(self.rules)

    def __bool__(self) -> bool:
        """Return True if rules exist."""
        return bool(self.rules)
