# Batch Processing

PMCGrab provides efficient batch processing capabilities for handling large collections of PMC articles.

## Recommended Approach

The primary way to process multiple articles is using the `process_single_pmc` function in a loop:

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

## Advanced Batch Processing Patterns

### With Error Tracking

```python
import json
from pathlib import Path
from pmcgrab.application.processing import process_single_pmc
from pmcgrab.infrastructure.settings import next_email

def process_with_error_tracking(pmcids, output_dir="results"):
    """Process PMC IDs with comprehensive error tracking."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    successful = []
    failed = []

    for pmcid in pmcids:
        email = next_email()
        print(f"Processing PMC{pmcid}...")

        try:
            data = process_single_pmc(pmcid)
            if data is None:
                failed.append(pmcid)
                print(f"  Failed: No data returned")
                continue

            # Save successful result
            output_file = output_path / f"PMC{pmcid}.json"
            with output_file.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            successful.append(pmcid)
            print(f"  Success: {data['title'][:50]}...")

        except Exception as e:
            failed.append(pmcid)
            print(f"  Error: {str(e)}")

    # Save processing summary
    summary = {
        'total': len(pmcids),
        'successful': len(successful),
        'failed': len(failed),
        'failed_ids': failed
    }

    summary_file = output_path / "processing_summary.json"
    with summary_file.open('w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    print(f"\nProcessing complete: {len(successful)}/{len(pmcids)} successful")
    return successful, failed

# Usage
pmcids = ["7114487", "3084273", "7690653", "invalid_id", "5707528"]
successful, failed = process_with_error_tracking(pmcids)
```

### With Progress Tracking

```python
from tqdm import tqdm
import json
from pathlib import Path
from pmcgrab.application.processing import process_single_pmc
from pmcgrab.infrastructure.settings import next_email

def process_with_progress(pmcids, output_dir="results"):
    """Process PMC IDs with progress bar."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    successful = 0

    for pmcid in tqdm(pmcids, desc="Processing papers"):
        email = next_email()
        data = process_single_pmc(pmcid)

        if data is not None:
            output_file = output_path / f"PMC{pmcid}.json"
            with output_file.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            successful += 1
            tqdm.write(f"Success PMC{pmcid}: {data['title'][:40]}...")
        else:
            tqdm.write(f"Error PMC{pmcid}: Failed to process")

    print(f"\nCompleted: {successful}/{len(pmcids)} papers processed successfully")

# Usage
large_pmcid_list = ["7114487", "3084273", "7690653", "5707528", "7979870"]
process_with_progress(large_pmcid_list)
```

### Reading PMC IDs from Files

#### From Text File

```python
import json
from pathlib import Path
from pmcgrab.application.processing import process_single_pmc
from pmcgrab.infrastructure.settings import next_email

def process_from_file(filename, output_dir="results"):
    """Process PMC IDs from a text file."""
    # Read PMC IDs from file (one per line)
    with open(filename, 'r') as f:
        pmcids = [line.strip() for line in f if line.strip()]

    print(f"Read {len(pmcids)} PMC IDs from {filename}")

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    for pmcid in pmcids:
        email = next_email()
        print(f"Processing PMC{pmcid}...")

        data = process_single_pmc(pmcid)
        if data is not None:
            output_file = output_path / f"PMC{pmcid}.json"
            with output_file.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"  Saved PMC{pmcid}")
        else:
            print(f"  Failed PMC{pmcid}")

# Create example file
with open('pmc_ids.txt', 'w') as f:
    f.write("7114487\n3084273\n7690653\n5707528\n7979870\n")

# Process from file
process_from_file('pmc_ids.txt')
```

#### From CSV File

