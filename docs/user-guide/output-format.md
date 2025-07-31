# Output Format

PMCGrab produces structured JSON output optimized for AI and machine learning applications.

## JSON Structure Overview

Each processed PMC article returns a comprehensive dictionary with the following structure:

```json
{
  "pmc_id": "7114487",
  "title": "Machine learning approaches in cancer research",
  "abstract": "Recent advances in machine learning have revolutionized...",
  "authors": [...],
  "body": {...},
  "journal": "Nature Medicine",
  "pub_date": "2023-05-15",
  "doi": "10.1038/s41591-023-02345-6",
  "figures": [...],
  "tables": [...],
  "references": [...]
}
```

## Complete Example

Here's a real example of the JSON structure returned by `process_single_pmc`:

```json
{
  "pmc_id": "7114487",
  "title": "Machine learning approaches in cancer research: A systematic review",
  "abstract": "Recent advances in machine learning have revolutionized the field of cancer research, enabling more accurate diagnosis, prognosis, and treatment selection. This systematic review examines current applications and future prospects.",
  "authors": [
    {
      "First_Name": "John",
      "Last_Name": "Doe",
      "Affiliation": "Cancer Research Institute, University of Science"
    },
    {
      "First_Name": "Jane",
      "Last_Name": "Smith",
      "Affiliation": "Department of Oncology, Medical Center"
    }
  ],
  "body": {
    "Introduction": "Cancer remains one of the leading causes of death worldwide...",
    "Methods": "We conducted a systematic review following PRISMA guidelines...",
    "Results": "Our analysis identified 127 studies that met inclusion criteria...",
    "Discussion": "The findings demonstrate significant potential for ML in cancer care...",
    "Conclusion": "Machine learning represents a transformative technology..."
  },
  "journal": "Nature Medicine",
  "pub_date": "2023-05-15",
  "doi": "10.1038/s41591-023-02345-6",
  "figures": [
    {
      "id": "fig1",
      "caption": "Overview of machine learning applications in cancer research",
      "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7114487/bin/fig1.jpg"
    }
  ],
  "tables": [
    {
      "id": "table1",
      "caption": "Summary of studies included in systematic review",
      "content": "..."
    }
  ],
  "references": [
    {
      "id": "ref1",
      "citation": "Smith J, et al. Deep learning for cancer diagnosis. Nature. 2022;123:456-789."
    }
  ]
}
```

## Field Descriptions

### Core Metadata

| Field      | Type   | Description                                      |
| ---------- | ------ | ------------------------------------------------ |
| `pmc_id`   | string | PubMed Central identifier (without "PMC" prefix) |
| `title`    | string | Complete article title                           |
| `abstract` | string | Article abstract text                            |
| `journal`  | string | Journal name                                     |
| `pub_date` | string | Publication date (ISO format)                    |
| `doi`      | string | Digital Object Identifier                        |

### Authors Array

```json
{
  "authors": [
    {
      "First_Name": "John",
      "Last_Name": "Doe",
      "Affiliation": "University Name"
    }
  ]
}
```

Each author object contains:

- `First_Name`: Author's first name
- `Last_Name`: Author's last name
- `Affiliation`: Institutional affiliation (when available)

### Body Sections

```json
{
  "body": {
    "Introduction": "The introduction section content...",
    "Methods": "The methods section content...",
    "Results": "The results section content...",
    "Discussion": "The discussion section content...",
    "Conclusion": "The conclusion section content..."
  }
}
```

Common section names include:

- Introduction / Background
- Methods / Materials and Methods
- Results
- Discussion
- Conclusion
- References (when included in body)

### Figures Array

```json
{
  "figures": [
    {
      "id": "fig1",
      "caption": "Description of the figure",
      "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7114487/bin/fig1.jpg"
    }
  ]
}
```

### Tables Array

```json
{
  "tables": [
    {
      "id": "table1",
      "caption": "Table description",
      "content": "Table content when extractable"
    }
  ]
}
```

### References Array

```json
{
  "references": [
    {
      "id": "ref1",
      "citation": "Complete citation text"
    }
  ]
}
```

## Usage Examples

### Accessing Article Data

