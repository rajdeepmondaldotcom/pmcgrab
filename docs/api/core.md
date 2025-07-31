# Core API

The core API provides the main functions for processing PMC articles.

## Primary Processing Function

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

## Example Usage

```python
from pmcgrab.application.processing import process_single_pmc
from pmcgrab.infrastructure.settings import next_email

# Process a single PMC article
email = next_email()
data = process_single_pmc("7114487")

if data:
    print(f"Title: {data['title']}")
    print(f"Authors: {len(data['authors'])}")
    print(f"Sections: {list(data['body'].keys())}")
```
