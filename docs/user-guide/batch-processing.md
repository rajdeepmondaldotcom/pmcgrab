# Batch Processing

PMCGrab supports three batch paths:

- Loop over `process_single_pmc()` when you need each article dictionary.
- Use `process_pmc_ids()` when you only need a success/failure map.
- Use `process_local_xml_dir()` for pre-downloaded PMC XML at scale.

## Save Multiple Network Articles

```python
import json
from pathlib import Path

from pmcgrab import process_single_pmc

PMC_IDS = ["7181753", "3539614", "3084273"]
OUT_DIR = Path("pmc_output")
OUT_DIR.mkdir(exist_ok=True)

successful = []
failed = []

for pmcid in PMC_IDS:
    print(f"Processing PMC{pmcid}...")
    data = process_single_pmc(pmcid)

    if not data:
        failed.append(pmcid)
        continue

    (OUT_DIR / f"PMC{data['identifiers']['pmc_id']}.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    successful.append(pmcid)

print(f"Successful: {len(successful)}")
print(f"Failed: {failed}")
```

`process_single_pmc()` handles email rotation, timeout protection, retries, and
normalization internally. It returns `None` when an article cannot be fetched,
parsed, or converted into usable article content.

## Concurrent Success Map

Use `process_pmc_ids()` when another layer owns persistence and you only need to
know which IDs succeeded:

```python
from pmcgrab import process_pmc_ids

results = process_pmc_ids(["7181753", "3539614", "3084273"], workers=8)

successful = [pmcid for pmcid, ok in results.items() if ok]
failed = [pmcid for pmcid, ok in results.items() if not ok]

print(f"Successful: {successful}")
print(f"Failed: {failed}")
```

## Local XML Directory

Local XML processing skips network I/O and is the fastest path for bulk PMC
exports:

```python
from pmcgrab import process_local_xml_dir

results = process_local_xml_dir("./pmc_bulk_xml", workers=16)

for filename, data in results.items():
    if data:
        print(filename, data["title"]["main"])
```

The returned dictionary maps each XML filename stem to a normalized article
dictionary or `None` when that file failed.

## Async Applications

Async applications can use `async_process_pmc_ids()`:

```python
import asyncio

from pmcgrab.application.processing import async_process_pmc_ids

results = asyncio.run(
    async_process_pmc_ids(["7181753", "3539614", "3084273"], max_concurrency=10)
)

for pmcid, data in results.items():
    print(pmcid, "OK" if data else "FAIL")
```

## CLI Batch Processing

```bash
# Network PMCID batch
pmcgrab --pmcids 7181753 3539614 3084273 --output-dir ./results --workers 8

# Mixed ID file: PMCIDs, PMIDs, or DOIs, one per line
pmcgrab --from-id-file ids.txt --output-dir ./results

# Local XML directory
pmcgrab --from-dir ./pmc_bulk_xml --output-dir ./results --workers 16

# JSONL output
pmcgrab --pmcids 7181753 3539614 --format jsonl --output-dir ./results
```

The CLI accepts exactly one input mode per run.
