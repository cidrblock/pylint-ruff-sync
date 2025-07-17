"""Tests for DataCollector class."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

from pylint_ruff_sync.data_collector import DataCollector
from pylint_ruff_sync.mypy_overlap import MypyOverlapExtractor
from pylint_ruff_sync.pylint_extractor import PylintExtractor
from pylint_ruff_sync.ruff_pylint_extractor import RuffPylintExtractor
from pylint_ruff_sync.rule import Rule, Rules, RuleSource
from pylint_ruff_sync.rules_cache_manager import RulesCacheManager

# Number of rules expected in the mock rules setup
EXPECTED_MOCK_RULES_COUNT = 5


class MockCompletedProcess:
    """Mock subprocess.CompletedProcess for testing."""

    def __init__(self, *, returncode: int = 0) -> None:
        """Initialize mock process.

        Args:
            returncode: Return code for the process.

        """
        self.returncode = returncode


def create_mock_rules() -> Rules:
    """Create a mock Rules object for testing.

    Returns:
        Rules object with test data.

    """
    rules = Rules()

    test_rules = [
        Rule(
            description="Invalid name",
            is_implemented_in_ruff=False,
            pylint_id="C0103",
            pylint_name="invalid-name",
            source=RuleSource.PYLINT_LIST,
        ),
        Rule(
            description="Unused argument",
            is_implemented_in_ruff=True,
            pylint_id="W0613",
            pylint_name="unused-argument",
            source=RuleSource.RUFF_ISSUE,
        ),
        Rule(
            description="Too few public methods",
            is_implemented_in_ruff=False,
            pylint_id="R0903",
            pylint_name="too-few-public-methods",
            source=RuleSource.PYLINT_LIST,
        ),
        Rule(
            description="No member",
            is_implemented_in_ruff=False,
            is_mypy_overlap=True,
            pylint_id="E1101",
            pylint_name="no-member",
            source=RuleSource.PYLINT_LIST,
        ),
        Rule(
            description="Unused import",
            is_implemented_in_ruff=True,
            pylint_id="F401",
            pylint_name="unused-import",
            source=RuleSource.RUFF_ISSUE,
        ),
    ]

    for rule in test_rules:
        rules.add_rule(rule=rule)

    return rules


def test_data_collector_init(*, tmp_path: Path) -> None:
    """Test DataCollector initialization.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    cache_path = tmp_path / "test_cache.json"
    cache_manager = RulesCacheManager(cache_path=cache_path)
    collector = DataCollector(cache_manager=cache_manager)
    assert collector.cache_manager == cache_manager


def test_is_github_cli_available_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test GitHub CLI availability check when successful.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Pytest temporary directory fixture.

    """
    mock_run = MockCompletedProcess(returncode=0)
    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: mock_run)

    cache_manager = RulesCacheManager(cache_path=tmp_path / "test.json")
    collector = DataCollector(cache_manager=cache_manager)
    assert collector._is_github_cli_available()


def test_is_github_cli_available_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test GitHub CLI availability check when failing.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Pytest temporary directory fixture.

    """
    mock_run = MockCompletedProcess(returncode=1)
    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: mock_run)

    cache_manager = RulesCacheManager(cache_path=tmp_path / "test.json")
    collector = DataCollector(cache_manager=cache_manager)
    assert not collector._is_github_cli_available()


def test_is_github_cli_available_not_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test GitHub CLI availability check when command not found.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Pytest temporary directory fixture.

    """

    def mock_run_raise(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", mock_run_raise)

    cache_manager = RulesCacheManager(cache_path=tmp_path / "test.json")
    collector = DataCollector(cache_manager=cache_manager)
    assert not collector._is_github_cli_available()


def test_is_pylint_available_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test pylint availability check when successful.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Pytest temporary directory fixture.

    """
    mock_run = MockCompletedProcess(returncode=0)
    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: mock_run)

    cache_manager = RulesCacheManager(cache_path=tmp_path / "test.json")
    collector = DataCollector(cache_manager=cache_manager)
    assert collector._is_pylint_available()


