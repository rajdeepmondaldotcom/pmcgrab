#!/bin/bash
set -e

echo "Setting up pmcgrab development environment..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
uv sync

# Install development dependencies
echo "Installing development tools..."
uv add --group dev pytest pytest-cov pytest-xdist ruff mypy bandit safety pre-commit pydocstyle commitizen

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg

# Run initial checks
echo "Running initial code quality checks..."
uv run ruff check . --fix
uv run ruff format .

echo "Development environment setup complete!"
echo ""
echo "Next steps:"
echo "  1. Run tests: uv run pytest"
echo "  2. Check code quality: uv run ruff check ."
echo "  3. Format code: uv run ruff format ."
echo "  4. Type check: uv run mypy src/pmcgrab"
echo "  5. Run all pre-commit hooks: uv run pre-commit run --all-files"
