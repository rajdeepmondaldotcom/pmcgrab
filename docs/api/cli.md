# Command Line Interface

PMCGrab's command-line interface for batch processing and article retrieval.

## CLI Module

::: pmcgrab.cli.pmcgrab_cli

## Usage Examples

### Basic Commands

```bash
# Process single paper
uv run python -m pmcgrab PMC7181753

# Process multiple papers
uv run python -m pmcgrab PMC7181753 PMC3539614 PMC5454911
```

### Advanced Options

```bash
# Custom output directory
uv run python -m pmcgrab --output-dir ./results PMC7181753

# Parallel processing
uv run python -m pmcgrab --workers 8 PMC7181753 PMC3539614

# From file input
uv run python -m pmcgrab --input-file pmc_ids.txt --max-retries 3
```

### All Options

- `--output-dir`: Specify output directory (default: ./pmc_output)
- `--workers`: Number of parallel workers (default: 4)
- `--email`: Contact email for NCBI API
- `--input-file`: Read PMC IDs from file
- `--max-retries`: Maximum retry attempts for failed downloads
- `--batch-size`: Number of articles per batch
- `--timeout`: Request timeout in seconds
- `--verbose`: Enable verbose logging
- `--help`: Show help message
