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

        if len(data["abstract_text"]) < 500:
            print(f"Skipping PMC{pmcid}: abstract too short")
            continue

        output_file = output_path / f"PMC{data['pmc_id']}.json"
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
                "pmcid": data["pmc_id"],
                "title": data["title"],
                "journal": data["journal_title"],
                "published_date": data["published_date"],
                "doi": data["article_id"].get("doi"),
                "author_count": len(data["authors"]),
                "abstract_length": len(data["abstract_text"]),
                "section_count": len(data["body"]),
                "word_count": data["word_count"],
            }
        )

    return pd.DataFrame(rows)


df = create_papers_dataframe(["7181753", "3539614", "3084273"])
print(df[["pmcid", "journal", "section_count", "word_count"]])
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
print(f"Total words: {sum(item['word_count'] for item in parsed)}")
```
