# Batch Processing

PMCGrab provides powerful batch processing capabilities for handling large collections of PMC articles efficiently.

## Basic Batch Processing

### Using process_pmc_ids_in_batches

The main function for batch processing:

```python
from pmcgrab import process_pmc_ids_in_batches

# List of PMC IDs to process
pmc_ids = [
    "7181753", "3539614", "5454911", "8378853",
    "7462677", "7890123", "7456789", "8234567"
]

# Process in batches
process_pmc_ids_in_batches(
    pmc_ids=pmc_ids,
    output_dir="./batch_output",
    batch_size=5,        # Process 5 articles at a time
    max_workers=3,       # Use 3 parallel threads
    email="your-email@example.com"
)
```

This creates individual JSON files for each successfully processed article:

```
batch_output/
├── PMC7181753.json
├── PMC3539614.json
├── PMC5454911.json
├── PMC8378853.json
├── processing_summary.json
└── failed_pmcids.txt
```

## Advanced Batch Processing

### Custom Error Handling

```python
from pmcgrab import process_pmc_ids_in_batches
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Process with error tolerance
process_pmc_ids_in_batches(
    pmc_ids=pmc_ids,
    output_dir="./robust_output",
    batch_size=10,
    max_workers=4,
    max_retries=5,       # Retry failed downloads up to 5 times
    timeout=60,          # 60 second timeout per request
    email="your-email@example.com",
    verbose=True         # Detailed progress reporting
)
```

### Processing with Retry Logic

```python
from pmcgrab import process_in_batches_with_retry

# More robust processing with automatic retries
results = process_in_batches_with_retry(
    pmc_ids=pmc_ids,
    output_dir="./retry_output",
    batch_size=8,
    max_workers=6,
    max_retries=3,
    retry_delay=5,       # Wait 5 seconds between retries
    email="your-email@example.com"
)

print(f"Successfully processed: {len(results['successful'])}")
print(f"Failed after retries: {len(results['failed'])}")
```

## Reading PMC IDs from Files

### From Text File

```python
from pmcgrab import process_pmc_ids_in_batches

# Read PMC IDs from file (one per line)
def read_pmc_ids(filename):
    with open(filename, 'r') as f:
        return [line.strip() for line in f if line.strip()]

# Process from file
pmc_ids = read_pmc_ids('pmc_ids.txt')
process_pmc_ids_in_batches(
    pmc_ids=pmc_ids,
    output_dir="./file_output",
    batch_size=20,
    max_workers=8,
    email="your-email@example.com"
)
```

Example `pmc_ids.txt`:

```
7181753
3539614
5454911
8378853
7462677
```

### From CSV File

```python
import pandas as pd
from pmcgrab import process_pmc_ids_in_batches

# Read from CSV with metadata
df = pd.read_csv('articles.csv')
pmc_ids = df['pmcid'].astype(str).tolist()

# Process articles
process_pmc_ids_in_batches(
    pmc_ids=pmc_ids,
    output_dir="./csv_output",
    batch_size=15,
    max_workers=6,
    email="your-email@example.com"
)
```

Example `articles.csv`:

```csv
pmcid,title,category
7181753,COVID-19 Research Article,virology
3539614,Machine Learning in Biology,bioinformatics
5454911,Clinical Trial Results,medicine
```

## Progress Monitoring

### Built-in Progress Bars

PMCGrab uses tqdm for progress tracking:

```python
from pmcgrab import process_pmc_ids_in_batches

# Progress bars are shown automatically
process_pmc_ids_in_batches(
    pmc_ids=large_pmc_list,
    output_dir="./progress_output",
    batch_size=25,
    max_workers=8,
    email="your-email@example.com",
    verbose=True  # Enables detailed progress output
)
```

### Custom Progress Monitoring

```python
from pmcgrab import Paper
import time
from tqdm import tqdm

def process_with_custom_progress(pmc_ids, email, output_dir):
    """Process PMC IDs with custom progress monitoring."""
    successful = []
    failed = []

    # Create progress bar
    pbar = tqdm(total=len(pmc_ids), desc="Processing articles")

    for i, pmcid in enumerate(pmc_ids):
        try:
            paper = Paper.from_pmc(pmcid, email=email)

            # Save to file
            output_file = f"{output_dir}/PMC{pmcid}.json"
            with open(output_file, 'w') as f:
                import json
                json.dump(paper.to_dict(), f, indent=2)

            successful.append(pmcid)
            pbar.set_description(f"✓ PMC{pmcid}")

        except Exception as e:
            failed.append({'pmcid': pmcid, 'error': str(e)})
            pbar.set_description(f"✗ PMC{pmcid}: {str(e)[:50]}")

        pbar.update(1)
        time.sleep(0.1)  # Rate limiting

    pbar.close()
    return successful, failed

# Use custom progress monitoring
successful, failed = process_with_custom_progress(
    pmc_ids=["7181753", "3539614", "5454911"],
    email="your-email@example.com",
    output_dir="./custom_progress"
)
```

