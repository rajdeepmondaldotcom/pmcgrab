# Processing API

Functions for processing PMC articles efficiently.

## Primary Processing Function

The recommended way to process PMC articles:

### process_single_pmc

::: pmcgrab.application.processing.process_single_pmc
options:
show_source: true
show_root_heading: true
show_root_toc_entry: false
show_object_full_path: false
show_category_heading: false
show_signature_annotations: true
heading_level: 3

## Recommended Usage Pattern

```python
# ─── Recommended Processing Pattern ──────────────────────────────────────────
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

## Email Management

### next_email

::: pmcgrab.infrastructure.settings.next_email
options:
show_source: true
show_root_heading: true
show_root_toc_entry: false
show_object_full_path: false
show_category_heading: false
show_signature_annotations: true
heading_level: 3

This function automatically rotates through available email addresses for NCBI API requests, ensuring proper rate limiting and compliance.
