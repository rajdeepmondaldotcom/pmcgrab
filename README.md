# pmcgrab
Your gateway to AI-ready scientific literature from PubMed Central
**Download • Parse • Structure • Scale**

[![PyPI](https://img.shields.io/pypi/v/pmcgrab.svg)](https://pypi.org/project/pmcgrab/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

`pmcgrab` is a specialised Python toolkit for **retrieving, validating and restructuring PubMed Central (PMC) articles into clean, section-aware JSON** that large-language-model (LLM) pipelines can ingest directly for Retrieval-Augmented Generation (RAG), question-answering, summarisation and other downstream tasks.

---

## Table of Contents
1. [Key Features](#key-features)
2. [Why pmcgrab?](#why-pmcgrab)
3. [Installation](#installation)
4. [Quick Start (Python)](#quick-start-python)
5. [Command-Line Interface](#command-line-interface)
6. [Batch Processing & Scaling](#batch-processing--scaling)
7. [Output Schema](#output-schema)
8. [Configuration](#configuration)
9. [Logging](#logging)
10. [Development](#development)
11. [Contributing](#contributing)
12. [License](#license)
13. [Citation](#citation)
14. [Acknowledgements](#acknowledgements)

---

## Key Features
* **Effortless Retrieval** – Fetch full-text articles with a single PMCID using NCBI Entrez.
* **AI-Optimised JSON** – Output is pre-segmented into `Introduction`, `Methods`, `Results`, `Discussion`, etc., dramatically improving context relevance in RAG pipelines.
* **Highly Concurrent** – Multithreaded batch downloader with configurable worker count, retries and timeouts.
* **DTD Validation (Optional)** – Verify incoming XML to prevent downstream parsing errors.
* **HTML & Reference Cleaning** – Utilities to strip or normalise embedded HTML, citations and footnotes.
* **12-Factor Configuration** – Override behaviour via environment variables without touching code.
* **100 % Test Coverage** – Comprehensive pytest suite ensures reliability across updates.

---

## Why pmcgrab?
While the NCBI Entrez API already provides raw XML, consuming it directly is burdensome:

|                     | Entrez XML | pmcgrab JSON |
|---------------------|-----------:|-------------:|
| Section delineation | ❌          | ✅ |
| Straightforward to embed in vector DB | ❌ | ✅ |
| Ready for LLM chunking | ❌ | ✅ |
| Batch parallelism | Limited | Automatic |

Put simply, `pmcgrab` turns *publisher-centric* documents into *AI-centric* assets.

---

## Installation
### Requirements
* Python ≥ 3.9
* GCC or compatible compiler for `lxml` wheels on some platforms

### From PyPI
```bash
pip install pmcgrab
```

### From Source
```bash
git clone https://github.com/rajdeepmondaldotcom/pmcgrab.git
cd pmcgrab
pip install .
```

For optional development utilities:

```bash
pip install .[dev,test,docs]
```

---

## Quick Start (Python)
Fetch and inspect a single article:

```python
from pmcgrab import Paper

# NCBI requires an email for identification
paper = Paper.from_pmc("7181753", email="rajdeep@rajdeepmondal.com")

print(paper.title)
print(paper.body["Introduction"][:500])  # first 500 chars of Introduction
```

### Example: Process five PMC articles

Run the helper script located in `examples/run_five_pmcs.py`:

```bash
python examples/run_five_pmcs.py
```

The script will:

1. Download five predefined PMCIDs (see the source).
2. Print a brief summary for each article (title, abstract snippet, author count).
3. Persist the full JSON output into `pmc_output/PMC<id>.json` for further inspection.


---

## Command-Line Interface
Batch-process multiple PMCIDs directly from the shell:

```bash
python -m pmcgrab.cli.pmcgrab_cli \
  --pmcids 7181753 3539614 5454911 \
  --output-dir ./pmc_output \
  --batch-size 8
```

After completion you will find:
```
pmc_output/
├── PMC7181753.json
├── PMC3539614.json
└── PMC5454911.json
```

A `summary.json` file captures success/failure for each ID.

---

## Batch Processing & Scaling
Programmatic interface for large experiments:

```python
from pmcgrab.application.processing import process_pmc_ids

pmc_ids = ["7181753", "3539614", "5454911", ...]
stats = process_pmc_ids(pmc_ids, workers=32)

success_rate = sum(stats.values()) / len(stats)
print(f"{success_rate:%} downloaded successfully")
```

Internally, downloads are sharded across a thread pool and guarded by per-article timeouts.

---

## Output Schema
Below is an abridged view of the generated JSON (actual output contains >30 fields):

```json
{
  "pmc_id": "7181753",
  "title": "...",
  "abstract": "...",
  "authors": [
    {"Contributor_Type": "Author", "First_Name": "Llorenç", "Last_Name": "Solé-Boldo"}
  ],
  "body": {
    "Introduction": "The skin is the outermost protective barrier...",
    "Methods": "Clinical samples were obtained...",
    "Results": "...",
    "Discussion": "..."
  },
  "published_date": {"epub": "2020-04-23"},
  "journal_title": "Communications Biology"
}
```

This shape maps cleanly to embeddings or vector stores where section titles become metadata tags for context-aware retrieval.

---

## Configuration
`pmcgrab` follows the 12-factor methodology: **environment variables override defaults**.

| Variable            | Purpose                                                  | Default |
|---------------------|----------------------------------------------------------|---------|
| `PMCGRAB_EMAILS`    | Comma-separated pool of email addresses rotated for API  | Internal sample list |
| `PMCGRAB_WORKERS`   | Default worker count for batch processing (if not set programmatically) | `16` |

Set them in your shell or orchestrator:

```bash
export PMCGRAB_EMAILS="you@org.com,lab@org.com"
export PMCGRAB_WORKERS=32
```

---

## Logging
`pmcgrab` uses the standard Python `logging` library and leaves configuration to the host application:

```python
import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
```

Switch to `DEBUG` for verbose network and parsing diagnostics.

---

## Development
1. Clone the repository and install the dev extras:
   `pip install -e .[dev,test,docs]`
2. Run the test-suite (100 % coverage):
   `pytest -n auto --cov=pmcgrab`
3. Lint & type-check:
   `ruff check . && mypy src/pmcgrab`
4. Build documentation (MkDocs):
   `mkdocs serve`

Continuous Integration replicates the above on every pull request.

---

## Contributing
Contributions are welcome!  Please read the [CONTRIBUTING.md](CONTRIBUTING.md) (to be created) for details on:

* Code style and commit guidelines
* Branching and release process
* Reporting bugs or suggesting enhancements
* Security disclosures (please email the maintainer directly)

---

## License
`pmcgrab` is licensed under the [Apache 2.0](LICENSE) License.

---

## Citation
If this project contributes to your research, please consider citing it:

```bibtex
@software{pmcgrab,
  author       = {Rajdeep Mondal},
  title        = {pmcgrab: AI-ready retrieval of PubMed Central articles},
  year         = {2025},
  url          = {https://github.com/rajdeepmondaldotcom/pmcgrab},
  version      = {0.2.1},
  license      = {Apache-2.0}
}
```

---

## Acknowledgements
* The National Center for Biotechnology Information (NCBI) for maintaining PubMed Central.
* The open-source community behind **Biopython**, **BeautifulSoup**, **lxml** and other dependencies that make this project possible.

> **Disclaimer**
> Use of PubMed Central content is bound by the PMC terms of use.  Ensure you have the right to download and redistribute any article you process with `pmcgrab`.