## Chunked Processing for Large Datasets

### Processing Very Large Lists

```python
from pmcgrab import process_in_batches
import os

def process_large_dataset(pmc_ids, email, base_output_dir, chunk_size=1000):
    """Process very large datasets in chunks."""
    total_chunks = len(pmc_ids) // chunk_size + (1 if len(pmc_ids) % chunk_size else 0)

    for i in range(0, len(pmc_ids), chunk_size):
        chunk = pmc_ids[i:i + chunk_size]
        chunk_num = i // chunk_size + 1

        print(f"\nProcessing chunk {chunk_num}/{total_chunks} ({len(chunk)} articles)")

        # Create chunk-specific output directory
        chunk_output_dir = os.path.join(base_output_dir, f"chunk_{chunk_num:03d}")
        os.makedirs(chunk_output_dir, exist_ok=True)

        # Process chunk
        try:
            process_in_batches(
                pmc_ids=chunk,
                output_dir=chunk_output_dir,
                batch_size=50,
                max_workers=8,
                email=email
            )
            print(f"✓ Completed chunk {chunk_num}")

        except Exception as e:
            print(f"✗ Failed chunk {chunk_num}: {e}")
            continue

# Process 10,000 articles in chunks
large_pmc_list = [str(i) for i in range(1000000, 1010000)]  # Example large list
process_large_dataset(
    pmc_ids=large_pmc_list,
    email="your-email@example.com",
    base_output_dir="./large_dataset"
)
```

## Parallel Processing Strategies

### CPU-Bound vs I/O-Bound

```python
from pmcgrab import process_pmc_ids_in_batches

# For I/O-bound operations (network requests)
# Use more workers than CPU cores
io_bound_config = {
    'max_workers': 16,     # 2-4x CPU cores
    'batch_size': 20,
    'timeout': 30
}

# For CPU-bound operations (heavy parsing)
# Use workers equal to CPU cores
cpu_bound_config = {
    'max_workers': 8,      # Equal to CPU cores
    'batch_size': 10,
    'timeout': 60
}

# Apply configuration
process_pmc_ids_in_batches(
    pmc_ids=pmc_ids,
    output_dir="./optimized_output",
    email="your-email@example.com",
    **io_bound_config  # or cpu_bound_config
)
```

### Memory-Efficient Processing

```python
from pmcgrab import Paper
import json
import gc

def memory_efficient_processing(pmc_ids, email, output_dir, batch_size=10):
    """Process articles with memory management."""
    for i in range(0, len(pmc_ids), batch_size):
        batch = pmc_ids[i:i + batch_size]
        print(f"Processing batch {i//batch_size + 1}: {len(batch)} articles")

        for pmcid in batch:
            try:
                # Process single article
                paper = Paper.from_pmc(pmcid, email=email)

                # Save immediately
                output_file = f"{output_dir}/PMC{pmcid}.json"
                with open(output_file, 'w') as f:
                    json.dump(paper.to_dict(), f, indent=2)

                # Clear memory
                del paper

            except Exception as e:
                print(f"Error processing PMC{pmcid}: {e}")

        # Force garbage collection after each batch
        gc.collect()

# Use memory-efficient processing
memory_efficient_processing(
    pmc_ids=large_pmc_list,
    email="your-email@example.com",
    output_dir="./memory_efficient"
)
```

## Error Recovery and Resumption

### Resumable Processing

```python
import os
import json
from pmcgrab import process_pmc_ids_in_batches

def resumable_processing(pmc_ids, email, output_dir):
    """Resume processing from where it left off."""
    # Check what's already been processed
    processed_files = [f for f in os.listdir(output_dir) if f.startswith('PMC') and f.endswith('.json')]
    processed_ids = [f.replace('PMC', '').replace('.json', '') for f in processed_files]

    # Filter out already processed IDs
    remaining_ids = [pmcid for pmcid in pmc_ids if pmcid not in processed_ids]

    print(f"Found {len(processed_ids)} already processed articles")
    print(f"Remaining to process: {len(remaining_ids)}")

    if remaining_ids:
        process_pmc_ids_in_batches(
            pmc_ids=remaining_ids,
            output_dir=output_dir,
            batch_size=20,
            max_workers=6,
            email=email
        )
    else:
        print("All articles already processed!")

# Resume processing
resumable_processing(
    pmc_ids=all_pmc_ids,
    email="your-email@example.com",
    output_dir="./resumable_output"
)
```

