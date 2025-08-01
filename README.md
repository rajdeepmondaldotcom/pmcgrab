# PMCGrab

**Transform PubMed Central articles into AI-ready JSON for your research pipelines.**

[![PyPI](https://img.shields.io/pypi/v/pmcgrab.svg)](https://pypi.org/project/pmcgrab/)
[![Python](https://img.shields.io/pypi/pyversions/pmcgrab.svg)](https://pypi.org/project/pmcgrab/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/rajdeepmondaldotcom/pmcgrab/blob/main/LICENSE)
[![CI](https://github.com/rajdeepmondaldotcom/pmcgrab/workflows/CI/badge.svg)](https://github.com/rajdeepmondaldotcom/pmcgrab/actions)
[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://rajdeepmondaldotcom.github.io/pmcgrab/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

PMCGrab converts PubMed Central articles into clean, section-aware JSON optimized for large language models, RAG systems, and data analysis workflows.

## Why PMCGrab?

**From this complexity:**

- Raw XML with nested tags and references
- Inconsistent section structure
- Manual parsing and cleaning required

**To this simplicity:**

```json
{
  "pmc_id": "7114487",
  "title": "Machine learning approaches in cancer research",
  "abstract": "Recent advances in machine learning...",
  "body": {
    "Introduction": "Cancer research has evolved...",
    "Methods": "We implemented a deep learning...",
    "Results": "Our model achieved 94% accuracy...",
    "Discussion": "These findings demonstrate..."
  },
  "authors": [...],
  "journal": "Nature Medicine"
}
```

## Quick Start

### Installation

**With uv (recommended):**

```bash
uv add pmcgrab
```

**Standalone installation:**

```bash
uv pip install pmcgrab
```

**Why uv?** uv is 10-100x faster than pip and provides better dependency resolution. [Learn more about uv](https://github.com/astral-sh/uv)

### Basic Usage

```python
from pmcgrab.application.processing import process_single_pmc

# Get structured data from any PMC article
data = process_single_pmc("7114487")
print(f"Title: {data['title']}")
print(f"Sections: {list(data['body'].keys())}")
```

### Batch Processing Example

Process multiple research papers efficiently:

```python
# ─── examples/run_three_pmcs.py ──────────────────────────────────────────────
import json
from pathlib import Path

from pmcgrab.application.processing import process_single_pmc
from pmcgrab.infrastructure.settings import next_email

# The PMC IDs we want to process
PMC_IDS = ["7114487", "3084273", "7690653", "5707528", "7979870"]

OUT_DIR = Path("pmc_output")
OUT_DIR.mkdir(exist_ok=True)

for pmcid in PMC_IDS:
    email = next_email()
    print(f"• Fetching PMC{pmcid} using email {email} …")
    data = process_single_pmc(pmcid)
    if data is None:
        print(f"  ↳ FAILED to parse PMC{pmcid}")
        continue

    # Pretty-print a few key fields
    print(
        f"  Title   : {data['title'][:80]}{'…' if len(data['title']) > 80 else ''}\n"
        f"  Abstract: {data['abstract'][:120]}{'…' if len(data['abstract']) > 120 else ''}\n"
        f"  Authors : {len(data['authors']) if data['authors'] else 0}"
    )

    # Persist full JSON
    dest = OUT_DIR / f"PMC{pmcid}.json"
    with dest.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    print(f"  ↳ JSON saved to {dest}\n")
```

Run this example:

```bash
uv run python examples/run_three_pmcs.py
```

## Key Features

### AI-Optimized

- **Section-Aware Parsing**: Automatically extracts Introduction, Methods, Results, Discussion, and other sections
- **Clean JSON Output**: Structured data ready for vector databases and LLM pipelines
- **Research-Ready**: Perfect for systematic reviews, meta-analyses, and literature mining

### Performance & Reliability

- **Ultra-Fast**: Built with uv for lightning-speed dependency management
- **Robust Processing**: Built-in error handling and retry logic
- **Batch Processing**: Optimized for processing hundreds of articles with email rotation
- **Cross-Platform**: Works on Windows, macOS, and Linux

### Modern Development

- **Automated CI/CD**: Automatic testing, building, and PyPI publishing
- **Type-Safe**: Full type hints with MyPy checking
- **Code Quality**: Automated linting with Ruff and security scanning
- **Comprehensive Testing**: Multi-platform testing with pytest

## Command Line Interface

Process articles directly from the command line with uv:

```bash
# Single article
uv run python -m pmcgrab PMC7114487

# Multiple articles
uv run python -m pmcgrab PMC7114487 PMC3084273 PMC7690653

# From file with custom output directory
uv run python -m pmcgrab --input-file pmcids.txt --output-dir results/

# Parallel processing for speed
uv run python -m pmcgrab --workers 4 PMC7114487 PMC3084273 PMC7690653
```

**Pro tip**: All CLI commands use `uv run` for consistent environment management!

## Use Cases

- **Literature Reviews**: Systematically process hundreds of research papers
- **RAG Systems**: Feed structured content to your AI applications
- **Research Analysis**: Extract and analyze research methodologies and findings
- **Academic Workflows**: Automate paper processing for systematic reviews
- **Data Mining**: Build datasets from biomedical literature

## JSON Output Structure

Each processed article returns a comprehensive JSON structure:

```json
{
  "pmc_id": "7114487",
  "title": "Article title",
  "abstract": "Article abstract",
  "body": {
    "Introduction": "Section content...",
    "Methods": "Section content...",
    "Results": "Section content...",
    "Discussion": "Section content..."
  },
  "authors": [
    {
      "First_Name": "John",
      "Last_Name": "Doe",
      "Affiliation": "University Name"
    }
  ],
  "journal": "Journal Name",
  "pub_date": "2023-01-15",
  "doi": "10.1038/example",
  "figures": [...],
  "tables": [...],
  "references": [...]
}
```

## Documentation

- **[Complete Documentation](https://rajdeepmondaldotcom.github.io/pmcgrab/)** - Full API reference and guides
- **[Installation Guide](https://rajdeepmondaldotcom.github.io/pmcgrab/getting-started/installation/)** - Detailed setup instructions
- **[User Guide](https://rajdeepmondaldotcom.github.io/pmcgrab/user-guide/basic-usage/)** - Comprehensive usage examples
- **[Python Examples](https://rajdeepmondaldotcom.github.io/pmcgrab/examples/python-examples/)** - Code examples and patterns
- **[CLI Reference](https://rajdeepmondaldotcom.github.io/pmcgrab/user-guide/cli/)** - Command-line usage guide

## Requirements

- Python ≥ 3.10
- Internet connection for PMC API access

## Development

### Quick Setup with uv

```bash
# Clone and setup (lightning fast with uv!)
git clone https://github.com/rajdeepmondaldotcom/pmcgrab.git
cd pmcgrab
uv sync --dev --all-groups

# Run tests
uv run pytest

# Code quality checks
uv run ruff check .
uv run ruff format .
uv run mypy src/pmcgrab

# Build documentation
uv run mkdocs serve
```

### Automated Workflows

PMCGrab uses GitHub Actions for fully automated CI/CD:

- **Continuous Integration**: Tests on Python 3.10-3.13 across Ubuntu, Windows, macOS
- **Auto-Release**: Bump version → Push → Automatic PyPI publishing
- **Documentation**: Auto-deploy docs to GitHub Pages
- **Security**: Automated security scanning with Bandit and Safety
- **Dependencies**: Automatic dependency updates with Dependabot

**To release a new version:**

1. Update version in `pyproject.toml` and `src/pmcgrab/__init__.py`
2. Commit and push to main
3. **Everything else is automatic!**
   - Auto-detects version bump
   - Creates git tag
   - Runs full test suite
   - Builds package with uv
   - Publishes to PyPI
   - Creates GitHub release with changelog
   - Updates documentation

### Workflow Status

Check the status of our automated workflows:

- **[CI Pipeline](https://github.com/rajdeepmondaldotcom/pmcgrab/actions/workflows/ci.yml)** - Continuous Integration
- **[Release Pipeline](https://github.com/rajdeepmondaldotcom/pmcgrab/actions/workflows/release.yml)** - Auto-publish to PyPI
- **[Documentation](https://github.com/rajdeepmondaldotcom/pmcgrab/actions/workflows/docs.yml)** - Auto-deploy docs

## Links & Resources

- **[PyPI Package](https://pypi.org/project/pmcgrab/)** - Install with uv or pip
- **[GitHub Repository](https://github.com/rajdeepmondaldotcom/pmcgrab)** - Source code and issues
- **[Documentation](https://rajdeepmondaldotcom.github.io/pmcgrab/)** - Complete user guide
- **[uv Package Manager](https://github.com/astral-sh/uv)** - The fast Python package manager we use
- **[GitHub Actions](https://github.com/rajdeepmondaldotcom/pmcgrab/actions)** - CI/CD workflows
- **[License](https://github.com/rajdeepmondaldotcom/pmcgrab/blob/main/LICENSE)** - Apache 2.0

## Why Choose PMCGrab?

### vs Manual Processing

- **Manual**: Hours of XML parsing and cleaning
- **PMCGrab**: One function call, clean JSON output

### vs Other Tools

- **Others**: Slow pip installs, complex setup, limited output formats
- **PMCGrab**: Lightning-fast uv, simple API, AI-ready JSON

### vs Building Your Own

- **DIY**: Weeks of development, edge cases, maintenance burden
- **PMCGrab**: Production-ready, tested, actively maintained

## Performance

| Metric                | PMCGrab with uv  | Traditional pip-based tools  |
| --------------------- | ---------------- | ---------------------------- |
| Installation          | **~2 seconds**   | ~30-60 seconds               |
| Dependency resolution | **~1 second**    | ~10-30 seconds               |
| Article processing    | **~2-5 seconds** | ~2-5 seconds                 |
| Batch processing      | **Optimized**    | Manual implementation needed |

## Contributing

Contributions are welcome! Please see our [contributing guide](https://github.com/rajdeepmondaldotcom/pmcgrab/blob/main/CONTRIBUTING.md) for details on:

- Submitting bug reports and feature requests
- Setting up your development environment
- Code style and testing requirements
- Pull request process

## License

PMCGrab is licensed under the [Apache 2.0 License](https://github.com/rajdeepmondaldotcom/pmcgrab/blob/main/LICENSE).

## Citation

If PMCGrab helps your research, please cite it:

```bibtex
@software{pmcgrab,
  author = {Rajdeep Mondal},
  title = {PMCGrab: AI-ready retrieval and parsing of PubMed Central articles},
  url = {https://github.com/rajdeepmondaldotcom/pmcgrab},
  version = {0.3.6},
  year = {2025}
}
```

---

**Ready to transform biomedical literature into structured data?** [Install PMCGrab](https://pypi.org/project/pmcgrab/) and start processing papers in minutes.
