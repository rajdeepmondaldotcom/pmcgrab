# Command Line Interface

PMCGrab's CLI processes PMC IDs, PubMed IDs, DOIs, ID files, local XML files, and local XML directories into JSON or JSONL output.

## Quick Commands

```bash
# PMC IDs. Accepts PMC7181753, pmc7181753, or 7181753.
uv run python -m pmcgrab --pmcids 7181753 3539614 --output-dir ./results

# PubMed IDs, converted to PMC IDs before processing.
uv run python -m pmcgrab --pmids 33087749 --output-dir ./results

# DOIs, converted to PMC IDs before processing.
uv run python -m pmcgrab --dois 10.1038/s41586-020-2832-5 --output-dir ./results

# IDs from a text file.
uv run python -m pmcgrab --from-id-file ids.txt --output-dir ./results

# Local JATS XML directory, no network.
uv run python -m pmcgrab --from-dir ./pmc_bulk_xml --output-dir ./results

# Specific local XML files, no network.
uv run python -m pmcgrab --from-file article1.xml article2.xml --output-dir ./results
```

## Input Modes

Exactly one input mode is required.

| Option              | Description                                                                                                                                              |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--pmcids`, `--ids` | PMC IDs to download and process. Bare numeric IDs are treated as PMC IDs.                                                                                |
| `--pmids`           | PubMed IDs to convert to PMC IDs before processing.                                                                                                      |
| `--dois`            | DOIs to convert to PMC IDs before processing.                                                                                                            |
| `--from-id-file`    | Text file with one identifier per line. Blank lines and `#` comments are ignored. Bare numeric IDs are treated as PMC IDs; use `--pmids` for PubMed IDs. |
| `--from-dir`        | Directory of local JATS XML files.                                                                                                                       |
| `--from-file`       | One or more local JATS XML files.                                                                                                                        |

## Output Options

```bash
# One JSON file per successful article.
uv run python -m pmcgrab --pmcids 7181753 --output-dir ./results --format json

# One JSONL file containing all successful articles.
uv run python -m pmcgrab --pmcids 7181753 3539614 --output-dir ./results --format jsonl
```

Output files:

```text
results/
├── PMC7181753.json
├── PMC3539614.json
└── summary.json
```

For JSONL:

```text
results/
├── output.jsonl
└── summary.json
```

`summary.json` maps each input name or PMC ID to `true` or `false`.

## Performance and Logging

```bash
# Use four worker threads.
uv run python -m pmcgrab --pmcids 7181753 3539614 --workers 4

# --batch-size is an alias for --workers.
uv run python -m pmcgrab --pmcids 7181753 3539614 --batch-size 4

# Enable debug logging.
uv run python -m pmcgrab --pmcids 7181753 --verbose

# Suppress progress bars.
uv run python -m pmcgrab --pmcids 7181753 --quiet

# Print package version.
uv run python -m pmcgrab --version
```

## ID File Format

```text
# ids.txt
PMC7181753
3539614
10.1038/s41586-020-2832-5
```

Run:

```bash
uv run python -m pmcgrab --from-id-file ids.txt --output-dir ./results
```

Bare numeric values in ID files are interpreted as PMC IDs. If your file contains PubMed IDs, convert them with `--pmids` or call `normalize_pmid()` in Python first.

## Current Help Output

```text
usage: __main__.py [-h] (--pmcids PMCIDS [PMCIDS ...] |
                   --pmids PMIDS [PMIDS ...] | --dois DOIS [DOIS ...] |
                   --from-id-file FROM_ID_FILE | --from-dir FROM_DIR |
                   --from-file FROM_FILES [FROM_FILES ...])
                   [--output-dir OUTPUT_DIR] [--batch-size BATCH_SIZE]
                   [--format {json,jsonl}] [--verbose] [--quiet] [--version]
```
