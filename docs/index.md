---
title: Home
template: home.html
hide:
  - navigation
  - toc
---

<!-- Navigation Cards -->
<div class="grid cards" markdown>

- [:material-timer-sand-complete: **5-minute setup**](getting-started/quick-start.md)
  Install PMCGrab and run a multi-paper demo in minutes.

- [:material-book-open-variant: **User Guide**](user-guide/basic-usage.md)
  Comprehensive guides covering every feature.

- [:material-code-tags: **API Reference**](api/core.md)
  Auto-generated docs for every function and class.

- [:material-lightbulb-outline: **Examples**](examples/python-examples.md)
  Real-world usage and advanced patterns.

</div>

## PMCGrab — From PubMed Central ID to AI-Ready JSON in Seconds

Every AI workflow that touches biomedical literature hits the same wall:

1. **Download** PMC XML hoping it’s “structured.”
2. **Fight** nested tags, footnotes, figure refs, and half-broken links.
3. **Hope** your regex didn’t blow away the Methods section you actually need.

**PMCGrab ends this cycle.** Feed the tool a list of PMC IDs and get back clean, section-aware JSON ready for embeddings, vector stores, or prompt templates.

---

## Example Usage

```python
from pmcgrab.application.processing import process_single_pmc

# Process a PMC article
data = process_single_pmc("7114487")

if data:
    print(f"Title: {data['title']}")
    print(f"Authors: {len(data['authors'])}")
    print(f"Sections: {list(data['body'].keys())}")
```

## Example Output

```json
{
  "pmc_id": "7114487",
  "title": "Machine learning approaches in cancer research",
  "abstract": "Recent advances in machine learning have revolutionized...",
  "authors": [
    {
      "First_Name": "John",
      "Last_Name": "Doe",
      "Affiliation": "Cancer Research Institute"
    }
  ],
  "body": {
    "Introduction": "Cancer research has evolved significantly...",
    "Methods": "We implemented a deep learning framework...",
    "Results": "Our model achieved 94.2% accuracy...",
    "Discussion": "These findings demonstrate the potential..."
  },
  "journal": "Nature Medicine",
  "figures": [...],
  "tables": [...],
  "references": [...]
}
```
