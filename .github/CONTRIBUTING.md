# Contributing to pmcgrab

Thank you for your interest in contributing to pmcgrab! This document provides guidelines and information for contributors.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct (to be added).

## Getting Started

### Prerequisites

- Python 3.9 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- Git

### Development Setup

1. Fork the repository on GitHub
2. Clone your fork locally:

   ```bash
   git clone https://github.com/your-username/pmcgrab.git
   cd pmcgrab
   ```

3. Install development dependencies:

   ```bash
   uv sync --all-groups
   ```

4. Install pre-commit hooks:

   ```bash
   uv run pre-commit install
   ```

5. Create a branch for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

### Running Tests

```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=pmcgrab

# Run tests for specific Python versions
uv run tox
```

### Code Quality

We use several tools to maintain code quality:

```bash
# Linting
uv run ruff check .

# Formatting
uv run ruff format .

# Type checking
uv run mypy src/pmcgrab

# Security scanning
uv run bandit -r src/
```

### Building Documentation

```bash
# Install docs dependencies
uv sync --group docs

# Serve docs locally
uv run mkdocs serve

# Build docs
uv run mkdocs build
```

## Contribution Guidelines

### Pull Request Process

1. **Create an Issue**: For significant changes, create an issue first to discuss the proposed changes.

2. **Branch Naming**: Use descriptive branch names:
   - `feature/add-new-parser`
   - `bugfix/fix-xml-parsing`
   - `docs/update-readme`

3. **Commit Messages**: Follow conventional commit format:
   - `feat: add new XML validation feature`
   - `fix: resolve memory leak in batch processing`
   - `docs: update API documentation`
   - `test: add tests for error handling`

4. **Pull Request Requirements**:
   - All tests must pass
   - Code coverage should not decrease
   - Include tests for new functionality
   - Update documentation as needed
   - Fill out the PR template completely

5. **Review Process**:
   - At least one maintainer review is required
   - Address all review comments
   - Ensure CI passes

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for all public functions
- Write docstrings for all public classes and functions
- Keep functions focused and small
- Use descriptive variable and function names

### Testing

- Write tests for all new functionality
- Use pytest for testing framework
- Aim for high test coverage (>90%)
- Include both unit tests and integration tests
- Test edge cases and error conditions

### Documentation

- Update README.md for user-facing changes
- Add docstrings to all public APIs
- Include examples in docstrings
- Update API documentation as needed

## Types of Contributions

### Bug Reports

When filing bug reports, please include:

- pmcgrab version
- Python version
- Operating system
- Minimal reproduction case
- Expected vs actual behavior
- Full error traceback

### Feature Requests

For feature requests, please provide:

- Clear description of the problem
- Proposed solution
- Use cases and examples
- Consideration of alternatives

### Code Contributions

We welcome contributions for:

- Bug fixes
- New features
- Performance improvements
- Documentation improvements
- Test coverage improvements

## Release Process

Releases are automated:

1. Version is bumped in `pyproject.toml`
2. Changes are merged to `main`
3. GitHub release is created automatically
4. Package is published to PyPI automatically

## Getting Help

- Check existing issues and discussions
- Join our community discussions
- Reach out to maintainers

## Recognition

Contributors will be recognized in:

- CHANGELOG.md
- GitHub contributors page
- Release notes

Thank you for contributing to pmcgrab!
