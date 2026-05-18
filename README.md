# PMCGrab

[![PyPI](https://img.shields.io/pypi/v/pmcgrab.svg)](https://pypi.org/project/pmcgrab/)
[![Python](https://img.shields.io/pypi/pyversions/pmcgrab.svg)](https://pypi.org/project/pmcgrab/)
[![Docs](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://rajdeepmondaldotcom.github.io/pmcgrab/)
[![CI](https://github.com/rajdeepmondaldotcom/pmcgrab/workflows/CI/badge.svg)](https://github.com/rajdeepmondaldotcom/pmcgrab/actions)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/rajdeepmondaldotcom/pmcgrab/blob/main/LICENSE)

**PMC ID in. Clean paper JSON out. Add images when you need them.**

PMCGrab turns PubMed Central articles and JATS XML into structured JSON for
biomedical ingestion pipelines. The default output is the paper itself:
title, abstract, body, figures, and tables. Parser diagnostics, provenance,
relationship maps, and legacy compatibility fields are available only when you
ask for full JSON.

Use it when you need clean article context for RAG, search, text mining,
knowledge graphs, literature review systems, or downstream jobs that need the
paper text and figure files together.

## Install

```bash
uv add pmcgrab
```

or:

```bash
pip install pmcgrab
```

Requires Python 3.10 or newer.

## Quick Start

### Clean JSON

```python
from pmcgrab import process_single_pmc

article = process_single_pmc("7181753")

print(article["schema"])                  # pmcgrab.paper.v1
print(article["identifiers"]["pmcid"])    # PMC7181753
print(article["paper"]["title"])

for section in article["paper"]["body"]:
    print(section["title"])
```

CLI:

```bash
pmcgrab --pmcids 7181753 3539614 --output-dir ./pmc_output
```

Output:

```text
./pmc_output/
  PMC7181753.json
  PMC3539614.json
  summary.json
```

### Clean JSON With Images

```python
from pathlib import Path

from pmcgrab import AssetFetchPolicy, process_single_pmc_with_assets

article, fetch = process_single_pmc_with_assets(
    "7181753",
    out_dir="./pmc_output",
    policy=AssetFetchPolicy(fetch_images=True),
)

article_dir = Path("./pmc_output/PMC7181753")

for image in article["assets"]["images"]:
    for file in image["files"]:
        if file.get("local_path"):
            image_bytes = (article_dir / file["local_path"]).read_bytes()
            caption = image["caption"]
```

CLI:

```bash
pmcgrab --pmcids 7181753 --with-images --output-dir ./pmc_output
```

Output:

```text
./pmc_output/
  PMC7181753/
    article.json
    images/
      42003_2020_922_Fig1_HTML.jpg
      42003_2020_922_Fig2_HTML.jpg
  summary.json
```

`article.json` is the same clean paper JSON. Image paths are stored at
`assets.images[].files[].local_path`, relative to `article.json`.

## Output Contract

Default output schema:

```json
{
  "schema": "pmcgrab.paper.v1",
  "has_data": true,
  "identifiers": {
    "pmcid": "PMC7181753",
    "pmid": "32327715",
    "doi": "10.1038/s42003-020-0922-4"
  },
  "paper": {
    "title": "Single-cell transcriptomes of the human skin reveal ...",
    "abstract": [
      {
        "title": "Abstract",
        "content": [{ "type": "paragraph", "text": "..." }],
        "sections": []
      }
    ],
    "body": [
      {
        "title": "Introduction",
        "content": [{ "type": "paragraph", "text": "..." }],
        "sections": []
      }
    ]
  },
  "assets": {
    "images": [
      {
        "id": "f1",
        "label": "Figure 1",
        "caption": "...",
        "files": [
          {
            "href": "42003_2020_922_Fig1_HTML.jpg",
            "local_path": "images/42003_2020_922_Fig1_HTML.jpg",
            "status": "downloaded",
            "mime_type": "image/jpeg"
          }
        ]
      }
    ],
    "tables": []
  }
}
```

The clean contract intentionally excludes:

- parser provenance
- source XML paths
- relationship graphs
- author and affiliation metadata
- bibliography records
- diagnostics and quality counters
- old schema compatibility fields

Use full JSON when you need those fields:

```python
article = process_single_pmc("7181753", output_style="full")
```

```bash
pmcgrab --pmcids 7181753 --full-json --output-dir ./pmc_output
```

Older compatibility shapes remain available only through full JSON:

```python
article = process_single_pmc(
    "7181753",
    output_style="full",
    schema_version=2,
)
```

```bash
pmcgrab --pmcids 7181753 --full-json --schema-version 2
```

## Content Blocks

Sections contain ordered `content` blocks plus nested `sections`.

Common block types:

- `paragraph`: `text`
- `list`: `list_type`, `items`
- `definition_list`: `title`, `items`
- `formula`: `label`, `text`, `tex`, `mathml`
- `figure_ref`: `target_id`, `label`
- `table_ref`: `target_id`, `label`
- `quote`, `statement`, `boxed_text`: `content`, `text`
- `code`, `preformat`: `language`, `text`
- `unknown_block`: `jats_tag`, `text`, `children`

Unknown meaningful JATS blocks are preserved as readable fallback records
instead of being dropped.

## Image Fetching

Image fetching is off by default. `--with-images` and
`process_single_pmc_with_assets()` do extra network work:

1. Fetch the paper XML from NCBI.
2. Parse clean paper JSON.
3. Try the PMC Open Access tar.gz package.
4. Fall back to per-file `/bin/` image URLs when needed.
5. Write `PMC{id}/article.json` plus downloaded files.

Image file status values:

- `not_attempted`: image fetching was not enabled.
- `not_available`: the figure has no usable file reference.
- `missing`: PMCGrab tried but could not download the file.
- `downloaded`: the file was written to `local_path`.

Supplementary files are opt-in:

```bash
pmcgrab --pmcids 7181753 \
  --with-images \
  --include-supplementary \
  --output-dir ./pmc_output
```

Other asset flags:

- `--include-raw-xml`: save the source JATS XML as `raw.xml`.
- `--include-all-assets`: extract every file in the OA bundle.
- `--max-asset-bytes N`: set the per-article asset ceiling.

Safety defaults:

- tar paths are checked before extraction
- symlinks and device files are rejected
- partial downloads are removed on size-limit abort
- existing files are reused on reruns

## Local XML

Parse local JATS XML without network calls:

```python
from pmcgrab import process_local_xml_dir, process_single_local_xml

article = process_single_local_xml("./pmc_bulk/PMC7181753.xml")
batch = process_local_xml_dir("./pmc_bulk", workers=16)
```

CLI:

```bash
pmcgrab --from-file PMC7181753.xml --output-dir ./pmc_output
pmcgrab --from-dir ./pmc_bulk --workers 16 --output-dir ./pmc_output
```

Local XML mode does not download images. Use PMCID network mode with
`--with-images` when you need figure binaries.

## CLI Reference

Common input modes:

```bash
pmcgrab --pmcids 7181753 3539614 --output-dir ./out
pmcgrab --pmids 32327715 --output-dir ./out
pmcgrab --dois 10.1038/s42003-020-0922-4 --output-dir ./out
pmcgrab --from-id-file ids.txt --output-dir ./out
pmcgrab --from-dir ./xml --workers 16 --output-dir ./out
pmcgrab --from-file one.xml two.xml --output-dir ./out
```

Output modes:

```bash
# Default: clean paper JSON, one file per article.
pmcgrab --pmcids 7181753 --output-dir ./out

# Clean paper JSON plus image files.
pmcgrab --pmcids 7181753 --with-images --output-dir ./out

# JSONL instead of per-article files.
pmcgrab --pmcids 7181753 3539614 --format jsonl --output-dir ./out

# Metadata-rich full JSON.
pmcgrab --pmcids 7181753 --full-json --output-dir ./out
```

Run `pmcgrab --help` for every flag.

## Python API

```python
from pmcgrab import (
    AssetFetchPolicy,
    Paper,
    process_local_xml_dir,
    process_single_local_xml,
    process_single_pmc,
    process_single_pmc_with_assets,
)

article = process_single_pmc("7181753")
article, fetch = process_single_pmc_with_assets(
    "7181753",
    out_dir="./out",
    policy=AssetFetchPolicy(fetch_images=True),
)

paper = Paper.from_pmc("7181753")
paper.title
paper.abstract_as_str()
paper.get_toc()
paper.to_dict()
```

NCBI and PMC helper clients are also exported:

```python
from pmcgrab import (
    bioc_fetch,
    citation_export,
    id_convert,
    list_oa_links,
    normalize_id,
    normalize_pmid,
    oa_fetch,
    oai_get_record,
    oai_list_identifiers,
    oai_list_records,
    oai_list_sets,
    tgz_url_for,
)
```

## Configuration

- `PMCGRAB_EMAILS`: contact emails for NCBI requests. Default: maintainer contact.
- `NCBI_API_KEY`: optional NCBI API key. Default: unset.
- `PMCGRAB_TIMEOUT`: network timeout in seconds. Default: `60`.
- `PMCGRAB_RETRIES`: retry count for Entrez calls. Default: `3`.
- `PMCGRAB_SSL_VERIFY`: verify TLS certificates. Default: `true`.
- `PMCGRAB_MAX_ASSET_BYTES`: per-article asset download ceiling. Default:
  `268435456`.

For serious network use:

```bash
export PMCGRAB_EMAILS="you@university.edu"
export NCBI_API_KEY="your_ncbi_api_key_here"
```

## Verification

Release checks:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/pmcgrab
uv run pytest -q --no-cov
uv build
bash scripts/smoke-wheel-install.sh
```

Optional live NCBI smoke test:

```bash
PMCGRAB_RUN_LIVE_E2E=1 uv run pytest tests/test_e2e.py -q --no-cov
```

The live test is opt-in because public services can fail independently of this
package.

## Release

Releases are published from `main` through GitHub Actions:

1. Merge the release commit to `main`.
2. Run **Release from main**.
3. The workflow creates `vX.Y.Z`.
4. The tag workflow builds, tests, publishes to PyPI, and creates the GitHub
   Release.

Do not publish production packages from a laptop unless the GitHub pipeline is
unavailable and the failure mode is understood.

## License

Apache 2.0. See [LICENSE](LICENSE).
