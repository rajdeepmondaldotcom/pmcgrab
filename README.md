# PMCGrab

[![PyPI](https://img.shields.io/pypi/v/pmcgrab.svg)](https://pypi.org/project/pmcgrab/)
[![Python](https://img.shields.io/pypi/pyversions/pmcgrab.svg)](https://pypi.org/project/pmcgrab/)
[![Docs](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://rajdeepmondaldotcom.github.io/pmcgrab/)
[![CI](https://github.com/rajdeepmondaldotcom/pmcgrab/workflows/CI/badge.svg)](https://github.com/rajdeepmondaldotcom/pmcgrab/actions)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/rajdeepmondaldotcom/pmcgrab/blob/main/LICENSE)

**A PMC ID in. Clean, loss-aware article JSON out.**

PMCGrab turns PubMed Central articles and JATS XML into structured JSON for
biomedical AI systems. It is built for developers and researchers who need
reliable article context for RAG, search, literature review, corpus builds, text
mining, and knowledge graphs.

Raw PMC XML is not a product interface. It is source material: nested sections,
reference maps, captions, formulas, tables, figure links, author metadata,
licenses, supplements, footnotes, and publisher-specific edge cases. One-off XML
parsers usually work until they quietly drop the field you needed.

PMCGrab gives you a clean boundary:

```bash
uv add pmcgrab
```

```python
from pmcgrab import process_single_pmc

article = process_single_pmc("7181753")

print(article["article"]["title"]["main"])
print([section["title"] for section in article["content"]["sections"]])
```

Give PMCGrab a PMC ID or a local JATS XML file. Get back article data you can
inspect, store, chunk, embed, audit, or pass to the next system.

## Why It Exists

Biomedical AI fails quietly when the context layer is messy.

If retrieval cannot tell Methods from Discussion, the model gets the wrong
evidence with confidence. If a parser drops captions, identifiers, equations,
supplements, or permissions, every downstream system inherits that loss and
still calls it data.

The bottleneck is not another prompt. It is clean, complete context.

PMCGrab is a small piece of infrastructure for that job. It does not try to be a
literature review product. It does not parse every document on the internet. It
does one thing: turn PMC article sources into usable Python objects and JSON.

## What You Get

- **Schema V4 JSON by default** with article metadata, contributors, content,
  assets, relations, quality, and provenance.
- **Loss-aware content parsing** for paragraphs, nested sections, lists,
  definition lists, boxed text, formulas, tables, figures, supplements, and
  unknown JATS blocks.
- **No raw XML in output JSON**. Source traceability is preserved through clean
  `source` metadata: JATS tag, attributes, path, and ordinal.
- **Two ingestion paths**: fetch by PMC ID from NCBI, or parse bulk-downloaded
  JATS XML from disk.
- **A practical Python API** for notebooks, scripts, ingestion workers, and
  corpus build jobs.
- **A CLI path** for turning lists of article IDs or local XML files into JSON
  files.
- **Release checks that match real use**: deterministic local XML tests, parser
  regressions, CLI tests, JSON serialization checks, docs build, package build,
  wheel smoke install, and opt-in live NCBI E2E.

## Current Verification

Last local verification: **2026-05-18**.

| Check                                                                | Result                                     |
| -------------------------------------------------------------------- | ------------------------------------------ |
| `uv run ruff check .`                                                | passed                                     |
| `uv run mypy src/pmcgrab`                                            | passed, no type issues                     |
| `uv run pytest -q --no-cov`                                          | `200 passed, 1 skipped`                    |
| `PMCGRAB_RUN_LIVE_E2E=1 uv run pytest tests/test_e2e.py -q --no-cov` | `2 passed`                                 |
| `uv build`                                                           | built sdist and wheel for `pmcgrab-1.0.10` |
| `uv run twine check dist/*`                                          | passed                                     |
| `uv run mkdocs build`                                                | docs built successfully                    |
| `bash scripts/smoke-wheel-install.sh`                                | built wheel imports successfully           |

The skipped test is the opt-in live NCBI E2E check. Run it explicitly with
`PMCGRAB_RUN_LIVE_E2E=1` when you want release confidence against the real
service.

## Install

Recommended:

```bash
uv add pmcgrab
```

With pip:

```bash
pip install pmcgrab
```

Python 3.10 or newer is required. The package is tested on Python 3.10, 3.11,
3.12, and 3.13.

Optional extras:

```bash
pip install "pmcgrab[test]"      # pytest and coverage tools
pip install "pmcgrab[docs]"      # MkDocs documentation tooling
pip install "pmcgrab[notebook]"  # Jupyter support
pip install "pmcgrab[dev]"       # development tooling
```

## The 30-Second Path

### Fetch One PMC Article

```python
from pmcgrab import process_single_pmc

article = process_single_pmc("7181753")

if article:
    print(article["article"]["identifiers"]["pmcid"])
    print(article["article"]["title"]["main"])
    print(article["content"]["sections"][0]["title"])
```

Use this when you want pipeline-ready dictionaries.

### Explore One Article As An Object

```python
from pmcgrab import Paper

paper = Paper.from_pmc("7181753", suppress_warnings=True)

print(paper.title)
print(paper.abstract_as_str()[:500])
print(paper.get_toc())

json_payload = paper.to_json()
```

Use `Paper` when you are exploring an article in a notebook or script.

### Parse Local PMC XML

```python
from pmcgrab import Paper, process_single_local_xml, process_local_xml_dir

paper = Paper.from_local_xml("./pmc_bulk/PMC7181753.xml")
article = process_single_local_xml("./pmc_bulk/PMC7181753.xml")
batch = process_local_xml_dir("./pmc_bulk", workers=16)
```

Local XML mode is the right path when you already have PMC bulk data on disk. It
does not call NCBI. It just parses the files.

### Use The CLI

```bash
# Fetch by PMC ID
pmcgrab --pmcids 7181753 3539614 --output-dir ./articles

# Parse a local XML directory
pmcgrab --from-dir ./pmc_bulk_xml --output-dir ./articles --workers 16

# Parse specific local XML files
pmcgrab --from-file PMC7181753.xml PMC3539614.xml --output-dir ./articles

# Write JSONL instead of one JSON file per article
pmcgrab --pmcids 7181753 3539614 --format jsonl --output-dir ./articles
```

## Output Shape

PMCGrab returns a JSON-serializable article dictionary with stable top-level
groups:

```json
{
  "schema_version": 4,
  "has_data": true,
  "article": {
    "identifiers": {
      "pmc_id": "7181753",
      "pmcid": "PMC7181753",
      "pmid": "32327715",
      "doi": "10.1038/s42003-020-0922-4"
    },
    "title": {
      "main": "Single-cell transcriptomes of the human skin reveal age-related loss of fibroblast priming"
    },
    "publication": {
      "journal": {
        "title": "Communications Biology"
      }
    },
    "metadata": {
      "keyword_groups": []
    }
  },
  "contributors": {
    "people": [],
    "affiliations": []
  },
  "content": {
    "abstracts": [
      {
        "title": "Abstract",
        "kind": "primary",
        "blocks": [
          {
            "type": "paragraph",
            "text": "..."
          }
        ]
      }
    ],
    "sections": [
      {
        "title": "Introduction",
        "level": 1,
        "blocks": [
          {
            "type": "paragraph",
            "text": "..."
          }
        ],
        "children": []
      }
    ]
  },
  "assets": {
    "references": [],
    "tables": [],
    "figures": [],
    "equations": {
      "records": [],
      "mathml": [],
      "tex": []
    }
  },
  "relations": [],
  "quality": {
    "status": "complete",
    "diagnostics": [],
    "coverage": {
      "unrepresented_text_count": 0,
      "generic_fallback_count": 0
    }
  },
  "provenance": {
    "pmcgrab_version": "1.0.10",
    "source": "ncbi_entrez"
  }
}
```

Text lives under `content`, article metadata lives under `article`, contributors
live under `contributors`, cross-reference and affiliation links live under
`relations`, and parse diagnostics live under `quality`. Pass
`schema_version=2` or `schema_version=3` to `process_single_pmc()`,
`process_single_local_xml()`, or `Paper.to_dict()` when you need an older
shape. V4 preserves source traceability through structured `source` metadata,
not raw XML payloads. Body content uses typed records for paragraphs, lists,
definition lists, boxed text, formulas, figures, tables, and supplements;
unsupported JATS blocks become `unknown_block` records instead of disappearing.
The JSON writer uses `allow_nan=False`, so invalid JSON values do not quietly
leak into output files.

## What Makes The JSON Useful

The default V4 output is designed to be consumed directly by downstream systems,
not reverse-engineered after parsing.

- **Readable text** stays easy to chunk and embed.
- **Structure** stays available for routing, filtering, and citation-aware
  workflows.
- **Assets** are promoted into dedicated records: references, tables, figures,
  equations, and supplementary material.
- **Relations** capture xrefs and contributor-affiliation links with target IDs
  and resolution status.
- **Quality** reports parser diagnostics, count mismatches, unresolved
  relations, fallback records, and coverage metadata.
- **Source traceability** is retained through `source.jats_tag`, `source.attrs`,
  `source.path`, and `source.ordinal`.

Example content blocks:

```json
{
  "title": "Results",
  "level": 1,
  "blocks": [
    {
      "type": "paragraph",
      "text": "The cohort showed improved response.",
      "inline": []
    },
    {
      "type": "list",
      "list_type": "order",
      "items": [
        {
          "type": "list_item",
          "text": "Primary endpoint was met."
        }
      ]
    },
    {
      "type": "formula",
      "label": "Eq. 1",
      "tex": "E=mc^2",
      "mathml": {
        "tag": "math",
        "attrs": {},
        "children": []
      }
    },
    {
      "type": "unknown_block",
      "jats_tag": "publisher-specific-block",
      "text": "Preserved fallback text.",
      "parse_status": "generic_fallback"
    }
  ]
}
```

## When To Use It

Use PMCGrab if you are building:

- a biomedical RAG pipeline
- a literature search or review tool
- a knowledge graph from PMC articles
- a text-mining corpus
- a repeatable dataset from PMC bulk XML
- a CLI workflow that turns article IDs into JSON files

Do not use PMCGrab if you need:

- arbitrary PDF parsing
- paywalled full text that is not available through PMC
- general web scraping
- clinical guidance or medical decisions

The scope is intentionally narrow: PMC and JATS article sources in, structured
Python objects and JSON out.

## Python API

### `Paper`

```python
from pmcgrab import Paper

paper = Paper.from_pmc("7181753")

paper.title
paper.authors
paper.article_id
paper.journal_title
paper.keywords
paper.citations
paper.tables
paper.figures

paper.abstract_as_str()
paper.abstract_as_dict()
paper.body_as_dict()
paper.body_as_nested_dict()
paper.body_as_paragraphs()
paper.full_text()
paper.get_toc()
paper.to_dict()
paper.to_json()
```

### Processing Helpers

```python
from pmcgrab import (
    process_local_xml_dir,
    process_single_local_xml,
    process_single_pmc,
)

one_from_network = process_single_pmc("7181753")
one_from_disk = process_single_local_xml("./pmc_bulk/PMC7181753.xml")
many_from_disk = process_local_xml_dir("./pmc_bulk", workers=16)
```

### CLI Input Modes

| Mode             | Use it when                                                                       |
| ---------------- | --------------------------------------------------------------------------------- |
| `--pmcids`       | You already have PMC IDs. `7181753`, `PMC7181753`, and `pmc7181753` are accepted. |
| `--pmids`        | You have PubMed IDs and want PMCGrab to resolve them to PMC IDs first.            |
| `--dois`         | You have DOIs and want PMCGrab to resolve them to PMC IDs first.                  |
| `--from-id-file` | You have a text file with one identifier per line.                                |
| `--from-dir`     | You have a directory of local `.xml` files.                                       |
| `--from-file`    | You want to parse specific local JATS XML files.                                  |

### NCBI Service Helpers

```python
from pmcgrab import (
    bioc_fetch,
    citation_export,
    id_convert,
    normalize_id,
    normalize_pmid,
    oa_fetch,
    oai_get_record,
    oai_list_identifiers,
    oai_list_records,
    oai_list_sets,
)
```

These are thin clients around NCBI and PMC services. They are useful when your
pipeline needs identifier conversion, citation export, BioC JSON, Open Access
metadata, or OAI-PMH harvesting.

## Configuration

PMCGrab reads configuration from environment variables:

| Variable             | Purpose                                           | Default            |
| -------------------- | ------------------------------------------------- | ------------------ |
| `PMCGRAB_EMAILS`     | Comma-separated contact emails for NCBI requests. | Maintainer contact |
| `NCBI_API_KEY`       | Optional NCBI API key.                            | None               |
| `PMCGRAB_TIMEOUT`    | Network timeout in seconds.                       | `60`               |
| `PMCGRAB_RETRIES`    | Retry count for Entrez calls.                     | `3`                |
| `PMCGRAB_SSL_VERIFY` | Whether to verify TLS certificates.               | `true`             |

For serious network use, set your own contact email. NCBI asks clients to
identify themselves.

```bash
export PMCGRAB_EMAILS="you@university.edu"
export NCBI_API_KEY="your_ncbi_api_key_here"
```

Without an NCBI API key, PMCGrab follows the lower public request limit. With an
API key, NCBI allows a higher request rate.

## Bulk PMC XML

For large jobs, local XML mode is usually the better path.

Download PMC Open Access XML from:

- PMC FTP: https://ftp.ncbi.nlm.nih.gov/pub/pmc/
- PMC Open Access subset: https://pmc.ncbi.nlm.nih.gov/tools/openftlist/

Then parse from disk:

```bash
pmcgrab --from-dir ./pmc_xml --output-dir ./pmc_json --workers 16
```

This avoids repeated network calls and gives you a repeatable corpus build.

## Verification Commands

Run the deterministic suite:

```bash
uv run pytest -q --no-cov
```

Run lint and type checks:

```bash
uv run ruff check .
uv run mypy src/pmcgrab
```

Build the docs:

```bash
uv run mkdocs build
```

Build and smoke-test the wheel:

```bash
uv build
bash scripts/smoke-wheel-install.sh
```

Run the live NCBI end-to-end smoke test only when you want release confidence
against the real service:

```bash
PMCGRAB_RUN_LIVE_E2E=1 uv run pytest tests/test_e2e.py -q --no-cov
```

The live test is opt-in because public services can fail for reasons that have
nothing to do with this package.

## Proof

Current release checks cover:

- public API imports and version metadata
- CLI help, version, input modes, and output writing
- local XML parsing for files and directories
- malformed XML and regression cases
- canonical JSON output without `NaN` literals
- wheel build and clean install smoke checks
- opt-in live NCBI fetch and parse smoke checks

That is the bar: the README examples should be true, the CLI should work from an
installed wheel, and the network path should be tested deliberately before a
release.

## Contributing

Contributions are welcome when they make the parser more correct, the output
contract clearer, or the package easier to use.

Start with [DEVELOPMENT.md](DEVELOPMENT.md). Keep changes narrow. Add the test
that would have failed before your change.

## License

Apache 2.0. See [LICENSE](LICENSE).

## The Ask

If PMCGrab saves you from writing another one-off XML parser, star the repo.

If it breaks on a real PMC article, open an issue with the PMCID or XML shape.
That is the fastest way to make the parser better for the next person.
