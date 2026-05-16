# PMCGrab Clean-Code Implementation Plan

Status: Phase 3 revision, grounded in the current codebase and reviewer audit findings.

## Goal

Make PMCGrab easier to trust, maintain, and release without changing its core product direction: convert PMC IDs or local JATS XML into clean, section-aware, AI-ready Python objects and JSON.

This plan does not redesign PMCGrab into a new architecture. It deepens the Modules that already exist, tightens public Interfaces, and fixes drift between code, tests, docs, and release automation.

## Current Shape

PMCGrab currently has these important Modules:

- `pmcgrab.model.Paper`: public object Interface for parsed articles.
- `pmcgrab.parser`: XML-to-internal-dictionary orchestration.
- `pmcgrab.application.processing`: programmatic processing Interface for normalized article dictionaries.
- `pmcgrab.cli.pmcgrab_cli`: CLI Adapter over processing and file output.
- `pmcgrab.fetch`: network and local XML acquisition.
- `pmcgrab.processing`: deprecated legacy batch Adapter retained for compatibility.

The code works, but several Interfaces are shallow or misleading:

- Top-level `from pmcgrab import process_single_pmc` points at the deprecated Adapter instead of the application Module.
- Runtime `pmcgrab.__version__` diverges from `pyproject.toml`.
- `suppress_errors=True` only protects parser work after XML acquisition has already succeeded.
- Local XML PMCID extraction accepts `pub-id-type="pmc"` but misses `pub-id-type="pmcid"`.
- CLI docs and tests describe behavior that differs from actual `argparse`.
- Release workflows can publish from multiple paths, including paths that do not require tests first.

## Implementation Slices

### Slice 1: Public Interface and Version Truth

Files:

- `src/pmcgrab/__init__.py`
- `pyproject.toml`
- `docs/about/citation.md`
- `tests/`

Changes:

- Make top-level `process_single_pmc` export the application Module's function.
- Keep `pmcgrab.processing` as the explicit deprecated Adapter.
- Set `pmcgrab.__version__` to match `pyproject.toml`.
- Add tests that root exports have the expected signature and version stays synchronized with installed metadata.

Benefits:

- Better Leverage: callers get the current processing Interface from the package root.
- Better Locality: deprecated behavior stays isolated in `pmcgrab.processing`.

### Slice 2: Acquisition Error Policy and Local PMCID Parsing

Files:

- `src/pmcgrab/parser.py`
- `src/pmcgrab/fetch.py`
- `tests/test_local_xml.py`
- `tests/test_regression_bugs.py`

Changes:

- Apply `suppress_errors=True` around network and local XML acquisition, not only around `generate_paper_dict`.
- Accept both `pub-id-type="pmc"` and `pub-id-type="pmcid"` for local XML.
- Add malformed-local-XML regression tests.
- Add tests for both PMCID attribute spellings.

Benefits:

- Better Leverage: batch callers can trust one suppression flag across the full pipeline.
- Better Locality: identifier extraction rules live where local XML is parsed.

### Slice 3: CLI Adapter Correctness

Files:

- `src/pmcgrab/cli/pmcgrab_cli.py`
- `src/pmcgrab/__main__.py`
- `tests/test_cli_complete.py`
- `tests/test_cli_contract.py` or equivalent focused tests
- `docs/user-guide/cli.md`
- `docs/api/cli.md`
- `docs/examples/cli-examples.md`

Changes:

- Add `--version` using argparse's built-in version action.
- Validate `--batch-size/--workers` as a positive integer.
- Correct help text for `--from-id-file`: bare numeric IDs are treated as PMC IDs; PMIDs need `--pmids`.
- Prefer the application Module for processing and keep CLI code focused on args, progress, and output files.
- Replace broad catch/pass CLI tests with assertions on exit behavior, output files, JSONL, and summary.
- Update CLI docs from actual `--help` output.

Benefits:

- Better Depth: CLI becomes a thin Adapter instead of duplicating processing orchestration.
- Better test signal: broken CLI behavior fails tests instead of being swallowed.

### Slice 4: Release and CI Safety

Files:

- `.github/workflows/ci.yml`
- `.github/workflows/pre-commit.yml`
- `.github/workflows/publish-on-tag.yml`
- `.github/workflows/release.yml`
- `.github/workflows/publish.yml`
- `.pre-commit-config.yaml`

Changes:

- Keep one PyPI publish path.
- Ensure publish builds the package, installs the wheel, imports `pmcgrab`, and runs `python -m pmcgrab --help` before upload.
- Remove duplicate release/publish workflows or convert them to non-publishing release-note automation.
- Use `uv sync --locked` in CI so dependency resolution is reproducible.
- Remove CI-time `uv add`.
- Align Ruff versions between `pyproject.toml` and pre-commit.

Benefits:

- Better Locality: release responsibility lives in one workflow.
- Lower deployment risk: a publish path must prove the built artifact imports and exposes the CLI.

### Slice 5: Documentation Truthfulness

Files:

- `docs/development/architecture.md`
- `docs/development/testing.md`
- README and user-guide pages that describe output keys.

Changes:

- Replace imaginary classes and Interfaces in architecture docs with the actual Modules.
- Update output examples to use `abstract_text`, `journal_title`, `article_id`, and `citations`.
- Remove or regenerate stale test/coverage counts.
- Add a small schema snapshot test for normalized article dictionaries.

Benefits:

- Better Leverage for maintainers and agents: docs point to real seams.
- Lower support burden: examples use keys that exist at runtime.

### Slice 6: Deferred Deepening Work

These are valuable but larger than the first cleanup pass:

- Introduce a field registry for `build_complete_paper_dict`.
- Define explicit table and figure serialization schemas.
- Consolidate `Paper.to_dict` and application `_extract_paper_dict` behind one serialization Module.
- Introduce explicit XML source Adapters for network and local sources.

These should be implemented after the public Interface, error policy, CLI, and release paths are stable.

## Verification Plan

Run:

- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run pytest -q --no-cov`
- `uv run pytest`
- `uv build`
- install the wheel in a temp venv and run:
  - `python -c "import pmcgrab; print(pmcgrab.__version__)"`
  - `python -m pmcgrab --help`

Do not run Terraform commands.
