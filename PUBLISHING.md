# Publishing Guide for pylint-ruff-sync

This guide explains how to publish the `pylint-ruff-sync` package so it can be used by many projects as referenced in the [Medium article](https://medium.com/data-science/custom-pre-commit-hooks-for-safer-code-changes-d8b8aa1b2ebb).

## Overview

The package is structured as a proper Python package with:
- A main module (`pylint_ruff_sync/main.py`)
- A console script entry point (`pylint-ruff-sync`)
- Pre-commit hook configuration (`.pre-commit-hooks.yaml`)
- Dependencies managed via `pyproject.toml`

## Prerequisites

1. **GitHub Repository**: Create a public repository for the package
2. **PyPI Account**: Register at https://pypi.org (optional, for PyPI distribution)
3. **API Tokens**: Generate PyPI API token if publishing to PyPI

## Publishing Steps

### 1. Prepare the Repository

```bash
# Create a new repository on GitHub
gh repo create your-org/pylint-ruff-sync --public

# Clone and push the code
git clone https://github.com/your-org/pylint-ruff-sync.git
cd pylint-ruff-sync

# Copy all files from this project
cp -r . /path/to/pylint-ruff-sync/

# Initial commit
git add .
git commit -m "Initial release of pylint-ruff-sync precommit hook"
git push origin main
```

### 2. Update URLs in Configuration

Update the repository URLs in:

1. **`.pre-commit-config.yaml`**:
   ```yaml
   repos:
     - repo: https://github.com/your-org/pylint-ruff-sync
       rev: v0.1.0
   ```

2. **`README.md`**: Update all example URLs to point to your repository

3. **`example_integration.md`**: Update the repository URL

### 3. Version Management

Update the version in `pylint_ruff_sync/__init__.py`:

```python
__version__ = "0.1.0"  # Update as needed
```

### 4. Testing Before Release

Test the package locally:

```bash
# Install in development mode
pip install -e .

# Test the command
pylint-ruff-sync --help
pylint-ruff-sync --dry-run --verbose

# Test as a precommit hook
pre-commit try-repo . --all-files
```

### 5. Create a Release

#### Option A: GitHub Releases Only (Recommended)

```bash
# Create and push a tag
git tag v0.1.0
git push origin v0.1.0

# Create release on GitHub
gh release create v0.1.0 \
  --title "Release v0.1.0" \
  --notes "Initial release of pylint-ruff-sync precommit hook"
```

#### Option B: PyPI + GitHub Releases

If you want to publish to PyPI as well:

```bash
# Install build tools
pip install build twine

# Build the package
python -m build

# Upload to PyPI (requires API token)
twine upload dist/*

# Create GitHub release
gh release create v0.1.0 \
  --title "Release v0.1.0" \
  --notes "Initial release of pylint-ruff-sync precommit hook"
```

### 6. Set up Automated Releases (Optional)

The included `.github/workflows/release.yml` provides automated releases:

1. **Add PyPI API Token**: Go to repository settings → Secrets → Add `PYPI_API_TOKEN`
2. **Create a tag**: `git tag v0.1.1 && git push origin v0.1.1`
3. **Automatic release**: The workflow will build and publish automatically

## Using the Published Hook

Once published, projects can use the hook by adding to their `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/your-org/pylint-ruff-sync
    rev: v0.1.0  # Use the latest version
    hooks:
      - id: pylint-ruff-sync
```

## Version Updates

When updating the hook:

1. **Update the version** in `pylint_ruff_sync/__init__.py`
2. **Commit changes**: `git commit -m "Bump version to v0.1.1"`
3. **Create new tag**: `git tag v0.1.1 && git push origin v0.1.1`
4. **Users update their rev**: Projects using the hook update their `rev` field

## Key Benefits of This Approach

1. **No Script Copying**: Projects don't need to copy scripts or manage dependencies
2. **Automatic Updates**: Projects can easily update by changing the `rev` field
3. **Dependency Management**: All dependencies are handled by the package
4. **Standardized**: Follows pre-commit hook best practices
5. **Maintainable**: Single source of truth for the hook logic

## Distribution Channels

### 1. GitHub Releases (Primary)

- **Pros**: Easy to set up, works with pre-commit, version controlled
- **Cons**: Requires GitHub access
- **Best for**: Open source projects, internal tools

### 2. PyPI (Optional)

- **Pros**: Searchable, pip-installable, professional
- **Cons**: Requires PyPI account, more complex setup
- **Best for**: Public tools, when you want pip installation

### 3. Private Git Repositories

For private/internal use:

```yaml
repos:
  - repo: https://github.com/your-private-org/pylint-ruff-sync
    rev: v0.1.0
    hooks:
      - id: pylint-ruff-sync
```

## Example Projects Using the Hook

After publishing, projects can integrate the hook in seconds:

**ansible-creator project**:
```yaml
repos:
  - repo: https://github.com/your-org/pylint-ruff-sync
    rev: v0.1.0
    hooks:
      - id: pylint-ruff-sync
  
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
      - id: ruff-format
```

**Any Python project**:
```yaml
repos:
  - repo: https://github.com/your-org/pylint-ruff-sync
    rev: v0.1.0
    hooks:
      - id: pylint-ruff-sync
```

## Maintenance

### Regular Updates

1. **Monitor ruff releases**: Check when new pylint rules are implemented
2. **Update dependencies**: Keep dependencies current
3. **Test with new Python versions**: Ensure compatibility
4. **Update documentation**: Keep examples current

### User Support

1. **GitHub Issues**: Enable issues for bug reports and feature requests
2. **Documentation**: Keep README.md and examples up-to-date
3. **Changelog**: Document changes in releases

## Security Considerations

1. **GitHub Actions**: Use trusted actions and pin versions
2. **API Tokens**: Use repository secrets for sensitive data
3. **Dependencies**: Keep dependencies updated for security patches
4. **Code Review**: Review changes before releasing

## Success Metrics

Track adoption through:
- GitHub repository stars/forks
- PyPI download statistics (if using PyPI)
- GitHub issue reports and feature requests
- Community contributions

This publishing approach makes the hook reusable across many projects while maintaining a single source of truth for the logic and dependencies. 