```python
from pmcgrab.application.processing import process_single_pmc

data = process_single_pmc("7114487")

if data:
    # Basic information
    print(f"Title: {data['title']}")
    print(f"Journal: {data['journal']}")
    print(f"Authors: {len(data['authors'])}")

    # Content sections
    print(f"Available sections: {list(data['body'].keys())}")

    # Access specific sections
    if 'Introduction' in data['body']:
        intro = data['body']['Introduction']
        print(f"Introduction (first 200 chars): {intro[:200]}...")

    # Additional content
    print(f"Figures: {len(data.get('figures', []))}")
    print(f"Tables: {len(data.get('tables', []))}")
    print(f"References: {len(data.get('references', []))}")
```

### Processing Multiple Articles

```python
# ─── Process Multiple Articles ───────────────────────────────────────────────
import json
from pathlib import Path
from pmcgrab.application.processing import process_single_pmc
from pmcgrab.infrastructure.settings import next_email

PMC_IDS = ["7114487", "3084273", "7690653"]
OUTPUT_DIR = Path("articles")
OUTPUT_DIR.mkdir(exist_ok=True)

for pmcid in PMC_IDS:
    email = next_email()
    data = process_single_pmc(pmcid)

    if data:
        # Save complete JSON
        output_file = OUTPUT_DIR / f"PMC{pmcid}.json"
        with output_file.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"Saved PMC{pmcid}: {data['title'][:50]}...")
    else:
        print(f"Failed to process PMC{pmcid}")
```

## AI/ML Integration

### Vector Database Preparation

```python
def prepare_for_vector_db(data):
    """Prepare article data for vector database ingestion."""
    chunks = []

    # Add title and abstract as separate chunks
    chunks.append({
        'content': data['title'],
        'metadata': {
            'pmc_id': data['pmc_id'],
            'type': 'title',
            'journal': data['journal']
        }
    })

    chunks.append({
        'content': data['abstract'],
        'metadata': {
            'pmc_id': data['pmc_id'],
            'type': 'abstract',
            'journal': data['journal']
        }
    })

    # Add each body section as a chunk
    for section_name, content in data['body'].items():
        chunks.append({
            'content': content,
            'metadata': {
                'pmc_id': data['pmc_id'],
                'type': 'section',
                'section': section_name,
                'journal': data['journal']
            }
        })

    return chunks

# Usage
data = process_single_pmc("7114487")
if data:
    vector_chunks = prepare_for_vector_db(data)
    print(f"Created {len(vector_chunks)} chunks for vector database")
```

### RAG System Integration

```python
def create_rag_documents(pmcids):
    """Create documents for RAG system."""
    documents = []

    for pmcid in pmcids:
        data = process_single_pmc(pmcid)
        if data:
            # Combine sections into full text
            full_text = f"{data['title']}\n\n{data['abstract']}\n\n"
            full_text += "\n\n".join([
                f"{section}: {content}"
                for section, content in data['body'].items()
            ])

            documents.append({
                'id': f"PMC{pmcid}",
                'text': full_text,
                'metadata': {
                    'title': data['title'],
                    'journal': data['journal'],
                    'authors': [f"{a['First_Name']} {a['Last_Name']}" for a in data['authors']],
                    'pub_date': data.get('pub_date'),
                    'doi': data.get('doi')
                }
            })

    return documents

# Usage
pmcids = ["7114487", "3084273", "7690653"]
rag_docs = create_rag_documents(pmcids)
```

## File Output

### Individual JSON Files

When using the standard processing pattern, each article is saved as a separate JSON file:

```
pmc_output/
├── PMC7114487.json
├── PMC3084273.json
├── PMC7690653.json
├── PMC5707528.json
└── PMC7979870.json
```

### Batch Summary

You can also create summary files for batch processing:

```python
import json
from pathlib import Path

def save_batch_summary(results, output_dir):
    """Save a summary of batch processing results."""
    summary = {
        'total_processed': len(results),
        'articles': []
    }

    for pmcid, data in results:
        if data:
            summary['articles'].append({
                'pmc_id': pmcid,
                'title': data['title'],
                'journal': data['journal'],
                'authors_count': len(data['authors']),
                'sections': list(data['body'].keys()),
                'word_count': sum(len(content.split()) for content in data['body'].values())
            })

    summary_file = Path(output_dir) / "batch_summary.json"
    with summary_file.open('w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    return summary

# Usage with processing results
results = [(pmcid, process_single_pmc(pmcid)) for pmcid in PMC_IDS]
valid_results = [(pmcid, data) for pmcid, data in results if data is not None]
summary = save_batch_summary(valid_results, "pmc_output")
```

This structured JSON format provides everything needed for modern AI/ML workflows while maintaining human readability and programmatic access.