def test_is_pylint_available_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test pylint availability check when failing.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Pytest temporary directory fixture.

    """
    mock_run = MockCompletedProcess(returncode=1)
    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: mock_run)

    cache_manager = RulesCacheManager(cache_path=tmp_path / "test.json")
    collector = DataCollector(cache_manager=cache_manager)
    assert not collector._is_pylint_available()


def test_is_online_capable_both_available(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test online capability check when both tools are available.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Pytest temporary directory fixture.

    """
    cache_manager = RulesCacheManager(cache_path=tmp_path / "test.json")
    collector = DataCollector(cache_manager=cache_manager)

    monkeypatch.setattr(collector, "_is_github_cli_available", lambda: True)
    monkeypatch.setattr(collector, "_is_pylint_available", lambda: True)

    assert collector._is_online_capable()


def test_is_online_capable_partial_availability(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test online capability check when only one tool is available.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Pytest temporary directory fixture.

    """
    cache_manager = RulesCacheManager(cache_path=tmp_path / "test.json")
    collector = DataCollector(cache_manager=cache_manager)

    monkeypatch.setattr(collector, "_is_github_cli_available", lambda: True)
    monkeypatch.setattr(collector, "_is_pylint_available", lambda: False)

    assert not collector._is_online_capable()


def test_collect_fresh_rules(
    *, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test collecting fresh rules from extractors.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Pytest temporary directory fixture.

    """
    setup_extractor_mocks(monkeypatch=monkeypatch)

    cache_manager = RulesCacheManager(cache_path=tmp_path / "test.json")
    collector = DataCollector(cache_manager=cache_manager)
    rules = collector.collect_fresh_rules()

    assert isinstance(rules, Rules)
    assert len(rules.rules) == EXPECTED_MOCK_RULES_COUNT


def test_load_rules_from_cache_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test loading rules from cache when cache exists and is valid.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Pytest temporary directory fixture.

    """
    cache_manager = RulesCacheManager(cache_path=tmp_path / "test.json")
    collector = DataCollector(cache_manager=cache_manager)

    mock_rules = create_mock_rules()

    # Mock cache_manager.load_rules to return mock rules
    monkeypatch.setattr(cache_manager, "load_rules", lambda: mock_rules)

    rules = collector._load_rules_from_cache()

    assert rules == mock_rules


def test_load_rules_from_cache_file_not_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test loading rules from cache when cache file doesn't exist.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Pytest temporary directory fixture.

    """
    cache_manager = RulesCacheManager(cache_path=tmp_path / "test.json")
    collector = DataCollector(cache_manager=cache_manager)

    # Mock cache_manager.load_rules to raise FileNotFoundError
    def mock_load_raise() -> None:
        msg = "Cache file not found"
        raise FileNotFoundError(msg)

    monkeypatch.setattr(cache_manager, "load_rules", mock_load_raise)

    with pytest.raises(ValueError, match="Failed to load rules from cache"):
        collector._load_rules_from_cache()


def test_load_rules_from_cache_default_path(*, tmp_path: Path) -> None:
    """Test loading rules from cache using default cache path.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    cache_manager = RulesCacheManager(cache_path=tmp_path / "test.json")
    collector = DataCollector(cache_manager=cache_manager)

    mock_rules = create_mock_rules()

    # Mock the cache manager's save_rules method and then load_rules
    cache_manager.save_rules(rules=mock_rules)

    # Now test that we can load them back
    loaded_rules = collector._load_rules_from_cache()

    assert len(loaded_rules.rules) == len(mock_rules.rules)


def _create_mock_pylint_extract(
    *, mock_rules: Rules
) -> Callable[[PylintExtractor], None]:
    """Create mock pylint extractor function.

    Args:
        mock_rules: Mock rules to use for testing.

    Returns:
        Mock function for pylint extraction.

    """

    def mock_pylint_extract(self: PylintExtractor) -> None:
        """Mock pylint extractor.

        Args:
            self: PylintExtractor instance.

        """
        for rule in mock_rules.rules:
            if rule.source == RuleSource.PYLINT_LIST:
                self.rules.add_rule(rule=rule)

    return mock_pylint_extract


def _create_mock_ruff_extract(
    mock_rules: Rules,
) -> Callable[[RuffPylintExtractor], None]:
    """Create mock ruff extractor function.

    Args:
        mock_rules: Mock rules to use for testing.

    Returns:
        Mock function for ruff extraction.

    """

    def mock_ruff_extract(self: RuffPylintExtractor) -> None:
        """Mock ruff extractor.

        Args:
            self: RuffPylintExtractor instance.

        """
        for rule in mock_rules.rules:
            if rule.source == RuleSource.RUFF_ISSUE:
                # Find existing rule and update it, or add if new
                existing_rule = self.rules.get_by_id(pylint_id=rule.pylint_id)
                if existing_rule:
                    existing_rule.is_implemented_in_ruff = rule.is_implemented_in_ruff
                else:
                    self.rules.add_rule(rule=rule)

    return mock_ruff_extract


def _create_mock_mypy_extract() -> Callable[[MypyOverlapExtractor], None]:
    """Create mock mypy extractor function.

    Returns:
        Mock function for mypy extraction.

    """

    def mock_mypy_extract(self: MypyOverlapExtractor) -> None:
        """Mock mypy extractor.

        Args:
            self: MypyOverlapExtractor instance.

        """
        for rule in self.rules.rules:
            if rule.pylint_id in {"E1101"}:  # Example overlap rule
                rule.is_mypy_overlap = True

    return mock_mypy_extract


def setup_extractor_mocks(*, monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up mocks for extractor tests.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.

    """
    # Mock the extractor extract methods to populate with test data
    mock_rules = create_mock_rules()

    monkeypatch.setattr(
        PylintExtractor, "extract", _create_mock_pylint_extract(mock_rules=mock_rules)
    )
    monkeypatch.setattr(
        RuffPylintExtractor, "extract", _create_mock_ruff_extract(mock_rules)
    )
    monkeypatch.setattr(MypyOverlapExtractor, "extract", _create_mock_mypy_extract())


def test_collect_rules_online_capable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test collecting rules when online capable.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Pytest temporary directory fixture.

    """
    cache_manager = RulesCacheManager(cache_path=tmp_path / "test.json")
    collector = DataCollector(cache_manager=cache_manager)

    mock_rules = create_mock_rules()
    monkeypatch.setattr(collector, "_is_online_capable", lambda: True)
    monkeypatch.setattr(collector, "collect_fresh_rules", lambda: mock_rules)

    rules = collector.collect_rules()

    assert rules == mock_rules


def test_collect_rules_offline_fallback_to_cache(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test collecting rules when offline, falling back to cache.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Pytest temporary directory fixture.

    """
    cache_manager = RulesCacheManager(cache_path=tmp_path / "test.json")
    collector = DataCollector(cache_manager=cache_manager)

    mock_rules = create_mock_rules()
    monkeypatch.setattr(collector, "_is_online_capable", lambda: False)
    monkeypatch.setattr(collector, "_load_rules_from_cache", lambda: mock_rules)

    rules = collector.collect_rules()

    assert rules == mock_rules


def test_collect_rules_online_fails_fallback_to_cache(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test collecting rules when online extraction fails, fallback to cache.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Pytest temporary directory fixture.

    """
    cache_manager = RulesCacheManager(cache_path=tmp_path / "test.json")
    collector = DataCollector(cache_manager=cache_manager)

    mock_rules = create_mock_rules()

    def mock_collect_fresh_rules_raise() -> None:
        msg = "Network error"
        raise ValueError(msg)

    monkeypatch.setattr(collector, "_is_online_capable", lambda: True)
    monkeypatch.setattr(
        collector, "collect_fresh_rules", mock_collect_fresh_rules_raise
    )
    monkeypatch.setattr(collector, "_load_rules_from_cache", lambda: mock_rules)

    rules = collector.collect_rules()

    assert rules == mock_rules


def test_collect_rules_both_fail(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test collecting rules when both online and cache fail.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.
        tmp_path: Pytest temporary directory fixture.

    """
    cache_manager = RulesCacheManager(cache_path=tmp_path / "test.json")
    collector = DataCollector(cache_manager=cache_manager)

    def mock_collect_fresh_rules_raise() -> None:
        msg = "Network error"
        raise ValueError(msg)

    def mock_load_rules_from_cache_raise() -> None:
        msg = "Cache error"
        raise ValueError(msg)

    monkeypatch.setattr(collector, "_is_online_capable", lambda: True)
    monkeypatch.setattr(
        collector, "collect_fresh_rules", mock_collect_fresh_rules_raise
    )
    monkeypatch.setattr(
        collector, "_load_rules_from_cache", mock_load_rules_from_cache_raise
    )

    with pytest.raises(ValueError, match="Cache error"):
        collector.collect_rules()
