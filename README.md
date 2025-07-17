# Pylint-Ruff Sync

> **CAUTION: This project needs a maintainer!**
>
> This repository was created as a proof-of-concept and demonstration project. **Do not use this repository directly** as it may be removed or archived without notice.
>
> If you're interested in using this tool:
>
> - **Fork this repository** to create your own maintained version
> - **Consider becoming the maintainer** by reaching out to [@cidrblock](https://github.com/cidrblock)
> - **Check for community forks** that may have active maintenance
>
> This codebase includes comprehensive tests and documentation, but requires ongoing maintenance for GitHub API changes, ruff updates, and dependency management.

A precommit hook that automatically synchronizes your `pyproject.toml` pylint configuration with ruff's implementation status. This tool eliminates rule duplication between pylint and ruff by maintaining an optimal configuration that leverages the strengths of both tools.

## Core Functionality

This tool performs two primary operations:

1. **Configuration Synchronization**: Updates `pyproject.toml` to enable only pylint rules not implemented in ruff
2. **Code Cleanup**: Removes unnecessary pylint disable comments from your codebase

The configuration is automatically synchronized based on real-time data from the [ruff pylint implementation tracking issue](https://github.com/astral-sh/ruff/issues/970), ensuring your setup remains current as ruff evolves.

## Pylint Command and Configuration

### Command Execution

The tool runs pylint with the following command to detect unnecessary disable comments:

```bash
pylint --output-format=parseable --enable=useless-suppression --rcfile {config_file} $(git ls-files '*.py')
```

This command:

- Uses your existing pylint configuration file (`--rcfile`) with all your normal rules
- Enables useless-suppression detection (`--enable=useless-suppression`) in addition to your config
- Only checks Python files tracked by git (`git ls-files '*.py'`)
- Outputs results in parseable format for processing

**Important**: The `useless-suppression` check must run with your normal pylint configuration to properly detect which disable comments are actually unnecessary. If we disabled all other rules, every disable comment would appear useless.

### Configuration Requirements

**All pylint configuration must be in your config file** (typically `pyproject.toml`). The tool does not modify pylint's behavior beyond updating the `disable` and `enable` lists in your configuration file. Settings like:

- Line length limits
- Naming conventions
- Plugin configurations
- Custom rule settings
- Output formats

Should all be configured in your `[tool.pylint]` sections in `pyproject.toml`.

## Key Features

### Configuration Management

- **Always Current**: References live GitHub issue data for accurate rule status
- **Enable-Only Strategy**: Maintains shorter, more manageable rule lists that shrink over time
- **Format Preservation**: Preserves existing formatting, comments, and custom configurations
- **Mypy Integration**: Optionally excludes rules that overlap with mypy functionality

### Code Cleanup (PylintCleaner)

- **Comment Removal**: Identifies and removes unnecessary pylint disable comments
- **Multi-Format Support**: Handles various pylint disable comment patterns
- **Tool Preservation**: Maintains comments for other tools (noqa, type: ignore, etc.)
- **Selective Removal**: Removes only unnecessary rules while preserving necessary ones

### Operational Features

- **Error Handling**: Graceful fallback to cached data when network unavailable
- **Logging**: Detailed operation reporting for debugging and monitoring
- **Type Safety**: Full type annotations throughout codebase
- **CI/CD Ready**: Designed for automated pipeline integration

## Installation

```bash
pip install pylint-ruff-sync
```

Or add to your precommit configuration:

```yaml
repos:
  - repo: https://github.com/your-org/pylint-ruff-sync
    rev: v1.0.0
    hooks:
      - id: pylint-ruff-sync
```

## Usage

### Basic Operation

```bash
# Update configuration with current ruff implementation status
pylint-ruff-sync

# Preview changes without modifying files
pylint-ruff-sync --dry-run

# Update specific configuration file
pylint-ruff-sync --config-file path/to/pyproject.toml

# Disable automatic pylint comment cleanup
pylint-ruff-sync --disable-pylint-cleaner
```

### Advanced Options

```bash
# Enable verbose logging for debugging
pylint-ruff-sync --verbose

# Include rules that overlap with mypy
pylint-ruff-sync --disable-mypy-overlap

# Update local cache from GitHub
pylint-ruff-sync --update-cache

# Use custom cache location
pylint-ruff-sync --cache-path /custom/cache/path.json
```

## PylintCleaner: Automated Comment Cleanup

The PylintCleaner component automatically removes unnecessary pylint disable comments after updating your configuration. This feature:

### Detection Process

1. Runs pylint with `useless-suppression` enabled to identify unnecessary disables
2. Parses various pylint disable comment formats
3. Determines which specific rules are no longer needed

### Supported Comment Formats

```python
# Single rule disable
x = eval("1 + 2")  # pylint: disable=eval-used

# Multiple rules
def foo(bar):  # pylint: disable=unused-argument,missing-function-docstring

# Mixed with other tools
z = eval("5 + 6")  # noqa: E501  # pylint: disable=eval-used

# File-level disables
# pylint: skip-file

# Code and name formats
y = eval("3 + 4")  # pylint: disable=W0123
```

### Processing Behavior

- **Partial Removal**: Removes only unnecessary rules while preserving necessary ones
- **Tool Preservation**: Maintains comments for ruff, mypy, type checkers, etc.
- **Format Preservation**: Maintains original comment structure and spacing
- **Testing**: Includes test coverage for comment processing functionality

### Configuration

PylintCleaner is enabled by default but can be controlled:

```bash
# Disable cleaner functionality
pylint-ruff-sync --disable-pylint-cleaner

# Preview cleaner actions in dry-run mode
pylint-ruff-sync --dry-run  # Shows both config and cleaner changes
```

## Configuration Examples

### Before Synchronization

```toml
[tool.pylint.messages_control]
disable = [
  "C0103",  # invalid-name (implemented in ruff)
  "W0613",  # unused-argument (implemented in ruff)
  "C0116",  # missing-function-docstring (not in ruff)
]
```

### After Synchronization

```toml
[tool.pylint.messages_control]
disable = ["all"]
enable = [
  "C0116",  # https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/missing-function-docstring.html
]
```

## Technical Architecture

### Data Collection Pipeline

```
pylint --list-msgs → GitHub Issue Parsing → Mypy Overlap Analysis → Rule Synchronization
```

### Components

- **PylintExtractor**: Extracts available rules from pylint installation
- **RuffPylintExtractor**: Parses ruff implementation status from GitHub
- **MypyOverlapExtractor**: Identifies rules that overlap with mypy
- **PyprojectUpdater**: Manages TOML configuration updates
- **PylintCleaner**: Removes unnecessary disable comments
- **TomlFile/TomlRegex**: TOML editing with format preservation

### Caching Strategy

- Local cache for offline operation
- Automatic fallback when network unavailable
- Configurable cache paths for CI/CD environments
- GitHub CLI integration for authenticated access

## Network and Authentication

### GitHub Access

- **Preferred**: GitHub CLI (`gh`) for authenticated access
- **Fallback**: Public API access (rate-limited)
- **Offline**: Local cache for continued operation

### Requirements

- **Network**: Internet connection for live data updates
- **Authentication**: None required (reads public issue data)
- **Fallback**: Cached data enables offline operation

## Integration Patterns

### Precommit Hook

```yaml
repos:
  - repo: https://github.com/your-org/pylint-ruff-sync
    rev: v1.0.0
    hooks:
      - id: pylint-ruff-sync
        args: ["--config-file", "pyproject.toml"]
```

### CI/CD Pipeline

```yaml
- name: Sync Pylint Configuration
  run: |
    pylint-ruff-sync --verbose
    git diff --exit-code pyproject.toml || {
      echo "Configuration updated - review changes"
      exit 1
    }
```

### Development Workflow

```bash
# Daily development
pylint-ruff-sync

# Before releases
pylint-ruff-sync --update-cache --verbose

# Debugging
pylint-ruff-sync --dry-run --verbose
```

## Performance Characteristics

### Execution Time

- **Cached Operation**: < 1 second
- **Network Update**: 2-5 seconds
- **Comment Cleanup**: Variable based on codebase size

### Resource Usage

- **Memory**: Minimal (processes TOML and rule data)
- **Network**: Single GitHub API call when updating
- **Disk**: Small cache file (typically < 100KB)

## Error Handling and Reliability

### Graceful Degradation

- Network failures fall back to cached data
- Malformed TOML preserves original files
- GitHub API rate limits trigger cache usage
- Missing dependencies skip optional features

### Validation

- TOML syntax validation before writing
- Rule identifier validation against known pylint rules
- Backup creation for critical operations
- Comprehensive test coverage (>95%)

## Development and Contribution

### Code Quality Standards

- **Type Safety**: Full mypy compliance
- **Testing**: Comprehensive unit and integration tests
- **Documentation**: Complete docstring coverage
- **Code Style**: Black, ruff, and pylint compliance

### Architecture Principles

- **Single Responsibility**: Each class has one clear purpose
- **Dependency Injection**: Configurable components for testing
- **Error Isolation**: Failures in one component don't affect others
- **Immutable Operations**: No unexpected side effects

## License and Attribution

This project was developed through collaborative human-AI pair programming between [Bradley Thornton (cidrblock)](https://github.com/cidrblock) and Claude 4 Sonnet AI.

Licensed under the MIT License. See LICENSE file for details.
