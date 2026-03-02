# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

## [Unreleased]

### Added
- Comprehensive CI/CD workflows
- Automated dependency updates
- Security scanning and vulnerability management
- Documentation generation and deployment
- Issue and PR templates
- Contributing guidelines
- Security policy

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
