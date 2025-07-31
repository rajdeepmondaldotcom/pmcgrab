# Development Setup

Complete guide for setting up PMCGrab for development.

## Prerequisites

- Python 3.10+
- Git
- uv (recommended) or pip

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/rajdeepmondaldotcom/pmcgrab.git
cd pmcgrab
```

### 2. Set Up Virtual Environment

#### Using uv (Recommended)

```bash
uv sync --dev
```

#### Using pip

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

### 3. Verify Installation

```bash
uv run python -c "import pmcgrab; print(pmcgrab.__version__)"
uv run pytest --version
```

## Development Tools

### Code Quality

```bash
# Linting
uv run ruff check .

# Formatting
uv run ruff format .

# Type checking
uv run mypy src/

# Security scanning
uv run bandit -r src/
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=pmcgrab

# Run specific test file
uv run pytest tests/test_model.py
```

### Documentation

```bash
# Build documentation
uv run mkdocs serve

# View at http://localhost:8000
```

## Pre-commit Hooks

Install pre-commit hooks:

```bash
uv run pre-commit install
```

This will run checks automatically before each commit.

## Environment Variables

For development, create a `.env` file:

```bash
PMCGRAB_EMAIL=your-dev-email@example.com
PMCGRAB_DEBUG=true
```

## IDE Setup

### VS Code

Recommended extensions:

- Python
- Pylance
- Ruff
- Test Explorer UI

Workspace settings in `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.linting.enabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true
}
```

### PyCharm

1. Open project in PyCharm
2. Configure Python interpreter to use virtual environment
3. Enable pytest as test runner
4. Configure Ruff as code formatter

## Common Development Tasks

### Adding a New Feature

1. Create feature branch
2. Add implementation in `src/pmcgrab/`
3. Add tests in `tests/`
4. Update documentation
5. Run all checks
6. Submit pull request

### Debugging

```bash
# Enable verbose logging
export PMCGRAB_LOG_LEVEL=DEBUG

# Run with debugger
uv run python -m pdb -c continue -m pmcgrab.cli.pmcgrab_cli --help
```

### Performance Profiling

```bash
# Profile code
uv run python -m cProfile -o profile.stats script.py

# Analyze results
uv run python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(20)"
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure virtual environment is activated
2. **Test failures**: Check if all dependencies are installed
3. **Linting errors**: Run `uv run ruff format .` to auto-fix

### Getting Help

- Check existing issues on GitHub
- Ask questions in discussions
- Join our development chat (if available)