### Failed Article Recovery

```python
import json
from pmcgrab import Paper

def reprocess_failed_articles(failed_file, email, output_dir):
    """Reprocess articles that failed in previous runs."""
    # Read failed PMC IDs
    if os.path.exists(failed_file):
        with open(failed_file, 'r') as f:
            failed_ids = [line.strip() for line in f if line.strip()]
    else:
        print("No failed articles file found")
        return

    print(f"Attempting to reprocess {len(failed_ids)} failed articles")

    reprocessed = []
    still_failed = []

    for pmcid in failed_ids:
        try:
            paper = Paper.from_pmc(pmcid, email=email, timeout=120)  # Longer timeout

            # Save successful reprocessing
            output_file = f"{output_dir}/PMC{pmcid}.json"
            with open(output_file, 'w') as f:
                json.dump(paper.to_dict(), f, indent=2)

            reprocessed.append(pmcid)
            print(f"✓ Reprocessed PMC{pmcid}")

        except Exception as e:
            still_failed.append(pmcid)
            print(f"✗ Still failed PMC{pmcid}: {e}")

    # Update failed file
    if still_failed:
        with open(failed_file, 'w') as f:
            for pmcid in still_failed:
                f.write(f"{pmcid}\n")
    else:
        os.remove(failed_file)  # All recovered!

    print(f"Recovered: {len(reprocessed)}, Still failed: {len(still_failed)}")

# Reprocess failed articles
reprocess_failed_articles(
    failed_file="./batch_output/failed_pmcids.txt",
    email="your-email@example.com",
    output_dir="./batch_output"
)
```

## Performance Optimization

### Optimal Batch Sizes

```python
# Performance testing for optimal batch size
import time
from pmcgrab import process_pmc_ids_in_batches

def test_batch_performance(pmc_ids, email, batch_sizes=[5, 10, 20, 50]):
    """Test different batch sizes to find optimal performance."""
    results = {}

    for batch_size in batch_sizes:
        print(f"\nTesting batch size: {batch_size}")
        start_time = time.time()

        try:
            process_pmc_ids_in_batches(
                pmc_ids=pmc_ids[:20],  # Test subset
                output_dir=f"./test_batch_{batch_size}",
                batch_size=batch_size,
                max_workers=4,
                email=email
            )

            duration = time.time() - start_time
            results[batch_size] = duration
            print(f"Batch size {batch_size}: {duration:.2f} seconds")

        except Exception as e:
            print(f"Batch size {batch_size} failed: {e}")

    # Find optimal batch size
    if results:
        optimal_batch = min(results, key=results.get)
        print(f"\nOptimal batch size: {optimal_batch} ({results[optimal_batch]:.2f}s)")
        return optimal_batch

    return None

# Test performance
optimal_batch = test_batch_performance(
    pmc_ids=test_pmc_ids,
    email="your-email@example.com"
)
```

## Best Practices

### Production Batch Processing

```python
from pmcgrab import process_pmc_ids_in_batches
import logging
import os
from datetime import datetime

def production_batch_processing(pmc_ids, email, base_output_dir):
    """Production-ready batch processing with logging and error handling."""

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
    logger.info(f"Starting batch processing of {len(pmc_ids)} articles")

    # Create timestamped output directory
    output_dir = os.path.join(base_output_dir, f"batch_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Process with robust settings
        process_pmc_ids_in_batches(
            pmc_ids=pmc_ids,
            output_dir=output_dir,
            batch_size=25,       # Balanced batch size
            max_workers=8,       # Reasonable parallelism
            max_retries=5,       # Robust retry logic
            timeout=90,          # Generous timeout
            email=email,
            verbose=True
        )

        logger.info(f"Batch processing completed successfully")
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"Log file: {log_file}")

    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        raise

# Run production batch processing
production_batch_processing(
    pmc_ids=production_pmc_ids,
    email="your-email@example.com",
    base_output_dir="./production_output"
)
```

This comprehensive guide should help you handle any batch processing scenario with PMCGrab efficiently and reliably.
