# CLI Examples

Practical command-line examples for the current PMCGrab CLI.

## PMC IDs

```bash
uv run python -m pmcgrab --pmcids 7181753 --output-dir ./papers
uv run python -m pmcgrab --pmcids PMC7181753 PMC3539614 --workers 4
```

## PubMed IDs and DOIs

```bash
uv run python -m pmcgrab --pmids 33087749 --output-dir ./papers
uv run python -m pmcgrab --dois 10.1038/s41586-020-2832-5 --output-dir ./papers
```

## Text File

Create `pmcids.txt`:

```text
# Comments and blank lines are ignored.
PMC7181753
3539614
10.1038/s41586-020-2832-5
```

Process the list:

```bash
uv run python -m pmcgrab --from-id-file pmcids.txt --output-dir ./papers
```

Bare numeric values in `--from-id-file` are treated as PMC IDs. Use `--pmids` for PubMed IDs.

## Local XML

```bash
# Directory of JATS XML files.
uv run python -m pmcgrab --from-dir ./pmc_bulk_xml --output-dir ./papers

# Specific XML files.
uv run python -m pmcgrab --from-file article1.xml article2.xml --output-dir ./papers
```

## JSONL Output

```bash
uv run python -m pmcgrab \
    --pmcids 7181753 3539614 \
    --output-dir ./papers \
    --format jsonl
```

This writes `output.jsonl` plus `summary.json`.

The JSON and JSONL output is strict JSON. Missing values from pandas/numpy
tables and author metadata are emitted as `null`.

## Common Parameters

| Parameter                   | Description                     | Example                 |
| --------------------------- | ------------------------------- | ----------------------- |
| `--output-dir`, `--out`     | Output directory for JSON files | `--output-dir ./papers` |
| `--workers`, `--batch-size` | Number of worker threads        | `--workers 4`           |
| `--format`                  | `json` or `jsonl`               | `--format jsonl`        |
| `--verbose`                 | Enable debug logging            | `--verbose`             |
| `--quiet`                   | Suppress progress bars          | `--quiet`               |
| `--version`                 | Print installed version         | `--version`             |
