# GitHub Workflows for PMCGrab

This directory contains automated workflows for PMCGrab using GitHub Actions with uv.

## Workflows

### 🔄 CI (`ci.yml`)

**Triggers:** Push to main/develop, Pull Requests to main

**What it does:**

- Tests on multiple OS (Ubuntu, Windows, macOS) and Python versions (3.10-3.13)
- Runs linting with Ruff
- Performs type checking with MyPy
- Executes test suite with pytest
- Security scanning with Bandit and Safety
- Builds package artifacts
- Uploads coverage to Codecov

**Commands used:**

```bash
uv sync --dev --all-groups
uv run ruff check .
uv run mypy src/pmcgrab
uv run pytest --cov=pmcgrab
uv build
```

### 🚀 Release (`release.yml`)

**Triggers:** Git tags starting with 'v\*', Manual workflow dispatch

**What it does:**

- Runs full test suite
- Builds package with uv
- **Automatically publishes to PyPI** using your `PYPI_API_TOKEN`
- Creates GitHub release with changelog
- Includes installation instructions with uv

**Commands used:**

```bash
uv build
uv publish --token ${{ secrets.PYPI_API_TOKEN }}
```

### 🤖 Auto Release (`auto-release.yml`)

**Triggers:** Push to main when version changes in pyproject.toml

**What it does:**

- Detects version bumps automatically
- Creates git tags
- Triggers the release workflow
- **No manual intervention needed!**

### 📚 Documentation (`docs.yml`)

**Triggers:** Changes to docs/ or mkdocs.yml

**What it does:**

- Builds documentation with MkDocs
- Deploys to GitHub Pages automatically
- Uses uv for dependency management

**Commands used:**

```bash
uv sync --group docs
uv run mkdocs build
uv run mkdocs gh-deploy
```

## Automated Release Process

### Method 1: Version Bump (Recommended)

1. Update version in `pyproject.toml` and `src/pmcgrab/__init__.py`
2. Commit and push to main
3. **Auto-release workflow detects the change**
4. **Automatically creates tag and publishes to PyPI**

### Method 2: Manual Tag

1. Create and push a tag: `git tag v0.4.2 && git push origin v0.4.2`
2. **Release workflow triggers automatically**
3. **Publishes to PyPI**

### Method 3: Manual Workflow

1. Go to GitHub Actions → Release and Publish
2. Click "Run workflow"
3. Enter version number
4. **Publishes to PyPI**

## Environment Setup

### Required Secrets

Make sure these are set in your GitHub repository settings:

- `PYPI_API_TOKEN` - Your PyPI API token (already configured)
- `GITHUB_TOKEN` - Automatically provided by GitHub

### Repository Settings

- Enable GitHub Pages from Actions
- Allow GitHub Actions to create releases
- Enable Dependabot for automatic dependency updates

## Development Workflow

### For Contributors

1. Fork and clone the repository
2. Install dependencies: `uv sync --dev --all-groups`
3. Make changes
4. Run tests: `uv run pytest`
5. Check linting: `uv run ruff check .`
6. Format code: `uv run ruff format .`
7. Create pull request

### For Maintainers

1. Review and merge PRs
2. To release: bump version and push to main
3. **Everything else is automatic!**

## Workflow Status

All workflows use the modern uv package manager for:

- ✅ Faster dependency installation (10-100x faster than pip)
- ✅ Reproducible builds with uv.lock
- ✅ Simplified dependency management
- ✅ Cross-platform compatibility
- ✅ Automatic virtual environment handling

## Monitoring

- Check workflow runs in the Actions tab
- Monitor PyPI releases: https://pypi.org/project/pmcgrab/
- Documentation updates: https://rajdeepmondaldotcom.github.io/pmcgrab/
