# Development Guide

This document provides information on how to develop and contribute to pmcgrab.

## Prerequisites

- Python 3.9+
- [uv](https://docs.astral.sh/uv/) package manager

## Installation for Development

1. Clone the repository:
```bash
git clone https://github.com/rajdeepmondal/pmcgrab.git
cd pmcgrab
```

2. Install dependencies with uv:
```bash
uv sync --all-extras
```

This will create a virtual environment and install all dependencies including development tools.

## Development Workflow

### Code Quality

The project uses several tools to ensure code quality:

- **ruff**: For linting and formatting
- **mypy**: For type checking
- **pytest**: For testing
- **pre-commit**: For git hooks

### Running Tests

```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=pmcgrab

# Run tests in parallel
uv run pytest -n auto
```

### Code Formatting and Linting

```bash
# Format code
uv run ruff format

# Check for linting issues
uv run ruff check

# Fix auto-fixable linting issues
uv run ruff check --fix
```

### Type Checking

```bash
uv run mypy src/pmcgrab
```

### Pre-commit Hooks

Install pre-commit hooks to automatically run checks before commits:

```bash
uv run pre-commit install
```

## Project Structure

```
pmcgrab/
├── .github/workflows/     # GitHub Actions CI/CD
├── docs/                  # Documentation
├── src/pmcgrab/          # Source code
│   ├── __init__.py
│   ├── constants.py
│   ├── fetch.py
│   ├── model.py
│   ├── parser.py
│   ├── processing.py
│   ├── utils.py
│   └── data/             # Data files (DTDs, etc.)
├── tests/                # Test files
├── pyproject.toml        # Project configuration
├── .pre-commit-config.yaml
├── .gitignore
└── README.md
```

## Using uv with pmcgrab

### Installing from Local Development

```bash
# Install in development mode
uv pip install -e .

# Or install with extras
uv pip install -e ".[dev,docs,test]"
```

### Adding Dependencies

```bash
# Add a runtime dependency
uv add requests

# Add a development dependency
uv add --dev pytest-mock

# Add an optional dependency
uv add --optional docs mkdocs
```

### Managing Python Versions

```bash
# Install a specific Python version
uv python install 3.11

# Use a specific Python version for the project
uv python pin 3.11
```

### Virtual Environment Management

```bash
# Activate the virtual environment
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows

# Deactivate
deactivate
```

## Building and Publishing

### Building the Package

```bash
uv build
```

This creates distributions in the `dist/` directory.

### Publishing to PyPI

```bash
# Build first
uv build

# Publish (requires API token)
uv publish
```

## Configuration Files

### pyproject.toml

The main configuration file containing:
- Project metadata
- Dependencies
- Build configuration
- Tool configurations (ruff, pytest, mypy, etc.)

### .pre-commit-config.yaml

Configures pre-commit hooks for:
- Code formatting with ruff
- Linting with ruff
- Type checking with mypy
- Various file checks

## Continuous Integration

The project uses GitHub Actions for CI/CD:

- **ci.yml**: Runs tests, linting, and type checking on multiple Python versions
- **release.yml**: Builds and publishes to PyPI on releases

## Best Practices

1. **Code Style**: Follow PEP 8 and use type hints
2. **Testing**: Write tests for new features and bug fixes
3. **Documentation**: Update documentation for user-facing changes
4. **Dependencies**: Keep dependencies minimal and up-to-date
5. **Commits**: Use conventional commit messages
6. **Versioning**: Follow semantic versioning

## Troubleshooting

### Common Issues

1. **Import errors**: Make sure you've run `uv sync` to install dependencies
2. **Test failures**: Check if you have the required test data and network access
3. **Linting errors**: Run `uv run ruff check --fix` to auto-fix issues

### Getting Help

- Check the [Issues](https://github.com/rajdeepmondal/pmcgrab/issues) page
- Review the documentation in README.md
- Look at existing tests for examples