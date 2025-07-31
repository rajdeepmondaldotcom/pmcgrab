# Quick Start

This guide will get you up and running with PMCGrab in minutes.

## Before You Begin

You'll need:

1. **Internet connection**: To fetch articles from PMC
2. **Valid PMC ID**: Get one from [PMC database](https://www.ncbi.nlm.nih.gov/pmc/)

!!! tip "Finding PMC IDs"
PMC IDs are numerical identifiers like `7181753`. You can find them in PMC URLs:
`https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7181753/`

## Basic Usage

Start with the simplest approach - process a single article:

```python
from pmcgrab.application.processing import process_single_pmc

# Get structured data from any PMC article
data = process_single_pmc("7114487")

if data:
    print(f"Title: {data['title']}")
    print(f"Journal: {data['journal']}")
    print(f"Authors: {len(data['authors'])}")
    print(f"Sections: {list(data['body'].keys())}")
```

## Complete Example - Process Multiple Articles

Here's a complete working example that processes multiple papers:

```python
# ─── examples/run_three_pmcs.py ──────────────────────────────────────────────
import json
from pathlib import Path

from pmcgrab.application.processing import process_single_pmc
from pmcgrab.infrastructure.settings import next_email

# The PMC IDs we want to process
PMC_IDS = ["7114487", "3084273", "7690653", "5707528", "7979870"]

OUT_DIR = Path("pmc_output")
OUT_DIR.mkdir(exist_ok=True)

for pmcid in PMC_IDS:
    email = next_email()
    print(f"• Fetching PMC{pmcid} using email {email} …")
    data = process_single_pmc(pmcid)
    if data is None:
        print(f"  ↳ FAILED to parse PMC{pmcid}")
        continue

    # Pretty-print a few key fields
    print(
        f"  Title   : {data['title'][:80]}{'…' if len(data['title']) > 80 else ''}\n"
        f"  Abstract: {data['abstract'][:120]}{'…' if len(data['abstract']) > 120 else ''}\n"
        f"  Authors : {len(data['authors']) if data['authors'] else 0}"
    )

    # Persist full JSON
    dest = OUT_DIR / f"PMC{pmcid}.json"
    with dest.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    print(f"  ↳ JSON saved to {dest}\n")
```

Run this example:

```bash
python examples/run_three_pmcs.py
```

## Understanding the Output

Each processed article returns a structured dictionary with:

```python
# Access the data
print(data['pmc_id'])        # PMC ID
print(data['title'])         # Article title
print(data['journal'])       # Journal information

# Authors information
for author in data['authors'][:3]:  # First 3 authors
    print(f"{author['First_Name']} {author['Last_Name']}")

# Abstract content
print(f"Abstract: {data['abstract'][:200]}...")

# Main content sections
if 'Introduction' in data['body']:
    print(f"Introduction: {data['body']['Introduction'][:200]}...")
if 'Methods' in data['body']:
    print(f"Methods: {data['body']['Methods'][:200]}...")
```

## Output Structure

After processing, you'll have JSON files like:

```
pmc_output/
├── PMC7114487.json
├── PMC3084273.json
├── PMC7690653.json
├── PMC5707528.json
└── PMC7979870.json
```

Each JSON file contains structured data:

```json
{
  "pmc_id": "7114487",
  "title": "Article title",
  "abstract": "Article abstract",
  "body": {
    "Introduction": "Section content...",
    "Methods": "Section content...",
    "Results": "Section content...",
    "Discussion": "Section content..."
  },
  "authors": [...],
  "journal": "Journal Name",
  "figures": [...],
  "tables": [...]
}
```

## Command Line Usage

PMCGrab also works from the command line:

```bash
# Single paper
python -m pmcgrab PMC7114487

# Multiple papers
python -m pmcgrab PMC7114487 PMC3084273 PMC7690653

# With custom settings
python -m pmcgrab \
    --output-dir ./results \
    --workers 4 \
    --email your-email@example.com \
    PMC7114487
```

## Error Handling

Handle processing errors gracefully:

```python
from pmcgrab.application.processing import process_single_pmc

pmcid = "7114487"
data = process_single_pmc(pmcid)

if data is None:
    print(f"Failed to process PMC{pmcid}")
else:
    print(f"Successfully processed: {data['title']}")
```

## What's Next?

Now that you've got the basics:

- **[Basic Usage](../user-guide/basic-usage.md)**: Learn about all available features
- **[Batch Processing](../user-guide/batch-processing.md)**: Advanced batch processing techniques
- **[CLI Reference](../user-guide/cli.md)**: Command-line usage guide
- **[Examples](../examples/python-examples.md)**: Real-world usage examples

## Need Help?

- Check the [User Guide](../user-guide/basic-usage.md) for detailed explanations
- Browse [Examples](../examples/python-examples.md) for common use cases
- Open an issue on [GitHub](https://github.com/rajdeepmondaldotcom/pmcgrab/issues) if you find bugs
