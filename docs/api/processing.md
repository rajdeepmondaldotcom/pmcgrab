# Processing API

Functions for processing PMC articles efficiently.

## Primary Processing Function

The recommended way to process PMC articles is `process_single_pmc()`. See the
[Core API](core.md#process_single_pmc) for the generated function reference.

## Recommended Usage Pattern

```python
# ─── Recommended Processing Pattern ──────────────────────────────────────────
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
    title = data["title"]["main"]
    abstract_blocks = data["content"]["abstract"][0]["blocks"]
    abstract_preview = abstract_blocks[0]["text"] if abstract_blocks else ""
    print(
        f"  Title   : {title[:80]}{'…' if len(title) > 80 else ''}\n"
        f"  Abstract: {abstract_preview[:120]}{'…' if len(abstract_preview) > 120 else ''}\n"
        f"  Authors : {len(data['contributors']['authors'])}"
    )

    # Persist full JSON
    dest = OUT_DIR / f"PMC{pmcid}.json"
    with dest.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    print(f"  JSON saved to {dest}\n")
```

## Email Management

`next_email()` automatically rotates through available email addresses for NCBI
API requests, ensuring proper rate limiting and compliance. See the
[Core API](core.md#next_email) for the generated function reference.
