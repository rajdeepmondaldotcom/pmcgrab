# Output Format

PMCGrab emits clean paper JSON by default. The default schema is optimized for
signal-to-noise: the paper itself, plus figures/images and tables, without
parser trace metadata, diagnostics, bibliography records, contributor metadata,
or provenance.

Use `--full-json` in the CLI, or `output_style="full"` in Python, when you need
the metadata-rich V4 contract. V2 and V3 remain available only through the full
output path.

## Default Paper Shape

```json
{
  "schema": "pmcgrab.paper.v1",
  "has_data": true,
  "identifiers": {
    "pmcid": "PMC7181753",
    "pmid": "32327715",
    "doi": "10.1038/s42003-020-0922-4"
  },
  "paper": {
    "title": "Single-cell transcriptomes of the human skin reveal ...",
    "abstract": [
      {
        "title": "Abstract",
        "kind": "primary",
        "content": [{ "type": "paragraph", "text": "..." }],
        "sections": []
      }
    ],
    "body": [
      {
        "id": "s1",
        "title": "Introduction",
        "content": [{ "type": "paragraph", "text": "..." }],
        "sections": []
      }
    ]
  },
  "assets": {
    "images": [],
    "tables": []
  }
}
```

## Core Groups

| Group         | Notes                                                     |
| ------------- | --------------------------------------------------------- |
| `identifiers` | Minimal paper identifiers: PMCID, PMID, and DOI.          |
| `paper`       | Title, structured abstract, and nested body section tree. |
| `assets`      | Clean image/figure records and clean table records.       |

Body and abstract content is emitted as readable typed blocks. Supported block
types include `paragraph`, `list`, `definition_list`, `formula`, `quote`,
`boxed_text`, `code`, `preformat`, `figure_ref`, `table_ref`,
`supplementary_ref`, and `unknown_block`.

## Images And Tables

When image fetching is enabled with `--with-images` or
`process_single_pmc_with_assets()`, clean image records include local file paths:

```json
{
  "id": "f1",
  "label": "Figure 1",
  "caption": "...",
  "files": [
    {
      "href": "fig1.jpg",
      "local_path": "images/fig1.jpg",
      "status": "downloaded",
      "mime_type": "image/jpeg"
    }
  ]
}
```

Tables keep one canonical row representation:

```json
{
  "id": "t1",
  "label": "Table 1",
  "caption": "...",
  "columns": ["A", "B"],
  "rows": [{ "A": "1", "B": "2" }],
  "footnotes": []
}
```

## Access Article Data

```python
from pmcgrab import process_single_pmc

data = process_single_pmc("7181753")

if data:
    print(data["paper"]["title"])
    print(data["identifiers"]["doi"])
    print(data["paper"]["abstract"][0]["content"][0]["text"][:300])
    print([section["title"] for section in data["paper"]["body"]])
```

## Prepare Vector Chunks

```python
def iter_text_blocks(sections):
    for section in sections:
        for block in section["content"]:
            if block["type"] == "paragraph":
                yield section, block
        yield from iter_text_blocks(section["sections"])


def prepare_for_vector_db(data):
    chunks = []
    metadata_base = {
        "pmcid": data["identifiers"]["pmcid"],
        "doi": data["identifiers"]["doi"],
    }

    for abstract_section in data["paper"]["abstract"]:
        for block in abstract_section["content"]:
            if block["type"] == "paragraph":
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

    for section, block in iter_text_blocks(data["paper"]["body"]):
        chunks.append(
            {
                "content": block["text"],
                "metadata": {
                    **metadata_base,
                    "type": "paragraph",
                    "section": section["title"],
                },
            }
        )

    return chunks
```

## Full JSON Compatibility

```python
from pmcgrab import Paper, process_single_pmc

full_v4 = process_single_pmc("7181753", output_style="full")
v2_data = process_single_pmc("7181753", output_style="full", schema_version=2)
v2_paper_dict = Paper.from_pmc("7181753").to_dict(
    output_style="full",
    schema_version=2,
)
v3_data = process_single_pmc("7181753", output_style="full", schema_version=3)
```

Full V4 keeps article metadata, contributors, bibliography, relations, quality
diagnostics, provenance, source paths, and parse coverage. New projects should
start with the default `pmcgrab.paper.v1` view and opt in to full JSON only when
that extra metadata is needed.
