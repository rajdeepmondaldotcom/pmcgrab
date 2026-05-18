# Output Format

PMCGrab emits JSON-serializable article dictionaries for RAG, analytics, and
downstream LLM workflows. The default output is schema V4. V2 and V3 remain
available for compatibility by passing `schema_version=2` or `schema_version=3`.

## V4 Top-Level Shape

```json
{
  "schema_version": 4,
  "has_data": true,
  "article": {
    "identifiers": {
      "pmc_id": "7181753",
      "pmcid": "PMC7181753",
      "pmid": "32327715",
      "doi": "10.1038/s42003-020-0922-4",
      "publisher_id": "",
      "other": {},
      "all": []
    },
    "title": {
      "main": "Single-cell transcriptomes of the human skin reveal ...",
      "subtitle": "",
      "translated": [],
      "records": []
    },
    "publication": {
      "journal": { "title": "Communications Biology" },
      "dates": {
        "published": {
          "epub": {
            "source_text": "2020 04 24",
            "date": "2020-04-24",
            "precision": "day",
            "year": "2020",
            "month": "04",
            "day": "24"
          }
        },
        "history": {},
        "version_history": []
      }
    },
    "metadata": {
      "keywords": [],
      "keyword_groups": [],
      "counts": {}
    }
  },
  "contributors": {
    "people": [],
    "affiliations": [],
    "author_notes": {}
  },
  "content": {
    "abstracts": [],
    "primary_abstract": {},
    "sections": []
  },
  "assets": {
    "references": [],
    "tables": [],
    "figures": [],
    "equations": { "records": [], "mathml": [], "tex": [] },
    "supplementary_material": []
  },
  "relations": [],
  "quality": {
    "status": "complete",
    "diagnostics": [],
    "summary": {
      "abstract_count": 1,
      "section_count": 7,
      "block_count": 82,
      "reference_count": 42,
      "relation_count": 120,
      "generic_fallback_count": 0
    },
    "coverage": {
      "unrepresented_text_count": 0,
      "generic_fallback_count": 0,
      "duplicate_xml_id_count": 0
    }
  },
  "provenance": {
    "pmcgrab_version": "1.0.10",
    "parse_timestamp": "2024-01-01T00:00:00+00:00",
    "source": "ncbi_entrez",
    "xml_source_path": ""
  }
}
```

## Core Groups

| Group          | Notes                                                                  |
| -------------- | ---------------------------------------------------------------------- |
| `article`      | Identifiers, title, publication, compliance, and metadata.             |
| `contributors` | Contributors, affiliations, and author notes.                          |
| `content`      | Abstract records and ordered body section tree.                        |
| `assets`       | Full bibliography, tables, figures, equations, and supplementary data. |
| `relations`    | Inline xrefs, contributor-affiliation links, targets, and resolution.  |
| `quality`      | Parse status, diagnostics, and output counts.                          |
| `provenance`   | Parser version, parse timestamp, source, and local XML path.           |

Missing optional values are normalized to `""`, `{}`, or `[]` depending on
field shape. Date records preserve precision instead of inventing missing
month/day values.

V4 records include source metadata where PMCGrab has access to the source XML:
`source.jats_tag`, XML `attrs`, an XPath-like `path`, and an ordinal. The
output intentionally does not include raw XML payloads.

Body and abstract content is emitted as typed blocks instead of a single
flattened text stream. Known JATS blocks such as `paragraph`, `list`,
`def_list`, `boxed_text`, `formula`, `figure_ref`, `table_ref`, and
`supplementary_ref` keep their own structure. Unsupported but meaningful JATS
elements are emitted as `unknown_block` records with `jats_tag`, `attrs`,
`text`, nested `children`, `source`, and `parse_status: "generic_fallback"` so
their text is still represented in JSON. Formula MathML is represented as a
JSON tree (`tag`, `attrs`, `text`, `children`) rather than raw XML markup.

## Access Article Data

```python
from pmcgrab import process_single_pmc

data = process_single_pmc("7181753")

if data:
    print(data["article"]["title"]["main"])
    print(data["article"]["publication"]["journal"]["title"])
    print(data["article"]["identifiers"]["doi"])

    first_abstract = data["content"]["primary_abstract"]
    first_block = first_abstract["blocks"][0]
    print(first_block["text"][:300])

    print([section["title"] for section in data["content"]["sections"]])
```

## Prepare Vector Chunks

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
        "pmc_id": data["article"]["identifiers"]["pmc_id"],
        "journal": data["article"]["publication"]["journal"]["title"],
        "doi": data["article"]["identifiers"]["doi"],
    }

    for abstract_section in data["content"]["abstracts"]:
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

## Compatibility

```python
from pmcgrab import Paper, process_single_pmc

v2_data = process_single_pmc("7181753", schema_version=2)
v2_paper_dict = Paper.from_pmc("7181753").to_dict(schema_version=2)
v3_data = process_single_pmc("7181753", schema_version=3)
```

V2 keeps the previous top-level `identifiers`, `title`, `publication`,
`contributors`, and `content.abstract` shape. V3 keeps the first grouped
`article`/`content`/`assets` contract. New projects should use V4.