```python
import pandas as pd
import json
from pathlib import Path
from pmcgrab.application.processing import process_single_pmc
from pmcgrab.infrastructure.settings import next_email

def process_from_csv(csv_file, pmcid_column='pmcid', output_dir="results"):
    """Process PMC IDs from a CSV file."""
    df = pd.read_csv(csv_file)
    pmcids = df[pmcid_column].astype(str).tolist()

    print(f"Read {len(pmcids)} PMC IDs from {csv_file}")

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    results = []

    for i, pmcid in enumerate(pmcids):
        email = next_email()
        print(f"Processing {i+1}/{len(pmcids)}: PMC{pmcid}...")

        data = process_single_pmc(pmcid)
        if data is not None:
            # Add CSV metadata to the result
            csv_row = df.iloc[i].to_dict()
            data['csv_metadata'] = csv_row

            output_file = output_path / f"PMC{pmcid}.json"
            with output_file.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            results.append(data)
            print(f"  Success: {data['title'][:40]}...")
        else:
            print(f"  Failed to process PMC{pmcid}")

    return results

# Create example CSV
csv_data = {
    'pmcid': [7114487, 3084273, 7690653],
    'category': ['cancer', 'ML', 'genomics'],
    'priority': ['high', 'medium', 'high']
}
pd.DataFrame(csv_data).to_csv('articles.csv', index=False)

# Process from CSV
results = process_from_csv('articles.csv')
```

## Large Dataset Processing

### Chunked Processing

```python
import json
from pathlib import Path
from pmcgrab.application.processing import process_single_pmc
from pmcgrab.infrastructure.settings import next_email

def process_large_dataset(pmcids, output_dir="large_dataset", chunk_size=100):
    """Process very large datasets in chunks."""
    total_chunks = len(pmcids) // chunk_size + (1 if len(pmcids) % chunk_size else 0)

    base_path = Path(output_dir)
    base_path.mkdir(exist_ok=True)

    overall_stats = {'successful': 0, 'failed': 0}

    for i in range(0, len(pmcids), chunk_size):
        chunk = pmcids[i:i + chunk_size]
        chunk_num = i // chunk_size + 1

        print(f"\n=== Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} articles) ===")

        # Create chunk-specific output directory
        chunk_dir = base_path / f"chunk_{chunk_num:03d}"
        chunk_dir.mkdir(exist_ok=True)

        chunk_stats = {'successful': 0, 'failed': 0, 'failed_ids': []}

        for pmcid in chunk:
            email = next_email()
            data = process_single_pmc(pmcid)

            if data is not None:
                output_file = chunk_dir / f"PMC{pmcid}.json"
                with output_file.open('w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                chunk_stats['successful'] += 1
                overall_stats['successful'] += 1
            else:
                chunk_stats['failed'] += 1
                chunk_stats['failed_ids'].append(pmcid)
                overall_stats['failed'] += 1

        # Save chunk summary
        summary_file = chunk_dir / "chunk_summary.json"
        with summary_file.open('w', encoding='utf-8') as f:
            json.dump(chunk_stats, f, indent=2)

        print(f"Chunk {chunk_num} complete: {chunk_stats['successful']} successful, {chunk_stats['failed']} failed")

    # Save overall summary
    overall_summary = {
        'total_articles': len(pmcids),
        'total_chunks': total_chunks,
        'chunk_size': chunk_size,
        **overall_stats,
        'success_rate': overall_stats['successful'] / len(pmcids) * 100
    }

    summary_file = base_path / "overall_summary.json"
    with summary_file.open('w', encoding='utf-8') as f:
        json.dump(overall_summary, f, indent=2)

    print(f"\n=== Processing Complete ===")
    print(f"Total: {len(pmcids)} articles")
    print(f"Successful: {overall_stats['successful']}")
    print(f"Failed: {overall_stats['failed']}")
    print(f"Success rate: {overall_summary['success_rate']:.1f}%")

# Example: process 500 articles in chunks of 50
large_pmcid_list = [str(7000000 + i) for i in range(500)]  # Example IDs
process_large_dataset(large_pmcid_list, chunk_size=50)
```

### Memory-Efficient Processing

```python
import json
import gc
from pathlib import Path
from pmcgrab.application.processing import process_single_pmc
from pmcgrab.infrastructure.settings import next_email

def memory_efficient_processing(pmcids, output_dir="memory_efficient", batch_size=10):
    """Process articles with memory management."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    for i in range(0, len(pmcids), batch_size):
        batch = pmcids[i:i + batch_size]
        batch_num = i // batch_size + 1

        print(f"Processing batch {batch_num}: {len(batch)} articles")

        for pmcid in batch:
            email = next_email()
            data = process_single_pmc(pmcid)

            if data is not None:
                # Save immediately and clear from memory
                output_file = output_path / f"PMC{pmcid}.json"
                with output_file.open('w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"  Saved PMC{pmcid}")

                # Clear data from memory
                del data
            else:
                print(f"  Failed PMC{pmcid}")

        # Force garbage collection after each batch
        gc.collect()
        print(f"Batch {batch_num} complete, memory cleared")

# Usage
large_list = [str(7000000 + i) for i in range(100)]
memory_efficient_processing(large_list, batch_size=10)
```

