# PMCGrab

**Transform PubMed Central articles into AI-ready JSON for your research pipelines.**

[![PyPI](https://img.shields.io/pypi/v/pmcgrab.svg)](https://pypi.org/project/pmcgrab/)
[![Python](https://img.shields.io/pypi/pyversions/pmcgrab.svg)](https://pypi.org/project/pmcgrab/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/rajdeepmondaldotcom/pmcgrab/blob/main/LICENSE)
[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://rajdeepmondaldotcom.github.io/pmcgrab/)

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

```bash
pip install pmcgrab
```

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
python examples/run_three_pmcs.py
```

## Key Features

- **Section-Aware Parsing**: Automatically extracts Introduction, Methods, Results, Discussion, and other sections
- **Clean JSON Output**: Structured data ready for vector databases and LLM pipelines
- **Robust Processing**: Built-in error handling and retry logic
- **Fast & Efficient**: Optimized for batch processing with email rotation
- **Research-Ready**: Perfect for systematic reviews, meta-analyses, and literature mining

## Command Line Interface

Process articles directly from the command line:

```bash
# Single article
python -m pmcgrab PMC7114487

# Multiple articles
python -m pmcgrab PMC7114487 PMC3084273 PMC7690653

# From file
python -m pmcgrab --input-file pmcids.txt --output-dir results/
```

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

```bash
# Clone and setup
git clone https://github.com/rajdeepmondaldotcom/pmcgrab.git
cd pmcgrab
pip install -e ".[dev,test,docs]"

# Run tests
pytest

# Build documentation
mkdocs serve
```

## Links

- **[PyPI Package](https://pypi.org/project/pmcgrab/)** - Install via pip
- **[GitHub Repository](https://github.com/rajdeepmondaldotcom/pmcgrab)** - Source code and issues
- **[Documentation](https://rajdeepmondaldotcom.github.io/pmcgrab/)** - Complete user guide
- **[License](https://github.com/rajdeepmondaldotcom/pmcgrab/blob/main/LICENSE)** - Apache 2.0

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
  version = {0.3.4},
  year = {2025}
}
```

---

**Ready to transform biomedical literature into structured data?** [Install PMCGrab](https://pypi.org/project/pmcgrab/) and start processing papers in minutes.
