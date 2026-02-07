# PMCGrab -- From PubMed Central ID to AI-Ready JSON in Seconds

[![PyPI](https://img.shields.io/pypi/v/pmcgrab.svg)](https://pypi.org/project/pmcgrab/) [![Python](https://img.shields.io/pypi/pyversions/pmcgrab.svg)](https://pypi.org/project/pmcgrab/) [![Docs](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://rajdeepmondaldotcom.github.io/pmcgrab/) [![CI](https://github.com/rajdeepmondaldotcom/pmcgrab/workflows/CI/badge.svg)](https://github.com/rajdeepmondaldotcom/pmcgrab/actions) [![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/rajdeepmondaldotcom/pmcgrab/blob/main/LICENSE)

Every AI workflow that touches biomedical literature hits the same wall:

1. **Download** PMC XML hoping it's "structured."
2. **Fight** nested tags, footnotes, figure refs, and half-broken links.
3. **Hope** your regex didn't blow away the Methods section you actually need.

That wall steals hours from **RAG pipelines, knowledge-graph builds, LLM fine-tuning -- any downstream AI task**.

**PMCGrab knocks it down.** Feed it a list of PMC IDs -- or point it at a directory of bulk-downloaded XML -- and get back clean, section-aware JSON you can drop straight into a vector DB or LLM prompt. No network required for local files. No timeouts. No XML wrestling.

---

## The Hidden Cost of "I'll Just Parse It Myself"

| Task                        | Manual / ad-hoc         | **PMCGrab**                                  |
| --------------------------- | ----------------------- | -------------------------------------------- |
| Install dependencies        | 5-10 min                | **~2 s** (`uv add pmcgrab`)                  |
| Convert one article to JSON | 15-30 min               | **~3 s** (network) / **instant** (local XML) |
| Capture every IMRaD section | Hope & regex            | **98 % detection accuracy\***                |
| Parallel processing         | Bash loops & temp files | `--workers N` flag                           |
| Edge-case maintenance       | Yours forever           | **200+ tests**, active upkeep                |

**\*Evaluated on 7,500 PMC papers used in a disease-specific knowledge-graph pipeline.**

At \$50/hour, hand-parsing 100 papers burns **\$1,000+**.
PMCGrab does the same job for \$0 -- within minutes -- so you can focus on _using_ the information instead of extracting it.

---

## Quick Install

**Recommended** (via [uv](https://docs.astral.sh/uv/)):

```bash
uv add pmcgrab
```

Or with pip:

```bash
pip install pmcgrab
```

Python >= 3.10 required. Tested on 3.10, 3.11, 3.12, and 3.13.

**Optional extras:**

```bash
pip install pmcgrab[dev]       # Linting, type-checking, pre-commit
pip install pmcgrab[test]      # pytest + coverage
pip install pmcgrab[docs]      # MkDocs + Material theme
pip install pmcgrab[notebook]  # Jupyter support
```

---

## 30-Second Quick Start

```python
from pmcgrab import Paper

paper = Paper.from_pmc("7181753")

print(paper.title)
# => "Single-cell transcriptomes of the human skin reveal age-related loss of ..."

print(paper.abstract_as_str()[:200])
# => "Fibroblasts are an essential cell population for human skin architecture ..."

# Every section, clean and ready
for section, text in paper.body_as_dict().items():
    print(f"{section}: {len(text.split())} words")

# Save to JSON
paper.to_json()
```

That's it. One import, one line to fetch, structured data everywhere.

---

## Ways to Use PMCGrab

### 1. Python API -- the `Paper` class (recommended)

The `Paper` class is the primary interface. It wraps every piece of parsed data with convenient accessor methods.

**From the network:**

```python
from pmcgrab import Paper

paper = Paper.from_pmc("7181753", suppress_warnings=True)
```

**From a local XML file (no network needed):**

```python
paper = Paper.from_local_xml("path/to/PMC7181753.xml")
```

**Output methods -- choose the shape that fits your pipeline:**

```python
# Abstract
paper.abstract_as_str()          # Plain-text string
paper.abstract_as_dict()         # {"Background": "...", "Results": "..."}

# Body
paper.body_as_dict()             # Flat: {"Introduction": "...", "Methods": "..."}
paper.body_as_nested_dict()      # Hierarchical: preserves subsections
paper.body_as_paragraphs()       # List of dicts -- ideal for RAG chunking
                                 #   [{"section": "Methods", "text": "...", "paragraph_index": 0}, ...]

# Full text
paper.full_text()                # Abstract + body as one continuous string

# Table of contents
paper.get_toc()                  # ["Introduction", "Methods", "Results", ...]

# Serialization
paper.to_dict()                  # Full JSON-serializable dictionary
paper.to_json()                  # JSON string (pretty-printed)
```

**Metadata you can access directly:**

```python
paper.title                      # Article title
paper.authors                    # pandas DataFrame (names, emails, affiliations)
paper.journal_title              # "Genome Biology"
paper.article_id                 # {"pmcid": "PMC7181753", "doi": "10.1038/...", ...}
paper.keywords                   # ["fibroblasts", "aging", ...]
paper.published_date             # {"epub": "2020-04-24", ...}
paper.citations                  # Structured reference list
paper.tables                     # List of pandas DataFrames
paper.figures                    # Figure metadata + captions
paper.permissions                # Copyright, license info
paper.funding                    # Funding sources
paper.equations                  # MathML + TeX equations
# ... and 20+ more attributes (see "Extracted Metadata" below)
```

---

### 2. Dict-Based API (for data pipelines)

If you prefer raw dictionaries over the `Paper` object:

```python
from pmcgrab import process_single_pmc, process_single_local_xml

# From network
data = process_single_pmc("7181753")

# From local XML
data = process_single_local_xml("path/to/article.xml")

print(data["title"])
print(data["abstract_text"])       # Plain-text abstract
print(data["abstract"])            # Structured abstract (dict)
print(list(data["body"].keys()))   # Section titles
```

---

### 3. Bulk / Local XML Processing

> This feature was inspired by a great suggestion from [@vanAmsterdam](https://github.com/vanAmsterdam), who pointed out that working with [bulk-exported PMC data](https://pmc.ncbi.nlm.nih.gov/tools/ftp/#bulk) could be orders of magnitude faster than fetching articles one-by-one over the network.

**We built it.** Local XML processing skips the network entirely -- no HTTP requests, no timeouts, no rate limits. It is the fastest way to parse PMC articles at scale.

**Python API:**

```python
from pmcgrab import Paper, process_single_local_xml, process_local_xml_dir

# Single file
paper = Paper.from_local_xml("./pmc_bulk/PMC7181753.xml")

# Single file (dict output)
data = process_single_local_xml("./pmc_bulk/PMC7181753.xml")

# Entire directory -- concurrent with 16 workers by default
results = process_local_xml_dir("./pmc_bulk/", workers=16)
for filename, data in results.items():
    if data:
        print(f"{filename}: {data['title'][:60]}")
```

**CLI:**

```bash
# Process a directory of bulk-downloaded XML
pmcgrab --from-dir ./pmc_bulk_xml/ --output-dir ./results

# Process specific files
pmcgrab --from-file article1.xml article2.xml --output-dir ./results
```

**How to get bulk XML:** Download from the [PMC FTP service](https://ftp.ncbi.nlm.nih.gov/pub/pmc/) or the [PMC Open Access subset](https://pmc.ncbi.nlm.nih.gov/tools/openftlist/). Each `.xml` file is a standard JATS XML article that PMCGrab can parse directly.

---

### 4. Command Line

PMCGrab's CLI supports **six input modes**, all mutually exclusive:

```bash
# PMC IDs (accepts PMC7181753, pmc7181753, or just 7181753)
pmcgrab --pmcids 7181753 3539614 --output-dir ./results

# PubMed IDs (auto-converted to PMC IDs via NCBI API)
pmcgrab --pmids 33087749 34567890 --output-dir ./results

# DOIs (auto-converted to PMC IDs via NCBI API)
pmcgrab --dois 10.1038/s41586-020-2832-5 --output-dir ./results

# IDs from a text file (one per line -- PMCIDs, PMIDs, or DOIs)
pmcgrab --from-id-file ids.txt --output-dir ./results

# Local XML directory (bulk mode -- no network)
pmcgrab --from-dir ./xml_bulk/ --output-dir ./results

# Specific local XML files (no network)
pmcgrab --from-file article1.xml article2.xml --output-dir ./results
```

**Additional flags:**

| Flag                         | Description                                            | Default        |
| ---------------------------- | ------------------------------------------------------ | -------------- |
| `--output-dir` / `--out`     | Output directory for JSON files                        | `./pmc_output` |
| `--batch-size` / `--workers` | Number of concurrent worker threads                    | `10`           |
| `--format`                   | `json` (one file per article) or `jsonl` (single file) | `json`         |
| `--verbose` / `-v`           | Enable debug logging                                   | off            |
| `--quiet` / `-q`             | Suppress progress bars                                 | off            |

---

### 5. Async Support

For asyncio-based applications:

```python
import asyncio
from pmcgrab.application.processing import async_process_pmc_ids

results = asyncio.run(async_process_pmc_ids(
    ["7181753", "3539614", "3084273"],
    max_concurrency=10,
))

for pid, data in results.items():
    print(pid, "OK" if data else "FAIL")
```

---

### 6. Batch Processing

Process thousands of articles with built-in concurrency, retries, and rate-limit compliance:

```python
from pmcgrab import process_pmc_ids_in_batches

pmc_ids = ["7181753", "3539614", "5454911", "3084273"]
process_pmc_ids_in_batches(pmc_ids, "./output", batch_size=8)
```

---

## Output Example

Every parsed article produces a comprehensive JSON structure:

```json
{
  "pmc_id": "7181753",
  "title": "Single-cell transcriptomes of the human skin reveal ...",
  "abstract_text": "Fibroblasts are an essential cell population ...",
  "abstract": {
    "Abstract": "Fibroblasts are an essential cell population ..."
  },
  "body": {
    "Introduction": "The skin is the outermost protective barrier ...",
    "Results": "The anatomy of the skin can vary ...",
    "Discussion": "Single-cell transcriptomics currently represents ...",
    "Methods": "Skin specimens for single-cell RNA sequencing ..."
  },
  "body_nested": {
    "Results": {
      "scRNA-seq analysis of sun-protected human skin": { "_text": "..." },
      "Functional and spatial signatures": { "_text": "..." }
    }
  },
  "paragraphs": [
    {
      "section": "Introduction",
      "subsection": null,
      "paragraph_index": 0,
      "text": "..."
    }
  ],
  "authors": [
    {
      "First_Name": "...",
      "Last_Name": "...",
      "Email": "...",
      "Affiliations": "..."
    }
  ],
  "article_id": {
    "pmcid": "PMC7181753",
    "doi": "10.1038/s42003-020-0922-4",
    "pmid": "32327715"
  },
  "journal_title": "Communications Biology",
  "keywords": ["fibroblasts", "skin aging", "single-cell RNA-seq"],
  "published_date": { "epub": "2020-04-24" },
  "citations": [
    { "title": "...", "authors": "...", "doi": "...", "pmid": "..." }
  ],
  "tables": [{ "label": "Table 1", "caption": "...", "data": "..." }],
  "figures": [{ "label": "Fig. 1", "caption": "...", "graphic": "..." }],
  "permissions": {
    "Copyright Statement": "...",
    "License Type": "Creative Commons"
  },
  "funding": ["..."],
  "full_text": "..."
}
```

---

## Extracted Metadata -- Everything in One Object

The `Paper` class extracts and normalizes **40+ fields** from each PMC article:

**Content:**
title, subtitle, abstract (plain text + structured), body (flat / nested / paragraphs), full text, table of contents, footnotes, acknowledgements, notes, appendices, glossary

**Authors & Contributors:**
authors (as pandas DataFrame with names, emails, affiliations), non-author contributors, author notes

**Journal & Publication:**
journal ID, journal title, ISSN, publisher name & location, volume, issue, first/last page, elocation ID, article types, article categories

**Identifiers:**
PMC ID, PMID, DOI, publisher ID (all in one `article_id` dict)

**Dates:**
publication dates (epub, ppub, collection), manuscript history dates (received, accepted, revised)

**Scholarly Content:**
citations (structured with authors, title, DOI, PMID), tables (parsed to pandas DataFrames), figures (label, caption, graphic links, alt text), equations (MathML + TeX), supplementary materials

**Legal & Funding:**
permissions, copyright statement, license type, funding sources, ethics disclosures

**Additional:**
keywords, custom metadata, counts, self URIs, related articles, conference info, translated titles & abstracts, version history

---

## NCBI Service Clients

PMCGrab bundles lightweight clients for five NCBI APIs, all importable from the top level:

```python
from pmcgrab import bioc_fetch, id_convert, citation_export, oa_fetch
from pmcgrab import oai_get_record, oai_list_identifiers, oai_list_records, oai_list_sets
from pmcgrab import normalize_id, normalize_ids, normalize_pmid, normalize_pmids
```

| Client                   | What it does                                                         |
| ------------------------ | -------------------------------------------------------------------- |
| `bioc_fetch()`           | Fetch BioC JSON for Open Access articles                             |
| `id_convert()`           | Convert between PMC IDs, PMIDs, and DOIs                             |
| `normalize_id()`         | Normalize any ID format to a numeric PMC ID                          |
| `citation_export()`      | Export citations in MEDLINE, BibTeX, RIS, NBIB, or PubMed format     |
| `oa_fetch()`             | Check Open Access status and get download links                      |
| `oai_get_record()`       | Retrieve a single OAI-PMH metadata record                            |
| `oai_list_records()`     | Harvest metadata at scale with automatic resumption-token pagination |
| `oai_list_identifiers()` | List OAI-PMH identifiers for a date range or set                     |
| `oai_list_sets()`        | List available OAI-PMH sets                                          |

---

## Context Engineering: Why This Matters for LLMs

Large-language-model performance lives or dies on **context quality** -- the snippets you retrieve and feed back into the model:

- **RAG pipelines** need precise, de-duplicated passages to ground answers.
- **Knowledge-graph population** demands reliable section boundaries (e.g., Methods vs. Results) to classify triples accurately.
- **Fine-tuning & few-shot prompting** work best with noise-free, domain-specific examples.

PMCGrab _is_ a context-engineering tool: it converts messy XML into **clean, section-aware, UTF-8 JSON** that slots directly into embeddings, vector stores, or prompt templates. No preprocessing gymnastics, no guessing where the Methods section starts, no hallucinations from half-garbled text.

Better input --> better retrieval --> better answers.

---

## Why PMCGrab Beats Home-Grown Scripts

1. **Section-Aware Parsing**
   Detects IMRaD plus custom subsections like _Statistical Analysis_ -- crucial for accurate retrieval scoring.

2. **Resilient XML Cleaning**
   Removes cross-refs and figure stubs without dropping scientific content, preserving token-level fidelity for embeddings.

3. **True Concurrency**
   `--workers` fans out across CPU cores; automatic email rotation and a token-bucket rate limiter respect NCBI limits so large harvests don't throttle.

4. **Modern Python Stack**
   Type-safe (`mypy` strict mode), linted (`ruff`), CI-checked on Ubuntu, macOS, and Windows across Python 3.10-3.13.

5. **Bulk XML Support**
   Point at a directory of pre-downloaded JATS XML files and parse them locally -- orders of magnitude faster, no network required. Ideal for the [PMC FTP bulk export](https://ftp.ncbi.nlm.nih.gov/pub/pmc/).

---

## Configuration

PMCGrab follows the [12-factor app](https://12factor.net/) methodology. All settings are configurable via environment variables:

| Variable          | Description                                               | Default            |
| ----------------- | --------------------------------------------------------- | ------------------ |
| `PMCGRAB_EMAILS`  | Comma-separated email pool for NCBI Entrez authentication | Built-in test pool |
| `NCBI_API_KEY`    | NCBI API key -- enables 10 req/s instead of 3 req/s       | None               |
| `PMCGRAB_TIMEOUT` | Timeout in seconds for network operations                 | `60`               |
| `PMCGRAB_RETRIES` | Number of retry attempts for Entrez API calls             | `3`                |

**Rate limiting** is enforced automatically across all threads via a token-bucket limiter:

- **Without** an API key: 3 requests/second
- **With** an API key: 10 requests/second

To set your own email and API key:

```bash
export PMCGRAB_EMAILS="you@university.edu,colleague@lab.org"
export NCBI_API_KEY="your_ncbi_api_key_here"
```

---

## Proof at a Glance

| Metric                      | Value                  |
| --------------------------- | ---------------------- |
| Unit tests                  | **218**                |
| Branch coverage             | **95 %**               |
| Section detection accuracy  | **98 %**               |
| Median parse time / article | **3.1 s** (network)    |
| Local XML parse time        | **< 0.1 s**            |
| Largest batch processed     | **7,500 articles**     |
| CI platforms                | Ubuntu, macOS, Windows |
| Python versions tested      | 3.10, 3.11, 3.12, 3.13 |

---

## Acknowledgments

Special thanks to [@vanAmsterdam](https://github.com/vanAmsterdam) for [suggesting](https://github.com/rajdeepmondaldotcom/pmcgrab/issues) that PMCGrab support bulk-exported PMC data from disk. That idea led directly to the `--from-dir`, `--from-file`, and `Paper.from_local_xml()` features -- making local XML processing orders of magnitude faster than the network path. Community feedback like this makes PMCGrab better for everyone.

---

## Contributing

We welcome contributions. See [DEVELOPMENT.md](DEVELOPMENT.md) for setup instructions, testing, and CI details.

---

## License

Apache 2.0 -- see [LICENSE](LICENSE) for details.

---

## Install Now & Ship Real Results

```bash
uv add pmcgrab
```

Stop paying the **XML tax**. Start engineering context -- and building AI products that matter.
