# Quick Start

This guide will get you up and running with PMCGrab in minutes.

## Before You Begin

You'll need:

1. **Email address**: Required by NCBI Entrez API for rate limiting and contact
2. **Internet connection**: To fetch articles from PMC
3. **Valid PMC ID**: Get one from [PMC database](https://www.ncbi.nlm.nih.gov/pmc/)

!!! tip "Finding PMC IDs"
PMC IDs are numerical identifiers like `7181753`. You can find them in PMC URLs:
`https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7181753/`

## Quick Demo – Process Three Articles

Run the helper script shipped with PMCGrab. It processes three predefined PMCIDs and shows a concise summary for each one:

```bash
python examples/run_three_pmcs.py
```

What the script does:

1. Downloads each article
2. Prints title, first 120 characters of the abstract and author count
3. Writes full JSON into `pmc_output/PMC<id>.json`

Feel free to edit the `PMC_IDS` list in `examples/run_three_pmcs.py` to include any number of IDs (one or many – the script works the same).

## Understanding the Output

The `Paper` object contains structured data:

```python
# Basic metadata
print(paper.pmcid)        # PMC ID
print(paper.title)        # Article title
print(paper.journal)      # Journal information

# Authors and contributors
for author in paper.authors[:3]:  # First 3 authors
    print(f"{author['FirstName']} {author['LastName']}")

# Abstract (structured by section)
for section, content in paper.abstract.items():
    print(f"{section}: {content[:100]}...")

# Main content (structured by section)
print(f"Introduction: {paper.body.get('Introduction', 'N/A')[:200]}...")
print(f"Methods: {paper.body.get('Methods', 'N/A')[:200]}...")
```

## Working with Raw Dictionaries

If you prefer working with dictionaries instead of `Paper` objects:

```python
from pmcgrab import paper_dict_from_pmc

# Get structured dictionary
article_dict = paper_dict_from_pmc(
    7181753,
    email="your-email@example.com"
)

# Access data
print(article_dict['Title'])
print(article_dict['Body']['Introduction'][:200])
```

## Batch Processing

Process multiple papers at once:

```python
from pmcgrab import process_pmc_ids_in_batches

# List of PMC IDs to process
pmc_ids = ["7181753", "3539614", "5454911"]

# Process in batches (saves JSON files)
process_pmc_ids_in_batches(
    pmc_ids=pmc_ids,
    output_dir="./pmc_output",
    batch_size=5,        # Process 5 at a time
    max_workers=3,       # Use 3 parallel workers
    email="your-email@example.com"
)
```

This creates:

```
pmc_output/
├── PMC7181753.json
├── PMC3539614.json
├── PMC5454911.json
└── processing_summary.json
```

## Command Line Usage

PMCGrab also works from the command line:

```bash
# Single paper
python -m pmcgrab PMC7181753

# Multiple papers
python -m pmcgrab PMC7181753 PMC3539614 PMC5454911

# With custom settings
python -m pmcgrab \
    --output-dir ./results \
    --workers 8 \
    --email your-email@example.com \
    PMC7181753
```

## Error Handling

PMCGrab provides helpful error messages:

```python
from pmcgrab import Paper

try:
    paper = Paper.from_pmc("invalid_id", email="your-email@example.com")
except Exception as e:
    print(f"Error: {e}")
    # Handle the error appropriately
```

## Configuration Options

Customize behavior with optional parameters:

```python
# Download and cache XML locally
paper = Paper.from_pmc(
    "7181753",
    email="your-email@example.com",
    download=True,      # Cache XML files
    validate=True,      # Validate XML structure
    verbose=True        # Show progress
)
```

## What's Next?

Now that you've got the basics:

- **[Basic Usage](../user-guide/basic-usage.md)**: Learn about all available features
- **[Batch Processing](../user-guide/batch-processing.md)**: Advanced batch processing techniques
- **[API Reference](../api/core.md)**: Detailed documentation of all functions
- **[Examples](../examples/python-examples.md)**: Real-world usage examples

## Need Help?

- Check the [User Guide](../user-guide/basic-usage.md) for detailed explanations
- Browse [Examples](../examples/python-examples.md) for common use cases
- Open an issue on [GitHub](https://github.com/rajdeepmondaldotcom/pmcgrab/issues) if you find bugs
