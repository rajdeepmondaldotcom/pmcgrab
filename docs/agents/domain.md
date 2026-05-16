# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Layout

PMCGrab is a single-context Python package. The domain is "turn PMC/JATS article sources into clean, section-aware, AI-ready Python objects and JSON".

Read these before architecture work when they exist:

- `CONTEXT.md` at the repo root
- `docs/adr/` for architecture decisions
- `docs/development/architecture.md` for the current public architecture narrative

If `CONTEXT.md` or `docs/adr/` does not exist, proceed silently and ground decisions in the package code, tests, README, and development docs.

## Vocabulary

Use the terms from the codebase and docs:

- **PMC ID / PMCID**: PubMed Central article identifier accepted with or without the `PMC` prefix.
- **JATS XML**: The article XML format PMCGrab parses from network or local files.
- **Paper**: The public object-oriented representation of a parsed article.
- **Article dictionary**: The normalized, JSON-serializable dictionary returned by processing helpers.
- **Local XML processing**: Parsing pre-downloaded JATS XML files without network access.
- **NCBI client**: A module that talks to an NCBI or PMC service.

## ADR conflicts

If a proposed cleanup contradicts an existing ADR, surface the conflict explicitly and keep the current ADR as the default source of truth.
