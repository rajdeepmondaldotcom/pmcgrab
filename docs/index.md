---
title: Home
template: home.html
hide:
  - navigation
  - toc
---

<!-- Navigation Cards -->
<div class="grid cards" markdown>

- [:material-rocket-launch: **Complete Beginner Guide**](getting-started/complete-beginner-guide.md)
  Start from absolute zero. Install uv, PMCGrab, and process your first papers.

- [:material-notebook-outline: **Interactive Tutorial**](getting-started/jupyter-tutorial.md)
  Hands-on Jupyter notebook with real data and AI/ML examples.

- [:material-timer-sand-complete: **Quick Start**](getting-started/quick-start.md)
  5-minute setup for experienced users.

- [:material-book-open-variant: **User Guide**](user-guide/basic-usage.md)
  Comprehensive guides covering every feature.

- [:material-code-tags: **API Reference**](api/core.md)
  Auto-generated docs for every function and class.

- [:material-lightbulb-outline: **Examples**](examples/python-examples.md)
  Real-world usage and advanced patterns.

</div>

## PMCGrab - From PubMed Central ID to AI-Ready JSON in Seconds

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
    print(f"Title: {data['title']['main']}")
    print(f"Authors: {len(data['contributors']['authors'])}")
    print(f"Sections: {[section['title'] for section in data['content']['sections']]}")
```

## Example Output

```json
{
  "schema_version": 2,
  "identifiers": {
    "pmc_id": "7114487",
    "pmcid": "PMC7114487",
    "doi": "10.1038/s41591-023-02345-6"
  },
  "title": {
    "main": "Machine learning approaches in cancer research",
    "subtitle": "",
    "translated": []
  },
  "contributors": {
    "authors": [
      {
        "First_Name": "John",
        "Last_Name": "Doe",
        "Affiliation": "Cancer Research Institute"
      }
    ]
  },
  "publication": {
    "journal": {
      "title": "Nature Medicine"
    }
  },
  "content": {
    "abstract": [
      {
        "title": "Abstract",
        "blocks": [
          {
            "type": "paragraph",
            "text": "Recent advances in machine learning have revolutionized..."
          }
        ]
      }
    ],
    "sections": [...]
  },
  "assets": {
    "figures": [...],
    "tables": [...],
    "citations": [...]
  }
}
```
