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
    print(f"Title: {data['article']['title']['main']}")
    print(f"Journal: {data['article']['publication']['journal']['title']}")
    print(f"Authors: {len(data['article']['contributors']['authors'])}")
    print(f"Sections: {[section['title'] for section in data['content']['sections']]}")
```

## Complete Example - Process Multiple Articles

Here's a complete working example that processes multiple papers:

```python
# ─── examples/run_three_pmcs.py ──────────────────────────────────────────────
import json
from pathlib import Path

from pmcgrab.application.processing import process_single_pmc

# The PMC IDs we want to process
PMC_IDS = ["7114487", "3084273", "7690653", "5707528", "7979870"]

OUT_DIR = Path("pmc_output")
OUT_DIR.mkdir(exist_ok=True)

for pmcid in PMC_IDS:
    print(f"Fetching PMC{pmcid}...")
    data = process_single_pmc(pmcid)
    if data is None:
        print(f"  FAILED to parse PMC{pmcid}")
        continue

    # Pretty-print a few key fields
    title = data["article"]["title"]["main"]
    abstract_blocks = data["content"]["abstracts"][0]["blocks"]
    abstract_preview = abstract_blocks[0]["text"] if abstract_blocks else ""
    print(
        f"  Title   : {title[:80]}{'…' if len(title) > 80 else ''}\n"
        f"  Abstract: {abstract_preview[:120]}{'…' if len(abstract_preview) > 120 else ''}\n"
        f"  Authors : {len(data['article']['contributors']['authors'])}"
    )

    # Persist full JSON
    dest = OUT_DIR / f"PMC{pmcid}.json"
    with dest.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    print(f"  JSON saved to {dest}\n")
```

Run this example:

```bash
python examples/run_three_pmcs.py
```

## Understanding the Output

Each processed article returns a structured dictionary with:

```python
# Access the data
print(data['article']['identifiers']['pmc_id'])           # PMC ID
print(data['article']['title']['main'])                   # Article title
print(data['article']['publication']['journal']['title']) # Journal information

# Authors information
for author in data['article']['contributors']['authors'][:3]:  # First 3 authors
    print(f"{author['First_Name']} {author['Last_Name']}")

# Abstract content
abstract_blocks = data["content"]["abstracts"][0]["blocks"]
print(f"Abstract: {abstract_blocks[0]['text'][:200]}...")

# Main content sections
for section in data["content"]["sections"]:
    if section["title"] in {"Introduction", "Methods"} and section["blocks"]:
        print(f"{section['title']}: {section['blocks'][0]['text'][:200]}...")
```

## Output Structure

After processing, you'll have JSON files like:

```
pmc_output/
├── PMC7114487.json
├── 3084273.json
├── 7690653.json
├── PMC5707528.json
└── PMC7979870.json
```

Each JSON file contains structured data:

```json
{
  "schema": "pmcgrab.paper.v1",
  "identifiers": {
    "pmcid": "PMC7114487",
    "doi": "10.1038/example"
  },
  "paper": {
    "title": "Article title",
    "abstract": [
      {
        "title": "Abstract",
        "content": [{ "type": "paragraph", "text": "Structured abstract text" }],
        "sections": []
      }
    ],
    "body": [...]
  },
  "assets": {
    "images": [...],
    "tables": [...]
  }
}
```

## Command Line Usage

PMCGrab also works from the command line:

```bash
# Single paper
uv run python -m pmcgrab --pmcids 7114487

# Multiple papers
uv run python -m pmcgrab --pmcids 7114487 3084273 7690653

# With custom settings
uv run python -m pmcgrab \
    --output-dir ./results \
    --workers 4 \
    --pmcids 7114487 \

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
    print(f"Successfully processed: {data['article']['title']['main']}")
```

## What's Next?

Now that you've got the basics, choose your learning path:

### New to PMCGrab?

- **[Complete Beginner Guide](complete-beginner-guide.md)**: Start from absolute zero with step-by-step instructions
- **[Interactive Jupyter Tutorial](jupyter-tutorial.md)**: Hands-on notebook experience with real data

### Learn More Features

- **[Basic Usage](../user-guide/basic-usage.md)**: Learn about all available features
- **[Batch Processing](../user-guide/batch-processing.md)**: Advanced batch processing techniques
- **[CLI Reference](../user-guide/cli.md)**: Command-line usage guide

### See Examples

- **[Python Examples](../examples/python-examples.md)**: Code snippets and real-world usage
- **[Advanced Usage](../examples/advanced-usage.md)**: Production-ready workflows

## Need Help?

- Check the [User Guide](../user-guide/basic-usage.md) for detailed explanations
- Browse [Examples](../examples/python-examples.md) for common use cases
- Open an issue on [GitHub](https://github.com/rajdeepmondaldotcom/pmcgrab/issues) if you find bugs
