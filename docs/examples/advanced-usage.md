# Advanced Usage

Advanced patterns and techniques for power users of PMCGrab.

## Custom Processing Functions

### Processing with Custom Logic

```python
import json
from pathlib import Path
from pmcgrab.application.processing import process_single_pmc
from pmcgrab.infrastructure.settings import next_email

def process_with_filtering(pmcids, output_dir="filtered_output"):
    """Process PMCs with custom filtering logic."""

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    results = []

    for pmcid in pmcids:
        email = next_email()
        print(f"Processing PMC{pmcid}...")

        data = process_single_pmc(pmcid)
        if data is None:
            continue

        # Custom filtering - only keep papers with abstracts > 500 chars
        if len(data.get('abstract', '')) < 500:
            print(f"  Skipping PMC{pmcid} - abstract too short")
            continue

        # Save filtered result
        output_file = output_path / f"PMC{pmcid}.json"
        with output_file.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        results.append(data)
        print(f"  Saved PMC{pmcid} ({len(data['abstract'])} char abstract)")

    return results

# Usage
pmcids = ["7114487", "3084273", "7690653"]
filtered_papers = process_with_filtering(pmcids)
print(f"Processed {len(filtered_papers)} papers that met criteria")
```

## Data Analysis Integration

### Converting to DataFrame

```python
import pandas as pd
from pmcgrab.application.processing import process_single_pmc

def create_papers_dataframe(pmcids):
    """Create a pandas DataFrame from processed papers."""

    papers_data = []

    for pmcid in pmcids:
        data = process_single_pmc(pmcid)
        if data is None:
            continue

        # Extract key fields for analysis
        paper_info = {
            'pmcid': pmcid,
            'title': data.get('title', ''),
            'journal': data.get('journal', ''),
            'pub_date': data.get('pub_date', ''),
            'author_count': len(data.get('authors', [])),
            'abstract_length': len(data.get('abstract', '')),
            'section_count': len(data.get('body', {})),
            'has_figures': len(data.get('figures', [])) > 0,
            'has_tables': len(data.get('tables', [])) > 0
        }
        papers_data.append(paper_info)

    return pd.DataFrame(papers_data)

# Usage
pmcids = ["7114487", "3084273", "7690653", "5707528"]
df = create_papers_dataframe(pmcids)

print("Dataset Overview:")
print(df.describe())
print(f"\nJournals: {df['journal'].unique()}")
```

## Error Handling and Retry Logic

### Robust Processing with Retries

```python
import time
import json
from pathlib import Path
from pmcgrab.application.processing import process_single_pmc
from pmcgrab.infrastructure.settings import next_email

def robust_processing(pmcids, max_retries=3, delay=2):
    """Process PMCs with robust error handling and retries."""

    output_dir = Path("robust_output")
    output_dir.mkdir(exist_ok=True)

    successful = []
    failed = []

    for pmcid in pmcids:
        success = False

        for attempt in range(max_retries):
            try:
                email = next_email()
                print(f"Processing PMC{pmcid} (attempt {attempt + 1}/{max_retries})")

                data = process_single_pmc(pmcid)

                if data is not None:
                    # Save successful result
                    output_file = output_dir / f"PMC{pmcid}.json"
                    with output_file.open('w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)

                    successful.append(pmcid)
                    print(f"  Success Successfully processed PMC{pmcid}")
                    success = True
                    break
                else:
                    print(f"  ⚠ No data returned for PMC{pmcid}")

            except Exception as e:
                print(f"  Error Error processing PMC{pmcid}: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"    Retrying in {delay} seconds...")
                    time.sleep(delay)

        if not success:
            failed.append(pmcid)
            print(f"  Error Failed to process PMC{pmcid} after {max_retries} attempts")

    print(f"\nResults: {len(successful)} successful, {len(failed)} failed")
    return successful, failed

# Usage
pmcids = ["7114487", "3084273", "7690653", "5707528", "7979870"]
successful, failed = robust_processing(pmcids)

if failed:
    print(f"Failed PMC IDs: {failed}")
```

## Configuration and Settings

### Custom Email Rotation

```python
from pmcgrab.infrastructure.settings import next_email

# PMCGrab automatically rotates through available emails
# You can also check the current email configuration:

def show_email_status():
    """Display current email configuration status."""
    for i in range(5):  # Show first 5 emails in rotation
        email = next_email()
        print(f"Email {i+1}: {email}")

show_email_status()
```

## Performance Optimization

### Memory-Efficient Processing

```python
def memory_efficient_processing(pmcids, batch_size=5):
    """Process large datasets with memory efficiency."""

    total_batches = len(pmcids) // batch_size + (1 if len(pmcids) % batch_size else 0)

    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(pmcids))
        batch = pmcids[start_idx:end_idx]

        print(f"Processing batch {batch_num + 1}/{total_batches}")

        for pmcid in batch:
            data = process_single_pmc(pmcid)
            if data:
                # Process immediately and don't store in memory
                output_file = Path(f"batch_output/PMC{pmcid}.json")
                output_file.parent.mkdir(exist_ok=True)

                with output_file.open('w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                print(f"  Saved PMC{pmcid}")
                # Clear data from memory
                del data

# Usage for large datasets
large_pmcid_list = [str(i) for i in range(7000000, 7000100)]  # Example: 100 PMC IDs
memory_efficient_processing(large_pmcid_list, batch_size=10)
```

These advanced patterns provide robust, scalable solutions for research workflows while maintaining memory efficiency and error resilience.
