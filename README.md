# pmcgrab

pmcgrab is a toolkit for downloading and parsing articles from PubMed Central (PMC). It provides helpers for fetching XML, validating it, and turning it into convenient Python objects.

## Features

- Retrieve article XML via the NCBI Entrez service
- Optional DTD validation to ensure well formed input
- High level `Paper` class describing all parsed metadata
- Utilities for concurrent batch processing with retries
- Functions for cleaning HTML and resolving references

## Installation

Install the package from PyPI or from a local clone:

```bash
pip install pmcgrab
# or
pip install .
```

## Quick start

Fetch a single article using its PMCID:

```python
from pmcgrab import Paper

paper = Paper.from_pmc(123456, "name@example.com")
print(paper.title)
```

`Paper` instances expose attributes such as `authors`, `abstract`, `body` and `published_date`. Full details are documented in the module docstrings.

## Batch processing

For large datasets you can process IDs concurrently and automatically retry failures:

```python
from pmcgrab.processing import process_in_batches_with_retry

pmc_ids = ["123456", "7891011"]
process_in_batches_with_retry(pmc_ids, "output")
```

Each article is written to `output/PMC<pmcid>.json`.

## License

pmcgrab is licensed under the Apache 2.0 License.
