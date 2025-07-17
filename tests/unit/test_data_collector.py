"""Test module for DataCollector functionality."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from pylint_ruff_sync.data_collector import DataCollector
from pylint_ruff_sync.rule import Rule, Rules, RuleSource
from tests.constants import setup_mocks

# Test constants
EXPECTED_MOCK_RULES_COUNT = 2


def create_mock_rules() -> Rules:
    """Create a mock Rules object for testing.

    Returns:
        Rules object with test data.

    """
    rules = Rules()
    rules.add_rule(
        Rule(
            pylint_id="C0103",
            pylint_name="invalid-name",
            description="Test rule 1",
            source=RuleSource.PYLINT_LIST,
        )
    )
    rules.add_rule(
        Rule(
            pylint_id="W0613",
            pylint_name="unused-argument",
            description="Test rule 2",
            source=RuleSource.PYLINT_LIST,
            is_implemented_in_ruff=True,
            ruff_rule="ARG001",
        )
    )
    return rules


def test_data_collector_init() -> None:
    """Test DataCollector initialization."""
    collector = DataCollector()
    assert collector.cache_path is None

    cache_path = Path("/tmp/test.json")  # noqa: S108
    collector = DataCollector(cache_path=cache_path)
    assert collector.cache_path == cache_path


def test_is_github_cli_available_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test GitHub CLI availability check when successful.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.

    """
    mock_run = Mock()
    mock_run.returncode = 0
    monkeypatch.setattr(subprocess, "run", Mock(return_value=mock_run))

    collector = DataCollector()
    assert collector._is_github_cli_available() is True


def test_is_github_cli_available_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test GitHub CLI availability check when failing.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.

    """
    mock_run = Mock()
    mock_run.returncode = 1
    monkeypatch.setattr(subprocess, "run", Mock(return_value=mock_run))

    collector = DataCollector()
    assert collector._is_github_cli_available() is False


def test_is_github_cli_available_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test GitHub CLI availability check when command not found.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.

    """
    monkeypatch.setattr(subprocess, "run", Mock(side_effect=FileNotFoundError))

    collector = DataCollector()
    assert collector._is_github_cli_available() is False


def test_is_pylint_available_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test pylint availability check when successful.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.

    """
    mock_run = Mock()
    mock_run.returncode = 0
    monkeypatch.setattr(subprocess, "run", Mock(return_value=mock_run))

    collector = DataCollector()
    assert collector._is_pylint_available() is True


def test_is_pylint_available_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test pylint availability check when failing.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.

    """
    mock_run = Mock()
    mock_run.returncode = 1
    monkeypatch.setattr(subprocess, "run", Mock(return_value=mock_run))

    collector = DataCollector()
    assert collector._is_pylint_available() is False


def test_is_online_capable_both_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test online capability check when both tools are available.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.

    """
    collector = DataCollector()
    monkeypatch.setattr(collector, "_is_github_cli_available", Mock(return_value=True))
    monkeypatch.setattr(collector, "_is_pylint_available", Mock(return_value=True))

    assert collector._is_online_capable() is True


def test_is_online_capable_partial_availability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test online capability check when only one tool is available.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.

    """
    collector = DataCollector()
    monkeypatch.setattr(collector, "_is_github_cli_available", Mock(return_value=True))
    monkeypatch.setattr(collector, "_is_pylint_available", Mock(return_value=False))

    assert collector._is_online_capable() is False


def test_collect_fresh_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test collecting fresh rules from extractors.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.

    """
    setup_mocks(monkeypatch)

    collector = DataCollector()
    rules = collector.collect_fresh_rules()

    assert isinstance(rules, Rules)
    assert len(rules) > 0


def test_load_rules_from_cache_success() -> None:
    """Test loading rules from cache successfully."""
    rules = create_mock_rules()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        cache_path = Path(tmp.name)
        rules.save_to_cache(cache_path)

    try:
        collector = DataCollector(cache_path=cache_path)
        loaded_rules = collector._load_rules_from_cache()

        assert isinstance(loaded_rules, Rules)
        assert len(loaded_rules) == EXPECTED_MOCK_RULES_COUNT
    finally:
        cache_path.unlink()


def test_load_rules_from_cache_file_not_found() -> None:
    """Test loading rules from cache when file doesn't exist."""
    collector = DataCollector(cache_path=Path("/nonexistent/path.json"))

    with pytest.raises(ValueError, match="Failed to load rules from cache"):
        collector._load_rules_from_cache()


def test_load_rules_from_cache_default_path() -> None:
    """Test loading rules from cache with default path."""
    # Create a mock cache file at the default location
    collector = DataCollector()
    default_cache_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "pylint_ruff_sync"
        / "data"
        / "ruff_implemented_rules.json"
    )

    # This should work with the actual package data file or fail gracefully
    if default_cache_path.exists():
        loaded_rules = collector._load_rules_from_cache()
        assert isinstance(loaded_rules, Rules)
    else:
        with pytest.raises(ValueError, match="Failed to load rules from cache"):
            collector._load_rules_from_cache()


def test_collect_rules_online_capable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test collecting rules when online capable.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.

    """
    collector = DataCollector()

    mock_rules = create_mock_rules()
    monkeypatch.setattr(collector, "_is_online_capable", Mock(return_value=True))
    monkeypatch.setattr(collector, "collect_fresh_rules", Mock(return_value=mock_rules))

    rules = collector.collect_rules()

    assert rules == mock_rules


def test_collect_rules_offline_fallback_to_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test collecting rules when offline, falling back to cache.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.

    """
    collector = DataCollector()

    mock_rules = create_mock_rules()
    monkeypatch.setattr(collector, "_is_online_capable", Mock(return_value=False))
    monkeypatch.setattr(
        collector, "_load_rules_from_cache", Mock(return_value=mock_rules)
    )

    rules = collector.collect_rules()

    assert rules == mock_rules


def test_collect_rules_online_fails_fallback_to_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test collecting rules when online extraction fails, fallback to cache.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.

    """
    collector = DataCollector()

    mock_rules = create_mock_rules()
    monkeypatch.setattr(collector, "_is_online_capable", Mock(return_value=True))
    monkeypatch.setattr(
        collector, "collect_fresh_rules", Mock(side_effect=ValueError("Network error"))
    )
    monkeypatch.setattr(
        collector, "_load_rules_from_cache", Mock(return_value=mock_rules)
    )

    rules = collector.collect_rules()

    assert rules == mock_rules


def test_collect_rules_both_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test collecting rules when both online and cache fail.

    Args:
        monkeypatch: Pytest monkeypatch fixture for mocking.

    """
    collector = DataCollector()

    monkeypatch.setattr(collector, "_is_online_capable", Mock(return_value=True))
    monkeypatch.setattr(
        collector, "collect_fresh_rules", Mock(side_effect=ValueError("Network error"))
    )
    monkeypatch.setattr(
        collector, "_load_rules_from_cache", Mock(side_effect=ValueError("Cache error"))
    )

    with pytest.raises(ValueError, match="Cache error"):
        collector.collect_rules()
