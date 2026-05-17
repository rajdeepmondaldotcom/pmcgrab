# Command Line Interface

PMCGrab's CLI lives in `pmcgrab.cli.pmcgrab_cli`.

## CLI Module

::: pmcgrab.cli.pmcgrab_cli

## Usage Examples

```bash
# Process one PMC ID.
uv run python -m pmcgrab --pmcids 7181753

# Process multiple PMC IDs.
uv run python -m pmcgrab --pmcids 7181753 3539614 5454911

# Process PubMed IDs.
uv run python -m pmcgrab --pmids 33087749

# Process local XML without network access.
uv run python -m pmcgrab --from-dir ./pmc_bulk_xml --output-dir ./results
```

## Options

- `--pmcids`, `--ids`: PMC IDs to process.
- `--pmids`: PubMed IDs to convert to PMC IDs.
- `--dois`: DOIs to convert to PMC IDs.
- `--from-id-file`: Text file containing identifiers.
- `--from-dir`: Directory of local XML files.
- `--from-file`: One or more local XML files.
- `--output-dir`, `--out`: Output directory.
- `--workers`, `--batch-size`: Number of worker threads.
- `--format`: `json` or `jsonl`.
- `--verbose`: Enable debug logging.
- `--quiet`: Suppress progress bars.
- `--version`: Print the installed PMCGrab version.
