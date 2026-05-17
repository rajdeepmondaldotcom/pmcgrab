# Output Format

PMCGrab emits JSON-serializable dictionaries designed for RAG, analytics, and
downstream LLM workflows. The same normalized field names are used by the
Python processing helpers, `Paper.to_dict()`, and the CLI JSON output.

## Top-Level Shape

```json
{
  "pmc_id": "7181753",
  "article_id": {
    "pmcid": "PMC7181753",
    "pmid": "32327715",
    "doi": "10.1038/s42003-020-0922-4"
  },
  "title": "Single-cell transcriptomes of the human skin reveal ...",
  "has_data": true,
  "abstract": {
    "Abstract": "Fibroblasts are an essential cell population ..."
  },
  "abstract_text": "Fibroblasts are an essential cell population ...",
  "body": {
    "Introduction": "The skin is the outermost protective barrier ...",
    "Results": "The anatomy of the skin can vary ..."
  },
  "body_nested": {
    "Results": {
      "scRNA-seq analysis of sun-protected human skin": {
        "_text": "..."
      }
    }
  },
  "paragraphs": [
    {
      "section": "Introduction",
      "subsection": null,
      "paragraph_index": 0,
      "text": "..."
    }
  ],
  "full_text": "...",
  "toc": ["Introduction", "Results", "Discussion", "Methods"],
  "authors": [
    {
      "First_Name": "...",
      "Last_Name": "...",
      "Email": "...",
      "Affiliations": "..."
    }
  ],
  "journal_title": "Communications Biology",
  "published_date": {
    "epub": "2020-04-24"
  },
  "citations": [
    {
      "title": "...",
      "authors": "...",
      "doi": "...",
      "pmid": "..."
    }
  ],
  "tables": [],
  "figures": [],
  "permissions": {},
  "funding": [],
  "word_count": 12452,
  "_meta": {
    "pmcgrab_version": "1.0.7",
    "source": "ncbi_entrez",
    "xml_source_path": null
  }
}
```

## Core Fields

| Field            | Type    | Notes                                                                          |
| ---------------- | ------- | ------------------------------------------------------------------------------ |
| `pmc_id`         | string  | Numeric PMCID without the `PMC` prefix.                                        |
| `article_id`     | object  | Identifier map from the article metadata. DOI and PMID live here when present. |
| `title`          | string  | Clean article title.                                                           |
| `has_data`       | boolean | `false` only for empty `Paper` objects.                                        |
| `abstract`       | object  | Structured abstract by heading.                                                |
| `abstract_text`  | string  | Plain-text abstract for embeddings and prompts.                                |
| `body`           | object  | Flat map of section title to clean section text.                               |
| `body_nested`    | object  | Hierarchical body preserving subsections.                                      |
| `paragraphs`     | array   | Paragraph-level records for chunking.                                          |
| `full_text`      | string  | Abstract plus body as one continuous text field.                               |
| `toc`            | array   | Section titles in document order.                                              |
| `authors`        | array   | Normalized author records.                                                     |
| `journal_title`  | string  | Journal title.                                                                 |
| `published_date` | object  | Publication dates keyed by type, such as `epub` or `ppub`.                     |
| `citations`      | array   | Parsed reference list.                                                         |
| `tables`         | array   | Parsed table data and metadata when extractable.                               |
| `figures`        | array   | Figure labels, captions, graphics, and alt text when present.                  |
| `_meta`          | object  | Processing provenance. Present in `process_single_pmc()` output.               |

## Metadata Groups

PMCGrab also returns optional scholarly metadata when present in the source
article:

```python
identifier_fields = ["article_id", "journal_id", "issn"]
publication_fields = ["publisher_name", "publisher_location", "volume", "issue"]
classification_fields = ["article_types", "article_categories", "keywords"]
legal_fields = ["permissions", "copyright", "license"]
research_fields = ["funding", "ethics", "supplementary_material", "equations"]
extra_fields = ["counts", "self_uri", "related_articles", "conference"]
```

Missing optional values are normalized to `""`, `{}`, or `[]` depending on the
field shape. That keeps JSON output predictable and avoids `None` checks for the
common downstream paths.

## Usage Examples

### Access Article Data

```python
from pmcgrab import process_single_pmc

data = process_single_pmc("7181753")

if data:
    print(data["title"])
    print(data["journal_title"])
    print(data["article_id"].get("doi"))
    print(data["abstract_text"][:300])
    print(list(data["body"].keys()))
```

### Prepare Vector Chunks

```python
def prepare_for_vector_db(data):
    chunks = [
        {
            "content": data["title"],
            "metadata": {
                "pmc_id": data["pmc_id"],
                "type": "title",
                "journal": data["journal_title"],
            },
        },
        {
            "content": data["abstract_text"],
            "metadata": {
                "pmc_id": data["pmc_id"],
                "type": "abstract",
                "journal": data["journal_title"],
            },
        },
    ]

    for paragraph in data["paragraphs"]:
        chunks.append(
            {
                "content": paragraph["text"],
                "metadata": {
                    "pmc_id": data["pmc_id"],
                    "type": "paragraph",
                    "section": paragraph["section"],
                    "subsection": paragraph["subsection"],
                    "paragraph_index": paragraph["paragraph_index"],
                },
            }
        )

    return chunks
```

### Build RAG Documents

```python
from pmcgrab import process_single_pmc


def create_rag_documents(pmcids):
    documents = []

    for pmcid in pmcids:
        data = process_single_pmc(pmcid)
        if not data:
            continue

        documents.append(
            {
                "id": f"PMC{data['pmc_id']}",
                "text": data["full_text"],
                "metadata": {
                    "title": data["title"],
                    "journal": data["journal_title"],
                    "published_date": data["published_date"],
                    "doi": data["article_id"].get("doi"),
                    "section_count": data["section_count"],
                },
            }
        )

    return documents
```

## CLI Files

The CLI writes one JSON file per article by default:

```text
pmc_output/
├── PMC7181753.json
├── PMC3539614.json
└── PMC3084273.json
```

With `--format jsonl`, the CLI writes newline-delimited JSON records to a single
`results.jsonl` file in the output directory.
