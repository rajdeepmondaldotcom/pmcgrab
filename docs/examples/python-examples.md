# Python Examples

Real-world example showing how to use PMCGrab effectively.

## Batch Processing Multiple Papers

This example demonstrates how to process multiple PMC articles and save them as JSON files:

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

### Key Features Demonstrated

- **Batch Processing**: Efficiently processes multiple PMC articles
- **Error Handling**: Gracefully handles failed parsing attempts
- **Pretty Output**: Shows key information during processing
- **JSON Export**: Saves complete article data as structured JSON files
- **Email Rotation**: Uses the built-in email rotation system

### Expected Output

```
• Fetching PMC7114487 using email researcher1@example.com …
  Title   : COVID-19 pandemic response and lessons learned from the…
  Abstract: The COVID-19 pandemic has posed unprecedented challenges to global health…
  Authors : 5
  ↳ JSON saved to pmc_output/PMC7114487.json

• Fetching PMC3084273 using email researcher2@example.com …
  Title   : Machine learning approaches in genomics and personalized medicine…
  Abstract: Recent advances in machine learning have revolutionized the field of…
  Authors : 3
  ↳ JSON saved to pmc_output/PMC3084273.json
```

This example is perfect for:

- Building literature review datasets
- Creating training data for AI models
- Systematic research paper analysis
- Academic research workflows
