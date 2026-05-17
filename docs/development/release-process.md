# Release Process

Releases are published from `main` through GitHub Actions. Do not publish
production packages from a laptop unless the GitHub pipeline is unavailable and
the failure mode is understood.

## Standard Release

1. Update the package version in `pyproject.toml` and `src/pmcgrab/__init__.py`.
2. Add a matching `CHANGELOG.md` entry.
3. Open and merge the release pull request into `main`.
4. In GitHub Actions, run **Release from main** on the `main` branch.
5. Leave the `version` input blank to use `pyproject.toml`, or enter the exact
   version without the leading `v`.

The **Release from main** workflow validates the current `main` checkout, builds
the package, smoke-tests the wheel, checks that the tag and PyPI version do not
already exist, and pushes an annotated `vX.Y.Z` tag.

Pushing that tag triggers **Publish to PyPI (on tag)**. The tag workflow builds
from the tagged source, runs linting and tests, publishes to PyPI using the
repository `PYPI_TOKEN` secret, and creates the GitHub Release with the wheel and
sdist attached.

## Required Repository Setup

- `PYPI_TOKEN` must exist as a GitHub Actions repository secret.
- The release workflow needs `contents: write` permission so it can push tags.
- The publish workflow needs `contents: write` permission so it can create the
  GitHub Release.

## Failure Handling

- If **Release from main** fails before the tag is pushed, fix the issue on a
  branch, merge to `main`, and rerun the workflow.
- If **Publish to PyPI (on tag)** fails after the tag is pushed, inspect the
  failed run before moving the tag. Do not delete or recreate a published PyPI
  version; PyPI versions are immutable.
- If the PyPI upload succeeds but GitHub Release creation fails, create the
  release from the existing tag and attach the built wheel and sdist from the
  workflow artifacts or a verified local rebuild from that tag.
