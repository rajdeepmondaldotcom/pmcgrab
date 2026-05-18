# Advanced Usage

These examples build on the normalized dictionary returned by
`process_single_pmc()` and `process_single_local_xml()`.

## Filter Papers Before Saving

```python
import json
from pathlib import Path

from pmcgrab import process_single_pmc


def process_with_filtering(pmcids, output_dir="filtered_output"):
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    kept = []

    for pmcid in pmcids:
        data = process_single_pmc(pmcid)
        if not data:
            continue

        abstract_blocks = data["content"]["abstracts"][0]["blocks"]
        abstract_text = abstract_blocks[0]["text"] if abstract_blocks else ""
        if len(abstract_text) < 500:
            print(f"Skipping PMC{pmcid}: abstract too short")
            continue

        output_file = output_path / f"PMC{data['article']['identifiers']['pmc_id']}.json"
        output_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        kept.append(data)

    return kept


papers = process_with_filtering(["7181753", "3539614", "3084273"])
print(f"Saved {len(papers)} papers")
```

## Create a DataFrame

```python
import pandas as pd

from pmcgrab import process_single_pmc


def create_papers_dataframe(pmcids):
    rows = []

    for pmcid in pmcids:
        data = process_single_pmc(pmcid)
        if not data:
            continue

        rows.append(
            {
                "pmcid": data["article"]["identifiers"]["pmc_id"],
                "title": data["article"]["title"]["main"],
                "journal": data["article"]["publication"]["journal"]["title"],
                "published_date": data["article"]["publication"]["dates"]["published"],
                "doi": data["article"]["identifiers"]["doi"],
                "author_count": len(data["article"]["contributors"]["authors"]),
                "abstract_length": sum(
                    len(block["text"])
                    for section in data["content"]["abstracts"]
                    for block in section["blocks"]
                    if block["type"] == "paragraph"
                ),
                "section_count": len(data["content"]["sections"]),
            }
        )

    return pd.DataFrame(rows)


df = create_papers_dataframe(["7181753", "3539614", "3084273"])
print(df[["pmcid", "journal", "section_count"]])
```

## Retry Failed Network Calls

`process_single_pmc()` already returns `None` for failed processing. If your
workflow needs extra retry behavior around the whole operation, keep the retry
loop at the call site:

```python
import time

from pmcgrab import process_single_pmc


def process_with_retries(pmcid, attempts=3, delay_seconds=2):
    for attempt in range(1, attempts + 1):
        data = process_single_pmc(pmcid)
        if data:
            return data

        if attempt < attempts:
            time.sleep(delay_seconds)

    return None
```

## Stream Large Result Sets

For large jobs, process and persist one article at a time so the full corpus
does not stay in memory:

```python
import json
from pathlib import Path

from pmcgrab import process_single_pmc


def stream_to_jsonl(pmcids, output_file="papers.jsonl"):
    path = Path(output_file)

    with path.open("w", encoding="utf-8") as handle:
        for pmcid in pmcids:
            data = process_single_pmc(pmcid)
            if not data:
                continue

            handle.write(json.dumps(data, ensure_ascii=False) + "\n")


stream_to_jsonl(["7181753", "3539614", "3084273"])
```

## Local XML Analytics

```python
from pmcgrab import process_local_xml_dir

results = process_local_xml_dir("./pmc_bulk_xml", workers=16)
parsed = [data for data in results.values() if data]

print(f"Parsed {len(parsed)} articles")
print(f"Total top-level sections: {sum(len(item['content']['sections']) for item in parsed)}")
```
