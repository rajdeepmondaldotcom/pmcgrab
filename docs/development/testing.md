# Testing

PMCGrab uses pytest, pytest-cov, Ruff, pre-commit, and GitHub Actions. The test
suite is configured in `pyproject.toml` and currently lives directly under
`tests/`.

## Commands

```bash
# Run the full test suite with configured coverage reports
uv run pytest

# Run the suite without coverage when iterating quickly
uv run pytest -q --no-cov

# Run one file
uv run pytest tests/test_cli_complete.py

# Run one test
uv run pytest tests/test_parser.py::test_paper_dict_from_pmc_suppresses_fetch_errors

# Run Ruff
uv run ruff check .
uv run ruff format --check .

# Run pre-commit
uv run pre-commit run --all-files

# Build docs
uv run mkdocs build
```

`pytest` writes terminal, HTML, and XML coverage reports by default:

- terminal coverage via `--cov-report=term-missing`
- HTML coverage in `htmlcov/`
- XML coverage in `coverage.xml`

## Test Files

| File                                   | Coverage intent                                                        |
| -------------------------------------- | ---------------------------------------------------------------------- |
| `tests/test_public_api.py`             | Top-level exports and package version consistency.                     |
| `tests/test_cli_complete.py`           | CLI parser behavior, validation, ID modes, and subprocess smoke tests. |
| `tests/test_application_processing.py` | Application-level processing helpers.                                  |
| `tests/test_parser.py`                 | Parser orchestration, DTD validation behavior, and error suppression.  |
| `tests/test_local_xml.py`              | Local XML file and directory processing.                               |
| `tests/test_model.py`                  | `Paper` and text element behavior.                                     |
| `tests/test_figure.py`                 | Figure extraction.                                                     |
| `tests/test_html_cleaning.py`          | HTML cleanup utilities.                                                |
| `tests/test_settings.py`               | Environment-driven settings.                                           |
| `tests/test_utils.py`                  | Utility helpers.                                                       |
| `tests/test_regression_bugs.py`        | Regressions that should stay fixed.                                    |
| `tests/test_comprehensive_coverage.py` | Broad coverage for less common parser paths.                           |

## Pytest Configuration

The important pytest settings are in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "--cov=pmcgrab",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-report=xml",
]
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
```

Use `--no-cov` for targeted local runs when coverage output slows down the
feedback loop.

## CLI Testing Pattern

CLI tests should cover both parser-level behavior and installed-command behavior.
The subprocess smoke tests protect packaging entry points that direct function
tests cannot catch:

```python
import subprocess
import sys


def test_module_help_smoke():
    result = subprocess.run(
        [sys.executable, "-m", "pmcgrab", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "--pmcids" in result.stdout
```

Prefer mocked processing helpers for slow or network-sensitive CLI paths. Use a
real subprocess only when testing importability, argument parsing, version
output, or the package entry point.

## Network Testing

Do not make live NCBI calls in unit tests. Patch the boundary closest to the
behavior under test:

- Patch `pmcgrab.fetch.get_xml()` when testing parser error handling.
- Patch `pmcgrab.application.processing.process_single_pmc()` when testing CLI
  orchestration.
- Use small inline XML snippets for parser and model tests.

This keeps tests deterministic and avoids rate-limit coupling.

## CI

`.github/workflows/ci.yml` runs on pull requests and pushes across Python 3.10,
3.11, 3.12, and 3.13. The workflow installs dependencies with locked uv sync
commands, runs Ruff, and runs pytest.

`.github/workflows/publish-on-tag.yml` is the only PyPI publishing workflow. It
builds from a tag, smoke-tests the built wheel, and publishes with `uv publish`.

## Adding Tests

When changing behavior, add the narrowest test that would fail without the
change:

- Public API compatibility: `tests/test_public_api.py`
- CLI behavior: `tests/test_cli_complete.py`
- Local XML behavior: `tests/test_local_xml.py`
- Parser behavior: `tests/test_parser.py`
- Output schema behavior: model or application processing tests

Broaden coverage only when the change crosses module boundaries or affects a
public contract.
