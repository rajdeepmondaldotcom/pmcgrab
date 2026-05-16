# Clean-Code Plan Audit

Status: Phase 2 audit plus Phase 6 final audit inputs.

## Audit Sources

- Local code inspection of `src/pmcgrab`, `tests`, `.github/workflows`, docs, and package metadata.
- Strict architecture reviewer agent.
- Strict test/CI reviewer agent.
- Strict public API compatibility reviewer agent.
- Local verification: `uv run pytest -q --no-cov` passed with 158 tests and 34 warnings.

## Findings Against the Plan

### Public API and Version

Finding:

- `pyproject.toml` declares version `1.0.7`, while `src/pmcgrab/__init__.py` exposes `1.0.6`.
- Top-level `process_single_pmc` comes from deprecated `pmcgrab.processing`, while README recommends `from pmcgrab import process_single_pmc`.

Plan impact:

- Slice 1 is required before release cleanup. User-Agent strings and `_meta.pmcgrab_version` are runtime behavior, not cosmetic metadata.

### Error Policy

Finding:

- `paper_dict_from_local_xml(..., suppress_errors=True)` does not suppress XML parse errors because `parse_local_xml()` runs before `generate_paper_dict()`.
- `paper_dict_from_pmc(..., suppress_errors=True)` has the same shape around `get_xml()`.

Plan impact:

- Slice 2 must wrap acquisition and parsing under the same suppression policy.

### Local XML Identifier Extraction

Finding:

- `parse_local_xml()` checks `pub-id-type="pmc"` but not `pub-id-type="pmcid"`.
- Existing tests and PMC-like XML use both forms.

Plan impact:

- Slice 2 should add tests for both spellings and optional `PMC` prefix stripping.

### CLI

Finding:

- CLI docs advertise positional IDs, `--version`, `--show-config`, `--email`, `--input-file`, retry flags, timeout flags, and log files that argparse does not implement.
- CLI tests catch broad exceptions and pass, masking failures.
- CLI network mode reimplements concurrency instead of using the application Module.

Plan impact:

- Slice 3 should add `--version` and input validation now.
- Docs should be generated from actual argparse behavior.
- Full `BatchRun` deepening can be deferred if tests lock current behavior first.

### Release and CI

Finding:

- Multiple workflows can publish to PyPI.
- One release workflow publishes on `pyproject.toml` changes and does not require tests.
- CI has mypy configured but non-blocking.
- Pre-commit CI mutates dependencies with `uv add`.
- Ruff is pinned differently in `pyproject.toml` and pre-commit.

Plan impact:

- Slice 4 is required. Consolidating publish paths is higher priority than expanding mypy strictness, because duplicate publish paths can ship broken artifacts.

### Docs and Metrics

Finding:

- Architecture docs describe dataclasses and parser classes that do not exist.
- Several docs use nonexistent normalized output keys such as `journal`, `doi`, and `references`.
- README proof metrics appear stale: current test count is 158 test functions, not 218.

Plan impact:

- Slice 5 should remove stale hard-coded proof metrics or clearly mark them as historical.
- Architecture docs should represent current Modules first; deepening proposals can live in the final plan.

### Deferred Deepening

Finding:

- The parser facade and serialization paths are real architecture friction, but changing them carries larger compatibility risk.

Plan impact:

- Keep the field registry, table/figure schema, and serialization consolidation in the final plan as follow-up slices unless the first cleanup slices reveal low-risk entry points.

## Blockers

No code blockers found. The test suite currently passes without coverage.

## Audit Decision

Proceed with implementation in this priority order:

1. Public API/version correctness.
2. Error policy and local PMCID parsing.
3. CLI contract and tests.
4. Release workflow consolidation.
5. Docs truthfulness and final architecture plan.