## Resumable Processing

### Resume from Previous Run

```python
import json
from pathlib import Path
from pmcgrab.application.processing import process_single_pmc
from pmcgrab.infrastructure.settings import next_email

def resumable_processing(pmcids, output_dir="resumable_output"):
    """Resume processing from where it left off."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Check what's already been processed
    processed_files = list(output_path.glob("PMC*.json"))
    processed_ids = [f.stem.replace('PMC', '') for f in processed_files]

    # Filter out already processed IDs
    remaining_ids = [pmcid for pmcid in pmcids if pmcid not in processed_ids]

    print(f"Found {len(processed_ids)} already processed articles")
    print(f"Remaining to process: {len(remaining_ids)}")

    if not remaining_ids:
        print("All articles already processed!")
        return

    # Process remaining articles
    for pmcid in remaining_ids:
        email = next_email()
        print(f"Processing PMC{pmcid}...")

        data = process_single_pmc(pmcid)
        if data is not None:
            output_file = output_path / f"PMC{pmcid}.json"
            with output_file.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"  Saved PMC{pmcid}")
        else:
            print(f"  Failed PMC{pmcid}")

    print("Processing complete!")

# Usage - can be run multiple times safely
all_pmcids = ["7114487", "3084273", "7690653", "5707528", "7979870"]
resumable_processing(all_pmcids)
```

## Command Line Batch Processing

For command-line batch processing, use the built-in CLI:

```bash
# From individual IDs
python -m pmcgrab PMC7114487 PMC3084273 PMC7690653

# From file
echo -e "7114487\n3084273\n7690653" > pmcids.txt
python -m pmcgrab --input-file pmcids.txt --output-dir batch_results/

# With custom settings
python -m pmcgrab \
    --input-file pmcids.txt \
    --output-dir ./results \
    --workers 4 \
    --batch-size 10 \
    --max-retries 2 \
    --email researcher@university.edu
```

## Best Practices

### Production-Ready Processing

```python
import json
import logging
from datetime import datetime
from pathlib import Path
from pmcgrab.application.processing import process_single_pmc
from pmcgrab.infrastructure.settings import next_email

def production_batch_processing(pmcids, output_dir="production_output"):
    """Production-ready batch processing with logging."""

    # Set up logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"pmcgrab_batch_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Starting batch processing of {len(pmcids)} articles")

    # Create timestamped output directory
    output_path = Path(output_dir) / f"batch_{timestamp}"
    output_path.mkdir(parents=True, exist_ok=True)

    stats = {'successful': 0, 'failed': 0, 'failed_ids': []}

    try:
        for i, pmcid in enumerate(pmcids, 1):
            logger.info(f"Processing {i}/{len(pmcids)}: PMC{pmcid}")

            email = next_email()
            data = process_single_pmc(pmcid)

            if data is not None:
                output_file = output_path / f"PMC{pmcid}.json"
                with output_file.open('w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                stats['successful'] += 1
                logger.info(f"Success: {data['title'][:50]}...")
            else:
                stats['failed'] += 1
                stats['failed_ids'].append(pmcid)
                logger.warning(f"Failed to process PMC{pmcid}")

        # Save final summary
        summary_file = output_path / "processing_summary.json"
        with summary_file.open('w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)

        success_rate = stats['successful'] / len(pmcids) * 100
        logger.info(f"Batch processing completed: {stats['successful']}/{len(pmcids)} successful ({success_rate:.1f}%)")
        logger.info(f"Output directory: {output_path}")
        logger.info(f"Log file: {log_file}")

    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        raise

    return stats

# Run production processing
pmcids = ["7114487", "3084273", "7690653", "5707528", "7979870"]
results = production_batch_processing(pmcids)
```

This approach provides robust, scalable batch processing while maintaining simplicity and reliability.
