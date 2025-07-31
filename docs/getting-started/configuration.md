# Configuration

PMCGrab provides simple configuration options optimized for the `process_single_pmc` workflow.

## Email Management

PMCGrab automatically manages email rotation for NCBI API compliance:

```python
from pmcgrab.infrastructure.settings import next_email

# Get the next email in rotation
email = next_email()
print(f"Using email: {email}")
```

The system automatically rotates through available email addresses to ensure proper rate limiting and compliance with NCBI guidelines.

## Basic Usage Pattern

The recommended configuration-free approach:

```python
from pmcgrab.application.processing import process_single_pmc
from pmcgrab.infrastructure.settings import next_email

# Process a single article
email = next_email()  # Automatic email rotation
data = process_single_pmc("7114487")

if data:
    print(f"Successfully processed: {data['title']}")
else:
    print("Processing failed")
```

## Batch Processing Configuration

For processing multiple articles, use the standard pattern:

```python
# ─── Recommended Batch Processing Pattern ────────────────────────────────────
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

## Error Handling Configuration

Built-in error handling with graceful degradation:

```python
from pmcgrab.application.processing import process_single_pmc
from pmcgrab.infrastructure.settings import next_email

def robust_processing(pmcids):
    """Process PMC IDs with robust error handling."""
    successful = []
    failed = []

    for pmcid in pmcids:
        email = next_email()

        try:
            data = process_single_pmc(pmcid)
            if data is not None:
                successful.append((pmcid, data))
                print(f"✓ PMC{pmcid}: {data['title'][:50]}...")
            else:
                failed.append(pmcid)
                print(f"✗ PMC{pmcid}: No data returned")
        except Exception as e:
            failed.append(pmcid)
            print(f"✗ PMC{pmcid}: {str(e)}")

    return successful, failed

# Usage
pmcids = ["7114487", "3084273", "invalid_id", "7690653"]
successful, failed = robust_processing(pmcids)
print(f"Processed: {len(successful)}, Failed: {len(failed)}")
```

## Performance Configuration

### Memory-Efficient Processing

For large datasets, process in chunks to manage memory:

```python
import json
import gc
from pathlib import Path
from pmcgrab.application.processing import process_single_pmc
from pmcgrab.infrastructure.settings import next_email

def memory_efficient_processing(pmcids, output_dir="results", batch_size=10):
    """Process large datasets with memory management."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    for i in range(0, len(pmcids), batch_size):
        batch = pmcids[i:i + batch_size]
        print(f"Processing batch {i//batch_size + 1}: {len(batch)} articles")

        for pmcid in batch:
            email = next_email()
            data = process_single_pmc(pmcid)

            if data is not None:
                output_file = output_path / f"PMC{pmcid}.json"
                with output_file.open('w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"  Saved PMC{pmcid}")
                del data  # Clear from memory
            else:
                print(f"  Failed PMC{pmcid}")

        # Force garbage collection after each batch
        gc.collect()

# Usage for large datasets
large_pmcid_list = [str(i) for i in range(7000000, 7000100)]
memory_efficient_processing(large_pmcid_list, batch_size=20)
```

### Progress Tracking Configuration

Add progress tracking for long-running processes:

```python
from tqdm import tqdm
from pmcgrab.application.processing import process_single_pmc
from pmcgrab.infrastructure.settings import next_email

def process_with_progress(pmcids, output_dir="results"):
    """Process with progress tracking."""
    successful = 0

    for pmcid in tqdm(pmcids, desc="Processing papers"):
        email = next_email()
        data = process_single_pmc(pmcid)

        if data is not None:
            # Save and count success
            output_file = Path(output_dir) / f"PMC{pmcid}.json"
            output_file.parent.mkdir(exist_ok=True)

            with output_file.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            successful += 1
            tqdm.write(f"✓ {data['title'][:40]}...")
        else:
            tqdm.write(f"✗ PMC{pmcid}: Failed")

    print(f"Completed: {successful}/{len(pmcids)} papers")

# Usage
pmcids = ["7114487", "3084273", "7690653", "5707528"]
process_with_progress(pmcids)
```

## Output Configuration

### Custom Output Directories

Organize output with custom directory structures:

```python
from datetime import datetime
from pathlib import Path

# Create timestamped directories
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_dir = Path(f"pmc_batch_{timestamp}")

# Or organize by topic
topic_dir = Path("cancer_research_papers")
topic_dir.mkdir(exist_ok=True)
```

### JSON Formatting Options

Control JSON output formatting:

```python
import json
from pmcgrab.application.processing import process_single_pmc

data = process_single_pmc("7114487")

if data:
    # Compact JSON (smaller files)
    with open("compact.json", "w") as f:
        json.dump(data, f, separators=(',', ':'), ensure_ascii=False)

    # Pretty JSON (human readable)
    with open("pretty.json", "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # With Unicode preservation
    with open("unicode.json", "w", encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
```

## Command Line Configuration

For command-line usage, PMCGrab provides several configuration options:

```bash
# Basic usage
python -m pmcgrab PMC7114487

# With custom settings
python -m pmcgrab \
    --output-dir ./results \
    --workers 4 \
    --batch-size 10 \
    --email researcher@university.edu \
    PMC7114487 PMC3084273

# From file
python -m pmcgrab --input-file pmcids.txt --output-dir results/
```

## Best Practices

### Production Configuration

```python
import logging
from datetime import datetime
from pathlib import Path
from pmcgrab.application.processing import process_single_pmc
from pmcgrab.infrastructure.settings import next_email

def production_processing(pmcids, base_output_dir="production"):
    """Production-ready processing with logging and organization."""

    # Set up logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"pmcgrab_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Starting processing of {len(pmcids)} articles")

    # Create organized output structure
    output_dir = Path(base_output_dir) / f"batch_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    stats = {'successful': 0, 'failed': 0, 'failed_ids': []}

    for pmcid in pmcids:
        email = next_email()
        logger.info(f"Processing PMC{pmcid}")

        data = process_single_pmc(pmcid)
        if data is not None:
            output_file = output_dir / f"PMC{pmcid}.json"
            with output_file.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            stats['successful'] += 1
            logger.info(f"Success: {data['title'][:50]}...")
        else:
            stats['failed'] += 1
            stats['failed_ids'].append(pmcid)
            logger.warning(f"Failed: PMC{pmcid}")

    # Save summary
    summary_file = output_dir / "summary.json"
    with summary_file.open('w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)

    logger.info(f"Processing complete: {stats['successful']}/{len(pmcids)} successful")
    return stats

# Usage
pmcids = ["7114487", "3084273", "7690653"]
results = production_processing(pmcids)
```

This configuration approach provides robust, scalable processing while maintaining simplicity and reliability.
