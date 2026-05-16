# Clean-Code Industry Standards Research

Status: Phase 4 research. Research refines the existing plan; it does not redirect the architecture.

## Sources Checked

- PyPA: Single-sourcing the project version
  https://packaging.python.org/en/latest/discussions/single-source-version/
- Python docs: `argparse` version action and parsing behavior
  https://docs.python.org/3.10/library/argparse.html
- GitHub Docs: workflow syntax and `jobs.<job_id>.needs`
  https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- GitHub Docs: building, testing, and publishing Python packages
  https://docs.github.com/en/actions/tutorials/build-and-test-code/python
- uv docs: locking and syncing
  https://docs.astral.sh/uv/concepts/projects/sync/
- uv docs: building and publishing packages
  https://docs.astral.sh/uv/guides/package/
- pytest-cov docs: `--cov-fail-under`
  https://pytest-cov.readthedocs.io/en/latest/config.html
- NCBI Bookshelf: Entrez E-utilities parameters and API-key policy
  https://www.ncbi.nlm.nih.gov/sites/books/NBK25499/

## Research Findings Applied to the Plan

### Version Single-Sourcing

PyPA explicitly recognizes the common need for an import package's `__version__` to match `importlib.metadata.version()`, and recommends an automated test to prevent divergence.

Plan refinement:

- Keep Hatchling's configured source version path for now.
- Update `pmcgrab.__version__` to match `pyproject.toml`.
- Add an automated test that compares runtime `__version__` with package metadata.

No redesign:

- Do not introduce a VCS-derived versioning system in this pass.

### CLI Version Flag

Python's `argparse` has a built-in `action="version"` that prints version information and exits.

Plan refinement:

- Add `--version` via argparse's built-in action.
- Do not hand-roll version parsing.

No redesign:

- Do not add a new CLI framework.

### Release Workflow Safety

GitHub Actions supports `jobs.<job_id>.needs` to require successful dependent jobs before later jobs run. GitHub's Python packaging docs describe publishing after CI tests pass. uv supports `uv build` and `uv publish`, and notes that trusted publishing from GitHub Actions can avoid stored credentials.

Plan refinement:

- Keep one publish workflow.
- Build before publish.
- Install and smoke-test the built wheel before publish.
- Use explicit job ordering for build/test/publish where a single workflow owns the path.

No redesign:

- Do not change package hosting or replace uv.

### Reproducible CI Installs

uv documents `--locked` as the option that prevents automatic lockfile updates and fails if the lockfile is stale.

Plan refinement:

- Use `uv sync --locked` in CI paths that validate existing code.
- Keep scheduled dependency update workflow responsible for lockfile changes.

No redesign:

- Do not remove `uv.lock` or migrate to another package manager.

### Coverage Enforcement

pytest-cov supports `--cov-fail-under MIN` to fail when total coverage is below a threshold.

Plan refinement:

- Add a conservative coverage threshold only after measuring the current repo with the existing suite.
- Avoid asserting stale README coverage numbers until CI enforces a threshold.

No redesign:

- Do not make coverage the primary quality gate before CLI/release correctness is fixed.

### NCBI API Policy

NCBI E-utilities docs require an email parameter and describe API keys for callers posting more than three requests per second.

Plan refinement:

- Keep the existing email pool and API-key rate limiter direction.
- Do not increase default concurrency beyond current documented behavior.
- Prefer clearer docs/help text over behavioral changes in ID-file resolution.

No redesign:

- Do not introduce a new NCBI client stack in this pass.

## Resulting Plan Changes

The research supports the original plan with these specific refinements:

- Add version-sync tests, not just a manual version edit.
- Use `argparse`'s native `version` action.
- Consolidate publish paths before expanding release automation.
- Prefer `uv sync --locked` in CI.
- Keep API behavior stable where docs overpromise; update docs/help unless compatibility-safe aliases are obvious.
