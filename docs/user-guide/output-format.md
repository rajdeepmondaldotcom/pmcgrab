# Output Format

PMCGrab emits JSON-serializable article dictionaries designed for RAG,
analytics, and downstream LLM workflows. The same canonical v2 schema is used
by the Python processing helpers, `Paper.to_dict()`, and CLI JSON/JSONL output.

## Top-Level Shape

```json
{
  "schema_version": 2,
  "has_data": true,
  "identifiers": {
    "pmc_id": "7181753",
    "pmcid": "PMC7181753",
    "pmid": "32327715",
    "doi": "10.1038/s42003-020-0922-4",
    "publisher_id": "",
    "other": {}
  },
  "title": {
    "main": "Single-cell transcriptomes of the human skin reveal ...",
    "subtitle": "",
    "translated": []
  },
  "contributors": {
    "authors": [
      {
        "First_Name": "...",
        "Last_Name": "...",
        "Email": "...",
        "Affiliations": "..."
      }
    ],
    "non_author_contributors": [],
    "author_notes": {}
  },
  "publication": {
    "journal": {
      "title": "Communications Biology",
      "alternate_titles": [],
      "ids": {},
      "issn": {}
    },
    "publisher": {
      "name": "",
      "alternate_names": [],
      "location": "",
      "alternate_locations": []
    },
    "classification": {
      "article_types": ["research-article"],
      "article_categories": []
    },
    "dates": {
      "published": {
        "epub": "2020-04-24"
      },
      "history": {},
      "version_history": []
    },
    "issue": {
      "volume": "",
      "issue": "",
      "first_page": "",
      "last_page": "",
      "elocation_id": ""
    },
    "conference": {}
  },
  "content": {
    "abstract_type": "",
    "abstract": [
      {
        "id": "",
        "title": "Abstract",
        "level": 0,
        "blocks": [
          {
            "type": "paragraph",
            "id": "",
            "text": "Fibroblasts are an essential cell population ..."
          }
        ],
        "children": []
      }
    ],
    "translated_abstracts": [],
    "sections": [
      {
        "id": "s1",
        "title": "Introduction",
        "level": 1,
        "blocks": [
          {
            "type": "paragraph",
            "id": "p1",
            "text": "The skin is the outermost protective barrier ..."
          }
        ],
        "children": []
      }
    ],
    "appendices": [],
    "glossary": [],
    "footnotes": "",
    "acknowledgements": [],
    "notes": []
  },
  "assets": {
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
    "equations": {
      "mathml": [],
      "tex": []
    },
    "supplementary_material": []
  },
  "compliance": {
    "permissions": {},
    "copyright": "",
    "license": "",
    "ethics": {},
    "funding": []
  },
  "metadata": {
    "keywords": ["fibroblasts", "skin aging", "single-cell RNA-seq"],
    "counts": {},
    "self_uri": [],
    "related_articles": [],
    "custom_meta": {}
  },
  "provenance": {
    "pmcgrab_version": "1.0.8",
    "parse_timestamp": "2024-01-01T00:00:00+00:00",
    "source": "ncbi_entrez",
    "xml_source_path": ""
  }
}
```

## Core Groups

| Group            | Type    | Notes                                                                     |
| ---------------- | ------- | ------------------------------------------------------------------------- |
| `schema_version` | integer | Output schema version. Current value is `2`.                              |
| `has_data`       | boolean | `false` only for empty `Paper` objects.                                   |
| `identifiers`    | object  | PMC, PubMed, DOI, publisher, and other article identifiers.               |
| `title`          | object  | Main, subtitle, and translated title values.                              |
| `contributors`   | object  | Authors, non-author contributors, and author notes.                       |
| `publication`    | object  | Journal, publisher, classification, date, issue, and conference metadata. |
| `content`        | object  | Canonical article text: abstract records and ordered section tree.        |
| `assets`         | object  | Citations, tables, figures, equations, and supplementary material.        |
| `compliance`     | object  | Permissions, copyright, license, ethics, and funding data.                |
| `metadata`       | object  | Keywords, counts, links, related articles, and custom metadata.           |
| `provenance`     | object  | Parser version, parse timestamp, source, and XML source path.             |

Missing optional values are normalized to `""`, `{}`, or `[]` depending on the
field shape. That keeps output predictable and avoids `null` checks for common
downstream paths.

## Canonical Content

Article text appears once, under `content`.

- `content.abstract` is an ordered list of abstract section records.
- `content.sections` is an ordered recursive tree.
- Each section has `id`, `title`, `level`, `blocks`, and `children`.
- Paragraph text is stored in blocks with `type: "paragraph"`.
- Tables and figures are stored once under `assets`; section blocks reference
  them with `table_ref` or `figure_ref`.
- Figure `link` is the primary graphic reference. Additional figure graphics
  live in `alternate_links` so the same URL is not repeated in two fields.

The JSON output no longer includes duplicate top-level views such as `body`,
`body_nested`, `paragraphs`, `abstract_text`, or `full_text`. The `Paper` object
still exposes helper methods such as `body_as_dict()`, `body_as_paragraphs()`,
and `full_text()` for callers that want derived views in Python.

## Usage Examples

### Access Article Data

```python
from pmcgrab import process_single_pmc

data = process_single_pmc("7181753")

if data:
    print(data["title"]["main"])
    print(data["publication"]["journal"]["title"])
    print(data["identifiers"]["doi"])

    first_abstract_block = data["content"]["abstract"][0]["blocks"][0]
    print(first_abstract_block["text"][:300])

    print([section["title"] for section in data["content"]["sections"]])
```

### Prepare Vector Chunks

```python
def iter_paragraph_blocks(sections):
    for section in sections:
        for block in section["blocks"]:
            if block["type"] == "paragraph":
                yield section, block
        yield from iter_paragraph_blocks(section["children"])


def prepare_for_vector_db(data):
    chunks = []
    metadata_base = {
        "pmc_id": data["identifiers"]["pmc_id"],
        "journal": data["publication"]["journal"]["title"],
        "doi": data["identifiers"]["doi"],
    }

    for abstract_section in data["content"]["abstract"]:
        for block in abstract_section["blocks"]:
            chunks.append(
                {
                    "content": block["text"],
                    "metadata": {
                        **metadata_base,
                        "type": "abstract",
                        "section": abstract_section["title"],
                    },
                }
            )

    for section, block in iter_paragraph_blocks(data["content"]["sections"]):
        chunks.append(
            {
                "content": block["text"],
                "metadata": {
                    **metadata_base,
                    "type": "paragraph",
                    "section": section["title"],
                    "section_level": section["level"],
                },
            }
        )

    return chunks
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
`output.jsonl` file in the output directory.
