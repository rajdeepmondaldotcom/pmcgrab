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

By default, PMCGrab returns clean JSON only — no image downloads, no extra
round trips, fastest possible turnaround. When you need the figure binaries
next to the JSON, opt in with the asset orchestrator:

```python
from pmcgrab import AssetFetchPolicy, process_single_pmc_with_assets

article, fetch_result = process_single_pmc_with_assets(
    "7181753",
    out_dir="./pmc_output",
    policy=AssetFetchPolicy(fetch_images=True),
)
# ./pmc_output/PMC7181753/article.json + images/<figures>
for figure in article["assets"]["figures"]:
    print(figure["caption"], "->", figure["local_path"])
```

Or via the CLI:

```bash
# Fast default: one JSON per article, no images
pmcgrab --pmcids 7181753 3539614 --output-dir ./pmc_output
# ./pmc_output/PMC7181753.json
# ./pmc_output/PMC3539614.json

# Opt in to images and the folder layout
pmcgrab --pmcids 7181753 --with-images --output-dir ./pmc_output
# ./pmc_output/PMC7181753/article.json + images/<figures>
```

Give PMCGrab a PMC ID or a local JATS XML file. Get back article data you can
inspect, store, chunk, embed, audit, or pass to the next system — and pull
the images alongside the JSON when you actually need them.

## What's New In 2.0

- **Opt-in figure binaries.** The new `--with-images` flag (and the new
  `process_single_pmc_with_assets()` function) fetches the figure JPEG/TIFF/PNG
  files from the PMC Open Access service and writes them to disk next to
  the JSON. Each V4 figure record gains `local_path`, `download_status`,
  and `download_source` fields so downstream code can load the binary
  alongside its caption.
- **Fast by default.** The default CLI behaviour and the `process_single_pmc()`
  function are unchanged from 1.x: one Entrez fetch, JSON only, one flat file
  per article. No image downloads, no extra round trips. Existing pipelines
  upgrade transparently.
- **OA service helpers.** `list_oa_links()` and `tgz_url_for()` expose the
  PMC Open Access Web Service catalog so you can build your own asset
  fetchers if needed. `oa_fetch()` is now functional after a 1.x bug fix
  (the legacy implementation passed the wrong query parameter and silently
  always returned `None`).
- **Schema additions are non-breaking.** All new fields default to empty
  string / `"not_attempted"`. Consumers that ignore them see the same V4
  shape as 1.x.

See [CHANGELOG.md](CHANGELOG.md) for the full release notes.

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
- **Fast default, opt-in images.** The CLI default emits one `PMC{id}.json`
  per article — no image downloads, no extra round trips. Pass `--with-images`
  (or call `process_single_pmc_with_assets()` programmatically) when you also
  want the figure binaries on disk and the per-article folder layout.
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

Last local verification: **2026-05-19**.

| Check                                                                | Result                                    |
| -------------------------------------------------------------------- | ----------------------------------------- |
| `uv run ruff check .`                                                | passed                                    |
| `uv run mypy src/pmcgrab`                                            | passed, no type issues                    |
| `uv run pytest -q --no-cov`                                          | `235 passed, 2 skipped`                   |
| `PMCGRAB_RUN_LIVE_E2E=1 uv run pytest tests/test_e2e.py -q --no-cov` | `3 passed`                                |
| `uv run python scripts/test_images.py --seed 7`                      | `10/10 parsed, 10/10 image batches`       |
| `uv build`                                                           | built sdist and wheel for `pmcgrab-2.0.0` |
| `uv run twine check dist/*`                                          | passed                                    |
| `uv run mkdocs build`                                                | docs built successfully                   |
| `bash scripts/smoke-wheel-install.sh`                                | built wheel imports successfully          |

The two skipped tests are the opt-in live NCBI E2E checks. Run them explicitly
with `PMCGRAB_RUN_LIVE_E2E=1` when you want release confidence against the real
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

### Fetch One PMC Article (Fast, JSON Only)

```python
from pmcgrab import process_single_pmc

article = process_single_pmc("7181753")

if article:
    print(article["article"]["identifiers"]["pmcid"])
    print(article["article"]["title"]["main"])
    print(article["content"]["sections"][0]["title"])
```

This is the fast path: one Entrez fetch, one parse, no binary downloads.
Use it when you want pipeline-ready dictionaries.

### Fetch One PMC Article With Figure Binaries

