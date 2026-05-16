# Final Clean-Code Plan

Status: Phase 6 final consolidated plan.

## Anchor Decision

PMCGrab stays a Python library and CLI for converting PMC IDs and local JATS XML into AI-ready JSON. The cleanup deepens existing Modules and fixes drift. It does not replace the parser, CLI framework, package manager, or NCBI access approach.

## Implementation Order

### 1. Fix Public Interface Truth

Commit scope:

- Runtime version matches package version.
- Top-level `process_single_pmc` exports the application processing Interface.
- Tests lock both behaviors.

Acceptance:

- `pmcgrab.__version__ == importlib.metadata.version("pmcgrab")`
- `inspect.signature(pmcgrab.process_single_pmc)` includes `download`, `timeout`, and `metadata_only`.

### 2. Make Error Suppression Honest

Commit scope:

- `paper_dict_from_pmc(..., suppress_errors=True)` returns `{}` on XML acquisition/parsing failures.
- `paper_dict_from_local_xml(..., suppress_errors=True)` returns `{}` on local read/XML parse failures.
- Local PMCID extraction accepts `pub-id-type="pmc"` and `pub-id-type="pmcid"`.

Acceptance:

- Malformed local XML with `suppress_errors=True` does not raise.
- Local XML with `PMC123` under either supported PMCID attribute returns `123`.

### 3. Tighten CLI Contract

Commit scope:

- Add `--version`.
- Validate positive worker count.
- Correct `--from-id-file` help text.
- Add tests for version, invalid workers, JSONL output, quiet mode, and ID-file resolution.
- Replace broad catch/pass tests with assertions where touched.

Acceptance:

- `python -m pmcgrab --version` exits 0.
- `--batch-size 0` exits non-zero with a clear argparse error.
- JSONL output and `summary.json` are asserted by tests.

### 4. Consolidate Release Safety

Commit scope:

- Keep a single PyPI publish path.
- Remove duplicate release/publish workflows or make them non-publishing.
- Build and smoke-test the artifact before publish.
- Use locked dependency installs in CI.
- Remove CI-time dependency mutation.
- Align Ruff versions.

Acceptance:

- No workflow publishes on plain `pyproject.toml` changes.
- Tag publish workflow runs build/import/CLI smoke checks before `uv publish`.
- CI does not call `uv add`.

### 5. Make Docs Match Code

Commit scope:

- Update architecture docs to describe actual Modules and deferred deepening work.
- Update output examples to use current normalized keys.
- Remove stale test and coverage proof claims or replace them with current verified values.
- Keep research and audit docs in `docs/development`.

Acceptance:

- Docs no longer advertise unsupported CLI flags as current behavior.
- Docs no longer show `data["journal"]`, `data["doi"]`, or `data["references"]` for normalized processing output.

## Deferred Follow-Up Issues

These remain important, but they should be implemented after this cleanup branch lands:

- Parser field registry for `build_complete_paper_dict`.
- Unified serialization Module shared by `Paper.to_dict` and application processing.
- Explicit serialized schemas for tables and figures.
- Dedicated network/local XML source Adapters.
- Gradual mypy enforcement expansion after the current error set is measured.

## Final Audit Notes

- The highest release risk is duplicate publishing, not parser aesthetics.
- The highest compatibility risk is the top-level deprecated export.
- The highest reliability gap is error suppression not covering acquisition.
- The highest documentation risk is examples using keys that do not exist.

## Verification Commands

Run before final commit:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -q --no-cov
uv run pytest
uv build
python -m pmcgrab --help
python -m pmcgrab --version
```

Do not run Terraform commands.
