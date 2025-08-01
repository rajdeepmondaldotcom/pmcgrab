#!/usr/bin/env python3
"""
Script to update version numbers consistently across the entire codebase.

This script updates version numbers in all relevant files to ensure consistency:
- Core files: pyproject.toml, src/pmcgrab/__init__.py
- Documentation: README.md, docs/about/citation.md
- Source code: User-Agent strings in all API modules
- Citations: BibTeX, APA, MLA, Chicago formats

Usage: python scripts/update-version.py <new_version>
Example: python scripts/update-version.py 1.0.0

After running this script, commit and push the changes to trigger
automated release to PyPI via GitHub Actions.
"""

import re
import sys
from pathlib import Path


def update_version(new_version: str):
    """Update version in all relevant files."""

    # Validate version format (semantic versioning)
    if not re.match(r"^\d+\.\d+\.\d+$", new_version):
        print(
            f"Error: Invalid version format '{new_version}'. Use semantic versioning (e.g., 1.2.3)"
        )
        sys.exit(1)

    files_to_update = [
        # Core version files
        {
            "file": "pyproject.toml",
            "pattern": r'^version = "[^"]*"',
            "replacement": f'version = "{new_version}"',
        },
        {
            "file": "src/pmcgrab/__init__.py",
            "pattern": r'__version__ = "[^"]*"',
            "replacement": f'__version__ = "{new_version}"',
        },
        # Documentation and citation files
        {
            "file": "README.md",
            "pattern": r"version = \{[^}]*\}",
            "replacement": f"version = {{{new_version}}}",
        },
        {
            "file": "docs/about/citation.md",
            "pattern": r"Version [0-9]+\.[0-9]+\.[0-9]+",
            "replacement": f"Version {new_version}",
        },
        {
            "file": "docs/about/citation.md",
            "pattern": r"version [0-9]+\.[0-9]+\.[0-9]+",
            "replacement": f"version {new_version}",
        },
        {
            "file": "docs/about/citation.md",
            "pattern": r"version = \{[^}]*\}",
            "replacement": f"version = {{{new_version}}}",
        },
        {
            "file": "docs/about/citation.md",
            "pattern": r"\(e\.g\., [0-9]+\.[0-9]+\.[0-9]+\)",
            "replacement": f"(e.g., {new_version})",
        },
        # User-Agent strings in source code
        {
            "file": "src/pmcgrab/oa_service.py",
            "pattern": r'"User-Agent": "pmcgrab/[^"]*"',
            "replacement": f'"User-Agent": "pmcgrab/{new_version}"',
        },
        {
            "file": "src/pmcgrab/litctxp.py",
            "pattern": r'"User-Agent": "pmcgrab/[^"]*"',
            "replacement": f'"User-Agent": "pmcgrab/{new_version}"',
        },
        {
            "file": "src/pmcgrab/oai.py",
            "pattern": r'"User-Agent": "pmcgrab/[^"]*"',
            "replacement": f'"User-Agent": "pmcgrab/{new_version}"',
        },
        {
            "file": "src/pmcgrab/bioc.py",
            "pattern": r'"User-Agent": "pmcgrab/[^"]*"',
            "replacement": f'"User-Agent": "pmcgrab/{new_version}"',
        },
        {
            "file": "src/pmcgrab/idconvert.py",
            "pattern": r'"User-Agent": "pmcgrab/[^"]*"',
            "replacement": f'"User-Agent": "pmcgrab/{new_version}"',
        },
    ]

    updated_files = []

    for file_info in files_to_update:
        file_path = Path(file_info["file"])

        if not file_path.exists():
            print(f"Warning: File {file_path} not found, skipping...")
            continue

        # Read file content
        content = file_path.read_text()

        # Update version using regex replacement
        new_content = re.sub(
            file_info["pattern"], file_info["replacement"], content, flags=re.MULTILINE
        )

        if new_content != content:
            file_path.write_text(new_content)
            updated_files.append(str(file_path))
            print(f"✓ Updated {file_path}")
        else:
            print(f"- No changes needed in {file_path}")

    if updated_files:
        # Remove duplicates and sort for cleaner output
        unique_files = sorted(set(updated_files))
        print(f"\n✅ Version updated to {new_version} in {len(unique_files)} files:")
        for file in unique_files:
            print(f"   - {file}")
        print("\nNext steps:")
        print(f"1. git add {' '.join(unique_files)}")
        print(f"2. git commit -m 'release: bump version to {new_version}'")
        print("3. git push origin main")
        print(
            f"4. GitHub Actions will automatically create tag v{new_version} and publish to PyPI"
        )
        print("\n📍 Files updated:")
        print("   • Core: pyproject.toml, __init__.py")
        print("   • Docs: README.md, citation.md")
        print("   • Code: User-Agent strings in 5 API modules")
    else:
        print("No files were updated.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/update-version.py <new_version>")
        print("Example: python scripts/update-version.py 1.0.0")
        sys.exit(1)

    new_version = sys.argv[1]
    update_version(new_version)
