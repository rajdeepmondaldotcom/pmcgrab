#!/usr/bin/env python3
"""
Script to update version numbers consistently across the entire codebase.
Usage: python scripts/update-version.py <new_version>
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
    ]

    updated_files = []

    for file_info in files_to_update:
        file_path = Path(file_info["file"])

        if not file_path.exists():
            print(f"Warning: File {file_path} not found, skipping...")
            continue

        # Read file content
        content = file_path.read_text()

        # Update version (line by line to be more precise)
        lines = content.splitlines()
        new_lines = []

        for line in lines:
            if (
                file_info["file"] == "pyproject.toml"
                and line.strip().startswith('version = "')
                or file_info["file"] == "src/pmcgrab/__init__.py"
                and line.strip().startswith('__version__ = "')
            ):
                new_lines.append(file_info["replacement"])
            else:
                new_lines.append(line)

        new_content = "\n".join(new_lines) + "\n" if lines else content

        if new_content != content:
            file_path.write_text(new_content)
            updated_files.append(str(file_path))
            print(f"✓ Updated {file_path}")
        else:
            print(f"- No changes needed in {file_path}")

    if updated_files:
        print(f"\n✅ Version updated to {new_version} in {len(updated_files)} files:")
        for file in updated_files:
            print(f"   - {file}")
        print("\nNext steps:")
        print(f"1. git add {' '.join(updated_files)}")
        print(f"2. git commit -m 'release: bump version to {new_version}'")
        print("3. git push origin main")
        print(
            f"4. GitHub Actions will automatically create tag v{new_version} and publish to PyPI"
        )
    else:
        print("No files were updated.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/update-version.py <new_version>")
        print("Example: python scripts/update-version.py 1.0.0")
        sys.exit(1)

    new_version = sys.argv[1]
    update_version(new_version)