```python
from pmcgrab import AssetFetchPolicy, process_single_pmc_with_assets

article, fetch_result = process_single_pmc_with_assets(
    "7181753",
    out_dir="./pmc_output",
    policy=AssetFetchPolicy(fetch_images=True),
)

if article:
    for figure in article["assets"]["figures"]:
        print(figure["label"], figure["caption"][:80])
        print("  saved at:", figure["local_path"])  # e.g. images/foo.jpg
    print("downloaded", fetch_result.bytes_downloaded, "bytes via",
          fetch_result.sources_tried)
```

Use this when you also want the JPEG/TIFF/PNG figure files written next to
the JSON. See [Working With Figures](#working-with-figures) for details.

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
# Default: fetch by PMC ID, one flat JSON file per article (no images)
pmcgrab --pmcids 7181753 3539614 --output-dir ./articles
# ./articles/PMC7181753.json
# ./articles/PMC3539614.json
# ./articles/summary.json

# Opt in to images and the per-article folder layout
pmcgrab --pmcids 7181753 --with-images --output-dir ./articles
# ./articles/PMC7181753/article.json
# ./articles/PMC7181753/images/*.jpg

# Also pull supplementary files (PDFs, datasets, videos)
pmcgrab --pmcids 7181753 --with-images --include-supplementary \
    --output-dir ./articles

# Parse a local XML directory (offline, no image fetching)
pmcgrab --from-dir ./pmc_bulk_xml --output-dir ./articles --workers 16

# Parse specific local XML files
pmcgrab --from-file PMC7181753.xml PMC3539614.xml --output-dir ./articles

# Write JSONL instead of one JSON file per article
pmcgrab --pmcids 7181753 3539614 --format jsonl --output-dir ./articles
```

The CLI is fast by default and only does the extra work of downloading figure
binaries when you explicitly ask. Run `pmcgrab --help` for the full flag list.

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
    "pmcgrab_version": "2.0.0",
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

V4 figure and supplementary records also expose three asset-tracking fields
(`local_path`, `download_status`, `download_source`) that stay empty / set to
`"not_attempted"` on the fast default path and only get populated when you
ask for images via `--with-images` / `process_single_pmc_with_assets()`. See
[Working With Figures](#working-with-figures).

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

## Working With Figures

PMCGrab can return the figure metadata only (fast default) or also fetch the
binary images and write them to disk alongside the JSON. The image path is
explicitly opt-in because OA package downloads add 1–15 seconds per article
and 0.1–5 MB of data per article that most callers never need.

### Decide Which Path You Want

| You want                                                 | Use                                                   |
| -------------------------------------------------------- | ----------------------------------------------------- |
| JSON only, fastest possible turnaround                   | `process_single_pmc()` or `pmcgrab --pmcids ...`      |
| JSON plus figure JPEG/TIFF/PNG files on disk             | `process_single_pmc_with_assets()` or `--with-images` |
| JSON plus figures plus supplementary files (PDFs, etc.)  | `--with-images --include-supplementary`               |
| JSON plus figures plus the raw JATS XML for traceability | `--with-images --include-raw-xml`                     |
| Every file in the OA tar.gz (figures, supp, XML, PDFs)   | `--with-images --include-all-assets`                  |

### Output Layout

The two paths produce different layouts:

```
# Default (--format json, no --with-images)
./pmc_output/
    PMC7181753.json            ← one flat JSON file per article
    PMC3539614.json
    summary.json               ← { "7181753": true, "3539614": true }

# With --with-images
./pmc_output/
    PMC7181753/
        article.json           ← the same V4 JSON
        images/
            42003_2020_922_Fig1_HTML.jpg
            42003_2020_922_Fig2_HTML.jpg
            ...
        supplementary/         ← only with --include-supplementary
            41586_2020_2832_MOESM1_ESM.pdf
        raw.xml                ← only with --include-raw-xml
    PMC3539614/
        article.json
        images/...
    summary.json               ← { "7181753": { "parsed": true,
                                                "asset_status": "complete",
                                                "image_count": 6,
                                                "image_downloaded": 6,
                                                "bytes_downloaded": 814322 } }
```

### How The Binaries Are Sourced

PMCGrab tries two sources in order:

1. **Primary — PMC Open Access tar.gz.** One HTTPS request fetches every
   figure and supplementary file bundled with the original JATS `xlink:href`
   filenames. This works for any article in the PMC OA subset.
2. **Fallback — per-file `bin/` URL.** If the OA bundle is unavailable or
   missing a referenced filename, PMCGrab tries
   `https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{id}/bin/{href}` per file.

Both paths respect the existing NCBI rate limiter. The tar.gz path is
stream-extracted; the package never buffers a large archive in memory.

Articles that are not in the OA subset (NIHMS author manuscripts, paywalled
content) will see both sources fail. PMCGrab still writes the JSON; the
affected figure records carry `download_status: "missing"` and the
`quality.diagnostics` entry with code `asset_fetch_summary` records what
was attempted.

### Figure Records With Local Paths

Each figure in `assets.figures` carries three asset-tracking fields:

```json
{
  "id": "f1",
  "label": "Figure 1",
  "caption": "Single-cell transcriptomes...",
  "link": "42003_2020_922_Fig1_HTML.jpg",
  "local_path": "images/42003_2020_922_Fig1_HTML.jpg",
  "download_status": "downloaded",
  "download_source": "oa_package",
  "graphics": [
    {
      "href": "42003_2020_922_Fig1_HTML.jpg",
      "mime_type": "image/jpeg",
      "local_path": "images/42003_2020_922_Fig1_HTML.jpg",
      "download_status": "downloaded"
    }
  ]
}
```

`local_path` is a POSIX path relative to `article.json`, so iteration
in downstream code is straightforward:

```python
from pathlib import Path
import json

article_dir = Path("./pmc_output/PMC7181753")
article = json.loads((article_dir / "article.json").read_text())

for figure in article["assets"]["figures"]:
    if figure["local_path"]:
        img_bytes = (article_dir / figure["local_path"]).read_bytes()
        # do something with img_bytes alongside figure["caption"]
```

Status values you may see on a figure record:

| `download_status` | Meaning                                              |
| ----------------- | ---------------------------------------------------- |
| `not_attempted`   | Image fetching was not enabled for this run.         |
| `not_available`   | The JATS source had no `xlink:href` for this figure. |
| `missing`         | Both the OA bundle and the `bin/` fallback failed.   |
| `downloaded`      | A file was written to `local_path`.                  |

### Diagnostic Summary

Every run that touches the asset fetcher appends an info-level entry to
`quality.diagnostics`:

```json
{
  "severity": "info",
  "code": "asset_fetch_summary",
  "message": "Downloaded 6/6 figures, 0/0 supplementary",
  "details": {
    "status": "complete",
    "sources_tried": ["oa_package"],
    "bytes_downloaded": 5210122,
    "image_count": 6,
    "image_downloaded": 6,
    "supplementary_count": 0,
    "supplementary_downloaded": 0,
    "errors": []
  }
}
```

`details.errors` is a list of `{href, reason, code}` records; the codes
are stable strings (`oa_not_available`, `oa_tgz_http_error`, `bin_not_found`,
`tar_unsafe_member`, `asset_size_limit`, etc.) so downstream code can act
on them programmatically.

### Tuning The Fetch

```python
from pmcgrab import AssetFetchPolicy

policy = AssetFetchPolicy(
    fetch_images=True,
    fetch_supplementary=True,        # PDFs, datasets, videos
    include_all_assets=False,        # True extracts every tar member
    save_raw_xml=True,               # writes raw.xml next to article.json
    max_total_bytes=256 * 1024 * 1024,
    per_request_timeout=30,
    use_oa_bundle_first=True,
    fallback_to_bin=True,
)
```

The same flags are exposed on the CLI as `--include-supplementary`,
`--include-all-assets`, `--include-raw-xml`, and `--max-asset-bytes`.

### Safety

- **Tar-slip protection.** Every member's resolved path is checked against
  the resolved target directory; entries that escape are rejected.
- **No symlinks or device files.** Only regular tar entries are extracted.
- **Per-article size ceiling.** The fetcher aborts mid-stream and removes
  partials if a single article exceeds `max_total_bytes` (default 256 MiB,
  configurable via the `PMCGRAB_MAX_ASSET_BYTES` environment variable).
- **Idempotent.** Files already on disk in the article's `images/` folder
  are not re-fetched. Re-running the same command resumes cleanly.

### Smoke-Testing The Pipeline

A standalone runner exercises the full asset path against a curated pool of
known-OA articles:

```bash
# 10 random PMC IDs from a 50-entry OA pool
uv run python scripts/test_images.py

# Reproducible run with a seed
uv run python scripts/test_images.py --seed 42

# Override the sample with explicit IDs
uv run python scripts/test_images.py --pmcids 7181753 3539614 6535064

# Keep the downloaded artifacts to inspect them
uv run python scripts/test_images.py --keep --out-dir /tmp/pmc-smoke
```

It prints a markdown summary table with per-article figure counts, download
counts, byte totals, sources tried, and status. Exit code is non-zero if
any article failed completely.

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

### Asset-Aware Processing

```python
from pmcgrab import (
    AssetFetchPolicy,
    AssetFetchResult,
    process_single_pmc_with_assets,
)

article, fetch_result = process_single_pmc_with_assets(
    "7181753",
    out_dir="./pmc_output",
    policy=AssetFetchPolicy(fetch_images=True),
)
# article is the same V4 dict; fetch_result.image_paths maps href -> local path
```

`process_single_pmc_with_assets()` wraps `process_single_pmc()`, downloads
the figure binaries via the PMC OA service (with a per-file fallback), and
writes the per-article folder (`PMC{id}/article.json` + `images/`). See
[Working With Figures](#working-with-figures) for the full surface.

### Open Access Service Helpers

```python
from pmcgrab import list_oa_links, oa_fetch, tgz_url_for

# Every <link> element from the OA Web Service response (preserves multiplicity)
links = list_oa_links("PMC7181753")
# [{"format": "tgz", "href": "ftp://.../PMC7181753.tar.gz", "updated": "..."}]

# HTTPS-rewritten URL of the OA tar.gz package (or None if not OA)
package_url = tgz_url_for("7181753")

# Flattened single-record helper (legacy; prefer list_oa_links for new code)
metadata = oa_fetch("PMC7181753")
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

### CLI Asset Flags

These flags are off by default and only take effect when `--with-images` is
passed. The default fast path skips all of this.

| Flag                      | Effect                                                              |
| ------------------------- | ------------------------------------------------------------------- |
| `--with-images`           | Download figure binaries; switch to per-article folder layout.      |
| `--include-supplementary` | Also fetch supplementary files (PDFs, datasets, videos).            |
| `--include-raw-xml`       | Save the original JATS XML as `raw.xml` inside each article folder. |
| `--include-all-assets`    | Extract every file in the OA tar.gz, including unreferenced ones.   |
| `--max-asset-bytes N`     | Per-article ceiling in bytes (default `268435456` = 256 MiB).       |

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

| Variable                  | Purpose                                              | Default               |
| ------------------------- | ---------------------------------------------------- | --------------------- |
| `PMCGRAB_EMAILS`          | Comma-separated contact emails for NCBI requests.    | Maintainer contact    |
| `NCBI_API_KEY`            | Optional NCBI API key.                               | None                  |
| `PMCGRAB_TIMEOUT`         | Network timeout in seconds.                          | `60`                  |
| `PMCGRAB_RETRIES`         | Retry count for Entrez calls.                        | `3`                   |
| `PMCGRAB_SSL_VERIFY`      | Whether to verify TLS certificates.                  | `true`                |
| `PMCGRAB_MAX_ASSET_BYTES` | Per-article ceiling for OA-bundle / image downloads. | `268435456` (256 MiB) |

For serious network use, set your own contact email. NCBI asks clients to
identify themselves.

```bash
export PMCGRAB_EMAILS="you@university.edu"
export NCBI_API_KEY="your_ncbi_api_key_here"
export PMCGRAB_MAX_ASSET_BYTES=$((512 * 1024 * 1024))   # raise to 512 MiB
```

Without an NCBI API key, PMCGrab follows the lower public request limit. With an
API key, NCBI allows a higher request rate.

`PMCGRAB_MAX_ASSET_BYTES` is only consulted when you use `--with-images` or
`process_single_pmc_with_assets()`. The asset fetcher aborts mid-stream and
removes any partials if a single article exceeds the ceiling.

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

Local XML mode is offline: image fetching is intentionally skipped because
a JATS XML file does not always carry a reliable PMCID and PMCGrab refuses
to make unsolicited network calls in offline mode. Pass `--with-images`
together with `--pmcids` (network mode) if you also want the figure binaries.

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
- CLI help, version, input modes, output writing, and asset flag parsing
- local XML parsing for files and directories
- malformed XML and regression cases
- canonical JSON output without `NaN` literals
- the asset fetcher: in-memory tar.gz streaming, basename filtering,
  tar-slip rejection, size-ceiling abort, OA-not-available fallback,
  `bin/` 404 handling, rate-limit invocation, idempotent re-runs
- the orchestrator: folder layout creation, `local_path` injection on
  figures and graphics, `asset_fetch_summary` diagnostic emission
- wheel build and clean install smoke checks
- opt-in live NCBI fetch and parse smoke checks (with and without images)
- a 10-PMC randomized smoke runner against a 50-entry OA pool

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
