# Contributing

We welcome contributions to PMCGrab! This guide will help you get started.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/rajdeepmondaldotcom/pmcgrab.git
   cd pmcgrab
   ```
3. **Set up development environment**:
   ```bash
   uv sync --dev
   ```

## Development Workflow

1. **Create a feature branch**:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our coding standards

3. **Run tests**:

   ```bash
   uv run pytest
   ```

4. **Run linting**:

   ```bash
   uv run ruff check .
   uv run ruff format .
   ```

5. **Commit your changes**:

   ```bash
   git commit -m "feat: add new feature description"
   ```

6. **Push and create a pull request**

## Coding Standards

- Follow PEP 8 style guidelines
- Use type hints for all functions
- Write comprehensive docstrings in Google style
- Add tests for new functionality
- Keep functions focused and well-named

## Testing

- Write unit tests for all new code
- Ensure tests pass locally before submitting
- Add integration tests for complex features
- Maintain high test coverage

## Documentation

- Update documentation for new features
- Include examples in docstrings
- Update the changelog

## Questions?

Open an issue on GitHub if you have questions or need help.
