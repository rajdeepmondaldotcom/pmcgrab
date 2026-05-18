# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.0.1] - 2026-05-19

### Changed
- Reworked the README tables into CommonMark-friendly lists so the PyPI package
  page renders the install path, output contract, asset flags, and configuration
  cleanly.

## [3.0.0] - 2026-05-19

### Added
- Added the clean paper output contract `pmcgrab.paper.v1`, now emitted by
  default from the CLI, `Paper.to_dict()`, `Paper.to_json()`, and the high-level
  processing helpers. The clean contract contains the paper itself:
  identifiers, title, abstract, body, images, and tables.
- Added `--full-json` and `output_style="full"` as the explicit escape hatch
  for metadata-rich V4 output.

### Changed
- Rewrote the README and public package copy around the clean default contract,
  image-enabled ingestion workflow, and full-JSON escape hatch.
- The default output is now clean paper JSON instead of the full V4 parser
  record. This is a breaking change for callers that read `article`, `content`,
  `relations`, `quality`, or `provenance` from default output. Pass
  `--full-json` or `output_style="full"` to keep using the V4 record.
- `--schema-version` is now accepted only with `--full-json`. Schema V2/V3 are
  compatibility modes for full output, not clean paper output.

### Migration
- If you want the new ingestion-friendly output, no migration is needed. Read
  `paper.title`, `paper.abstract`, `paper.body`, `assets.images`, and
  `assets.tables`.
- If you want the old metadata-rich V4 structure, add `--full-json` on the CLI
  or pass `output_style="full"` in Python.
- Switch to `process_single_pmc_with_assets()` or `--with-images` when you want
  image binaries on disk alongside the clean JSON.

## [2.0.0] - 2026-05-18

### Added
- Added opt-in figure-binary downloading for network-mode PMC fetches. Pass
  `--with-images` on the CLI to switch from the default fast flat-file output
  to a per-article folder layout (`PMC{id}/article.json` + `images/`).
- Added `process_single_pmc_with_assets(pmc_id, out_dir, *, policy=...)` as a
  top-level public API for fetching an article and its assets in one call.
  Returns `(article_dict, AssetFetchResult)`.
- Added `AssetFetchPolicy` and `AssetFetchResult` dataclasses.
- Added two new helpers on `pmcgrab.oa_service`: `list_oa_links` (preserves
  every `<link>` element from the OA Web Service response) and `tgz_url_for`
  (HTTPS-rewritten URL of the OA tar.gz package).
- Added CLI flags: `--with-images`, `--include-supplementary`,
  `--include-raw-xml`, `--include-all-assets`, `--max-asset-bytes`. The
  `--include-*` flags require `--with-images`.
- Added `local_path`, `download_status`, and `download_source` fields to V4
  figure records (and per-graphic entries within `graphics`). Supplementary
  material records gain the same three fields. Defaults are empty
  string / `"not_attempted"`, so the schema is additive for callers that
  never opt in to image downloads.
- Added `quality.diagnostics` entry with code `asset_fetch_summary` summarising
  the per-article fetch outcome (only present when `--with-images` is used).
- Added `PMCGRAB_MAX_ASSET_BYTES` environment variable for the per-article
  asset size ceiling (default 256 MiB).
- Added `scripts/test_images.py` for end-to-end validation across 10 random
  PMC IDs sampled from a curated 50+ known-OA pool.

### Fixed
- `pmcgrab.oa_service.fetch()` was silently broken in 1.x — it sent the OA
  Web Service a `pmcid=` parameter, which returns the catalog summary
  instead of an individual record, so the helper always returned `None`.
  The fix uses the documented `id=` parameter, which means `oa_fetch` now
  returns useful data for the first time.

### Changed
- The default CLI output remains a flat single-file layout
  (`out_dir/PMC{id}.json`) with no image downloads. The per-article folder
  layout and image fetching are opt-in via `--with-images`.

### Migration
- No CLI migration required for the fast default path; the 1.x command line
  continues to emit V4 JSON with no image downloads.
- Programmatic callers of `process_single_pmc()` still receive the V4 parser
  record in 2.0.0. Switch to `process_single_pmc_with_assets()` when you want
  images on disk.

## [1.0.10] - 2026-05-18

### Added
- Added schema V4 as the default output contract for `Paper.to_dict()`,
  `Paper.to_json()`, processing helpers, and CLI output.
- Added a loss-aware JATS record extractor for V4 body and abstract content.
- Added typed JSON blocks for paragraphs, sections, lists, definition lists,
  boxed text, quotes, statements, formulas, tables, figures, supplementary
  material, and unknown JATS blocks.
- Added structured V4 records for contributors, affiliations, article IDs,
  title records, keyword groups, subject groups, licenses, equations, tables,
  figures, supplementary material, relations, and coverage metadata.
- Added generic fallback records for unsupported meaningful JATS elements so
  their text, attributes, children, and source metadata are still represented.
- Added regression coverage proving sentinel text survives parsing without raw
  XML leaking into V4 JSON.

