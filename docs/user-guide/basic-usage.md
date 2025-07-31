# Basic Usage

PMCGrab is designed for **batch-first** workflows – pass one or many PMCIDs and receive clean, section-aware JSON suitable for RAG pipelines or downstream analytics.

## TL;DR – Three-Paper Demo

```bash
python examples/run_three_pmcs.py
```

- Downloads three sample PMC articles
- Prints a one-line summary for each (title, abstract snippet, author count)
- Writes full JSON to `pmc_output/PMC<id>.json`

Edit the `PMC_IDS` list in the script to use any IDs you need – one or one-thousand, no other changes required.

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
