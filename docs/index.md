---
title: Home
template: home.html
hide:
  - navigation
  - toc
---

## A PMC ID in. Clean article JSON out.

```bash
uv add pmcgrab
```

```python
from pmcgrab import process_single_pmc

article = process_single_pmc("7181753")

print(article["article"]["title"]["main"])
print([section["title"] for section in article["content"]["sections"]])
```

PMCGrab turns a PMC ID or local JATS XML file into loss-aware article data you
can store, chunk, embed, inspect, audit, or pass to the next system.

## Why it exists

Biomedical AI fails quietly when the context layer is messy.

If retrieval cannot tell Methods from Discussion, the model gets the wrong
evidence with confidence. If a parser drops captions, identifiers, equations,
supplements, or licensing metadata, the downstream system inherits that loss and
still calls it data.

PMCGrab is a narrow tool for one boundary: PMC and JATS article sources in,
clean Python objects and JSON out.

## Choose your path

<div class="grid cards" markdown>

- [:material-rocket-launch: **Start from zero**](getting-started/complete-beginner-guide.md)
  Install PMCGrab, fetch your first article, and inspect the JSON shape.

- [:material-timer-sand-complete: **Move fast**](getting-started/quick-start.md)
  Use the shortest path if you already know Python packaging and PMC IDs.

- [:material-console-line: **Use the CLI**](user-guide/cli.md)
  Turn PMC IDs, PMIDs, DOIs, ID files, or local XML files into JSON output.

- [:material-database-arrow-down: **Process bulk XML**](user-guide/batch-processing.md)
  Parse pre-downloaded PMC/JATS XML from disk without repeated network calls.

- [:material-code-tags: **Read the API**](api/core.md)
  Use `Paper`, `process_single_pmc`, and local XML helpers directly.

- [:material-test-tube: **Check the contract**](user-guide/output-format.md)
  Understand the normalized JSON groups before wiring a pipeline around them.

</div>

## What you get

- Schema V4 JSON with article metadata, contributors, content, assets,
  relations, quality, and provenance.
- Loss-aware body and abstract parsing for paragraphs, nested sections, lists,
  definition lists, boxed text, formulas, figures, tables, supplements, and
  unknown JATS blocks.
- No raw XML payloads in output JSON; traceability lives in structured `source`
  metadata.
- Two ingestion paths: fetch by PMC ID from NCBI, or parse local JATS XML from
  a repeatable corpus build.
- A Python API and CLI that share the same output contract.
- Release checks built around real use: local XML E2E, opt-in live NCBI E2E,
  wheel smoke install, CLI tests, parser regressions, and JSON serialization.

## What it is not

PMCGrab is not a PDF parser, paywalled full-text scraper, clinical tool, or
general web crawler.

It is infrastructure for biomedical literature context. Small scope, clear
boundary, useful output.