### Changed
- Reworked V4 JSON around `article`, `contributors`, `content`, `assets`,
  `relations`, `quality`, and `provenance`.
- Improved source traceability with clean `source.jats_tag`, `source.attrs`,
  `source.path`, and `source.ordinal` metadata instead of raw XML payloads.
- Represented MathML as JSON trees rather than XML markup strings.
- Renamed V4 date source text to `source_text`.
- Updated README, docs, package metadata, citation docs, and GitHub About for
  the loss-aware JSON positioning.

### Removed
- Removed raw XML payloads from public V4 JSON output.
- Removed raw-ish V4 fields such as `raw_text` and `citation_raw` from emitted
  V4 records.

## [1.0.9] - 2026-05-18

### Added
- Added deterministic local XML end-to-end coverage for the CLI output path.
- Added an opt-in live NCBI end-to-end smoke test for release validation.
- Added a reusable wheel install smoke script for release workflows.

### Changed
- Repositioned README, docs homepage, package metadata, and GitHub About around
  the biomedical RAG use case.
- Refined the docs hero and public copy to emphasize structured PMC context,
  local JATS XML processing, and verifiable release checks.
- Reused the shared wheel smoke script in tag and main release workflows.

## [1.0.8] - 2026-05-17

### Fixed
- Emit strict JSON by normalizing pandas/numpy missing values and non-finite
  floats to `null` before serialization.
- Restore DOI and PMID conversion by using the current NCBI ID Converter API
  endpoint.
- Return non-zero CLI statuses for invalid inputs and all-failed processing.
- Enable TLS certificate verification by default for network calls.
- Avoid creating a local `data/` directory unless XML caching is requested.

### Changed
- Updated public examples and claims to match the v2 grouped JSON schema and
  current project guarantees.

## [1.0.7] - 2026-03-02

### Fixed
- **XMLSyntaxError crash on papers with consecutive self-closing `<xref/>` tags**
  (e.g. PMC10576104): the `split_text_and_refs` regex was treating self-closing
  tags as paired opening tags, causing multiple sibling xrefs to be bundled into
  one invalid XML string that crashed `process_reference_map`. Fixed with a
  negative lookbehind (`(?<!/)>`) in the paired-tag regex alternative.
- **Wrong abstract selected when a paper has multiple `<abstract>` elements**
  (e.g. PMC10576104, PMC12590228, PMC4643452): the parser always picked
  `nodes[0]`, which is often a typed variant (`executive-summary`,
  `author-highlights`, etc.) rather than the main text abstract. Now prefers
  the untyped abstract; falls back to `nodes[0]` only when all abstracts carry
  a type attribute.
- **Raw XML markup leaking into abstract/body text for papers where `<list>`
  elements are nested inside `<p>` tags** (e.g. PMC12590228, PMC4643452):
  `TextParagraph` now pre-processes the paragraph element with a deep-copy pass
  that converts block elements (`<list>`, `<disp-formula>`, etc.) to plain text
  before serialisation, preventing `<list-item>` XML from appearing verbatim in
  extracted text.
- **`<title>`, `<list>`, `<disp-formula>` silently dropped when they appear as
  direct children of `<abstract>` or `<body>`**: `_collect_sections` now handles
  these with the same `_render_block_element` + synthetic `TextParagraph` path
  that `TextSection` already used internally.
- Added `MalformedRefTagWarning` and a defensive `try/except` around
  `ET.fromstring` in `process_reference_map` so any remaining malformed ref-map
  entries emit a warning and are skipped instead of crashing the parser.

### Added
- `_select_main_abstract` helper in `sections.py` for robust multi-abstract selection.
- `_flatten_block_elements_in_paragraph` helper in `model.py` for safe in-paragraph block rendering.
- `MalformedRefTagWarning` in `constants.py`.
- 17 regression tests in `tests/test_regression_bugs.py` covering all fixed cases.

## [0.2.3] - 2025-01-31

### Fixed
- Improved release workflow reliability
- Enhanced version detection logic

## [0.2.2] - 2025-01-31

### Added
- Automated GitHub releases
- Enhanced PyPI metadata with comprehensive keywords and classifiers
- Additional project URLs for better discoverability

### Changed
- Updated author email to correct address
- Improved project description

## [0.2.1] - 2025-01-31

### Added
- Enhanced README with comprehensive documentation
- Example script instructions
- Better project structure documentation

### Changed
- Updated repository URLs to correct GitHub organization

## [0.2.0] - 2025-01-31

### Added
- Initial release with core functionality
- PubMed Central article retrieval and parsing
- AI-ready JSON output format
- Batch processing capabilities
- Command-line interface
- Comprehensive test suite

### Features
- Fetch full-text articles using PMC IDs
- Convert XML to structured JSON
- Section-aware parsing (Introduction, Methods, Results, Discussion)
- Concurrent batch processing
- HTML cleaning and reference utilities
- 12-factor configuration support
