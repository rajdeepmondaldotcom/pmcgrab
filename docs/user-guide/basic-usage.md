# Basic Usage

PMCGrab is designed for **batch-first** workflows – pass one or many PMCIDs and receive clean, section-aware JSON suitable for RAG pipelines or downstream analytics.

## TL;DR – Five-Paper Demo

```bash
python examples/run_five_pmcs.py
```

- Downloads five sample PMC articles
- Prints a one-line summary for each (title, abstract snippet, author count)
- Writes full JSON to `pmc_output/PMC<id>.json`

Edit the `PMC_IDS` list in the script to use any IDs you need – one or one-thousand, no other changes required.

## Minimal API Example (Single Function)

```python
from pmcgrab.application.processing import process_single_pmc

paper_json = process_single_pmc("7181753")  # returns a dict
print(paper_json["title"])
```

The helper handles XML retrieval, parsing, and validation – you get back ready-to-use JSON.

## Batch Processing in Code

```python
from pmcgrab.processing import process_pmc_ids_in_batches

pmc_ids = ["7114487", "3084273", "7690653"]
process_pmc_ids_in_batches(pmc_ids, output_dir="./pmc_output", batch_size=5)
```

## CLI One-Liner

```bash
python -m pmcgrab 7114487 3084273 7690653 --output-dir ./pmc_output
```

That’s it – you now have structured JSON for each article. For more options see `--help` or consult the Batch Processing guide.
