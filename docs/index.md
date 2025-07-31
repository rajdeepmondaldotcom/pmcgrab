---
title: Home
template: home.html
hide:
  - navigation
  - toc
---

<div class="grid cards" markdown>

- :material-clock-fast:{ .lg .middle } **5-minute setup**

  ***

  Install PMCGrab and process multiple papers immediately.

  [:octicons-arrow-right-24: Quick Start](getting-started/quick-start.md)

- :material-book-open-page-variant:{ .lg .middle } **User Guide**

  ***

  Comprehensive guides for every feature.

  [:octicons-arrow-right-24: User Guide](user-guide/basic-usage.md)

- :material-code-tags:{ .lg .middle } **API Reference**

  ***

  Auto-generated docs for every function and class.

  [:octicons-arrow-right-24: API Reference](api/core.md)

- :material-lightbulb:{ .lg .middle } **Examples**

  ***

  Real-world usage & advanced patterns.

  [:octicons-arrow-right-24: Examples](examples/python-examples.md)

</div>

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
