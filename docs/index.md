# PMCGrab Documentation

**From PMCID to structured JSON - bridge PubMed Central and your AI pipeline.**

[![PyPI](https://img.shields.io/pypi/v/PMCGrab.svg)](https://pypi.org/project/PMCGrab/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/rajdeepmondaldotcom/pmcgrab/blob/main/LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/rajdeepmondaldotcom/pmcgrab?style=social)](https://github.com/rajdeepmondaldotcom/pmcgrab)

PMCGrab is a specialized Python toolkit for **retrieving, validating and restructuring PubMed Central (PMC) articles into clean, section-aware JSON** that large-language-model (LLM) pipelines can ingest directly for Retrieval-Augmented Generation (RAG), question-answering, summarization and other downstream tasks.

## Key Features

:material-download: **Effortless Retrieval**
Fetch full-text articles with a single PMCID using NCBI Entrez.

:material-code-json: **AI-Optimized JSON**
Output is pre-segmented into `Introduction`, `Methods`, `Results`, `Discussion`, etc., dramatically improving context relevance in RAG pipelines.

:material-speedometer: **Highly Concurrent**
Multithreaded batch downloader with configurable worker count, retries and timeouts.

:material-auto-fix: **HTML & Reference Cleaning**
Utilities to strip or normalize embedded HTML, citations and footnotes.

## Why PMCGrab?

While the NCBI Entrez API already provides raw XML, consuming it directly is burdensome:

| Feature                               | Entrez XML | PMCGrab JSON |
| ------------------------------------- | ---------- | ------------ |
| Section delineation                   | ❌         | ✅           |
| Straightforward to embed in vector DB | ❌         | ✅           |
| Ready for LLM chunking                | ❌         | ✅           |
| Batch parallelism                     | Limited    | Automatic    |

## Quick Start

### Installation

```bash
pip install pmcgrab
```

### Example: Process five PMC articles

Run the helper script included in the repository:

```bash
python examples/run_five_pmcs.py
```

The script will:

1. Download the five predefined PMCIDs.
2. Print a short summary for each article (title, abstract snippet, author count).
3. Save the complete JSON output to `pmc_output/PMC<id>.json` so you can inspect it later.

### Command Line Interface

```bash
# Process single paper
python -m pmcgrab PMC7181753

# Batch process with custom settings
python -m pmcgrab --output-dir ./results --workers 8 PMC7181753 PMC3539614
```

## What's in the Documentation

<div class="grid cards" markdown>

- :material-clock-fast:{ .lg .middle } **Getting Started**

  ***

  Installation, basic configuration, and your first PMCGrab script

  [:octicons-arrow-right-24: Getting Started](getting-started/installation.md)

- :material-book-open-page-variant:{ .lg .middle } **User Guide**

  ***

  Comprehensive guides for all PMCGrab features and use cases

  [:octicons-arrow-right-24: User Guide](user-guide/basic-usage.md)

- :material-code-tags:{ .lg .middle } **API Reference**

  ***

  Detailed documentation of all classes, functions, and modules

  [:octicons-arrow-right-24: API Reference](api/core.md)

- :material-lightbulb:{ .lg .middle } **Examples**

  ***

  Real-world examples and advanced usage patterns

  [:octicons-arrow-right-24: Examples](examples/python-examples.md)

</div>

## Example Output

PMCGrab transforms PMC articles into structured JSON like this:

```json
{
  "PMCID": "PMC7181753",
  "Title": "Example Article Title",
  "Authors": [
    {
      "FirstName": "John",
      "LastName": "Doe",
      "Affiliation": "University Example"
    }
  ],
  "Abstract": {
    "Background": "Research background...",
    "Methods": "Methodology used...",
    "Results": "Key findings...",
    "Conclusions": "Main conclusions..."
  },
  "Body": {
    "Introduction": "Introduction text...",
    "Methods": "Methods section...",
    "Results": "Results section...",
    "Discussion": "Discussion section..."
  },
  "Citations": [...],
  "Tables": [...],
  "Figures": [...]
}
```

## Community & Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/rajdeepmondaldotcom/pmcgrab/issues)
- **Discussions**: [Ask questions and share ideas](https://github.com/rajdeepmondaldotcom/pmcgrab/discussions)
- **PyPI**: [Download from PyPI](https://pypi.org/project/pmcgrab/)

## License

PMCGrab is licensed under the [Apache License 2.0](about/license.md).
