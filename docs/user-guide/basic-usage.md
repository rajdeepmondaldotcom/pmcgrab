# Basic Usage

PMCGrab transforms PubMed Central articles into clean, structured JSON optimized for AI pipelines and research workflows.

## Core Function

The primary way to process articles is with `process_single_pmc`:

```python
from pmcgrab.application.processing import process_single_pmc

# Process a single PMC article
data = process_single_pmc("7114487")

if data:
    print(f"Title: {data['title']}")
    print(f"Authors: {len(data['authors'])}")
    print(f"Sections: {list(data['body'].keys())}")
```

## Complete Working Example

Here's the recommended approach for processing multiple articles:

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

## Key Features

### Automatic Email Rotation

PMCGrab automatically rotates through available email addresses for NCBI API requests:

```python
from pmcgrab.infrastructure.settings import next_email

# Each call returns the next email in rotation
email = next_email()
print(f"Using email: {email}")
```

### Robust Error Handling

Processing returns `None` for failed articles, making batch processing resilient:

```python
pmcids = ["7114487", "3084273", "invalid_id", "7690653"]
successful = []
failed = []

for pmcid in pmcids:
    data = process_single_pmc(pmcid)
    if data is None:
        failed.append(pmcid)
    else:
        successful.append(pmcid)

print(f"Processed: {len(successful)}, Failed: {len(failed)}")
```

### Structured Output

Each article returns a comprehensive dictionary:

```python
data = process_single_pmc("7114487")

# Core metadata
print(f"PMC ID: {data['pmc_id']}")
print(f"Title: {data['title']}")
print(f"Journal: {data['journal']}")
print(f"DOI: {data.get('doi', 'N/A')}")

# Authors
print(f"Authors ({len(data['authors'])}):")
for author in data['authors'][:3]:
    print(f"  - {author['First_Name']} {author['Last_Name']}")

# Content sections
print(f"Sections: {list(data['body'].keys())}")
print(f"Abstract length: {len(data['abstract'])} characters")

# Additional data
print(f"Figures: {len(data.get('figures', []))}")
print(f"Tables: {len(data.get('tables', []))}")
print(f"References: {len(data.get('references', []))}")
```

## Batch Processing Patterns

### Simple Loop Processing

```python
from pmcgrab.application.processing import process_single_pmc
from pmcgrab.infrastructure.settings import next_email
import json
from pathlib import Path

def process_pmcids(pmcids, output_dir="results"):
    """Process a list of PMC IDs and save results."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    results = []

    for pmcid in pmcids:
        email = next_email()
        print(f"Processing PMC{pmcid}...")

        data = process_single_pmc(pmcid)
        if data is None:
            print(f"  Failed to process PMC{pmcid}")
            continue

        # Save individual file
        output_file = output_path / f"PMC{pmcid}.json"
        with output_file.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        results.append(data)
        print(f"  Saved PMC{pmcid}")

    return results

# Usage
pmcids = ["7114487", "3084273", "7690653"]
papers = process_pmcids(pmcids)
print(f"Successfully processed {len(papers)} papers")
```

### With Progress Tracking

```python
from tqdm import tqdm

def process_with_progress(pmcids, output_dir="results"):
    """Process PMC IDs with progress bar."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    successful = 0

    for pmcid in tqdm(pmcids, desc="Processing papers"):
        data = process_single_pmc(pmcid)
        if data is not None:
            output_file = output_path / f"PMC{pmcid}.json"
            with output_file.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            successful += 1

    print(f"Successfully processed {successful}/{len(pmcids)} papers")

# Usage
large_pmcid_list = ["7114487", "3084273", "7690653", "5707528", "7979870"]
process_with_progress(large_pmcid_list)
```

## Command Line Interface

Process articles from the command line:

```bash
# Single article
python -m pmcgrab PMC7114487

# Multiple articles
python -m pmcgrab PMC7114487 PMC3084273 PMC7690653

# From file
echo -e "7114487\n3084273\n7690653" > pmcids.txt
python -m pmcgrab --input-file pmcids.txt --output-dir results/

# With custom settings
python -m pmcgrab \
    --output-dir ./papers \
    --workers 4 \
    --batch-size 10 \
    --email researcher@university.edu \
    PMC7114487 PMC3084273
```

## Output Files

PMCGrab creates structured JSON files:

```json
{
  "pmc_id": "7114487",
  "title": "Machine learning approaches in cancer research",
  "abstract": "Recent advances in machine learning have...",
  "body": {
    "Introduction": "Cancer research has evolved significantly...",
    "Methods": "We implemented a deep learning framework...",
    "Results": "Our model achieved 94.2% accuracy...",
    "Discussion": "These findings demonstrate the potential..."
  },
  "authors": [
    {
      "First_Name": "John",
      "Last_Name": "Doe",
      "Affiliation": "Cancer Research Institute"
    }
  ],
  "journal": "Nature Medicine",
  "pub_date": "2023-05-15",
  "doi": "10.1038/s41591-023-02345-6",
  "figures": [...],
  "tables": [...],
  "references": [...]
}
```

This structure is optimized for:

- **Vector databases**: Each section can be embedded separately
- **RAG systems**: Context-aware retrieval by section
- **Data analysis**: Structured access to all article components
- **LLM processing**: Clean, section-aware text chunks

## Next Steps

- **[Batch Processing](batch-processing.md)**: Advanced parallel processing techniques
- **[CLI Reference](cli.md)**: Complete command-line documentation
- **[Output Format](output-format.md)**: Detailed JSON schema reference
- **[Examples](../examples/python-examples.md)**: More real-world usage patterns
