# Command Line Interface

PMCGrab provides a powerful command-line interface for batch processing and article retrieval.

## Basic Usage

### Single Article

```bash
# Process a single PMC article
uv run uv run python -m pmcgrab PMC7181753

# Specify email (required by NCBI)
uv run uv run python -m pmcgrab --email your-email@example.com PMC7181753
```

### Multiple Articles

```bash
# Process multiple articles
uv run uv run python -m pmcgrab PMC7181753 PMC3539614 PMC5454911

# From a file (one PMC ID per line)
uv run uv run python -m pmcgrab --input-file pmc_ids.txt
```

## Command Options

### Output Configuration

```bash
# Custom output directory
uv run uv run python -m pmcgrab --output-dir ./results PMC7181753

# Create timestamped directory
uv run uv run python -m pmcgrab --output-dir ./results_$(date +%Y%m%d) PMC7181753
```

### Performance Options

```bash
# Parallel processing
uv run uv run python -m pmcgrab --workers 8 PMC7181753 PMC3539614

# Batch size configuration
uv run uv run python -m pmcgrab --batch-size 20 --workers 4 PMC7181753 PMC3539614

# Timeout settings
uv run uv run python -m pmcgrab --timeout 60 PMC7181753
```

### Error Handling

```bash
# Retry configuration
uv run python -m pmcgrab --max-retries 5 PMC7181753

# Verbose output
uv run python -m pmcgrab --verbose PMC7181753

# Suppress warnings
uv run python -m pmcgrab --quiet PMC7181753
```

## Complete Example

```bash
uv run python -m pmcgrab \
    --email your-email@example.com \
    --output-dir ./pmc_results \
    --workers 8 \
    --batch-size 25 \
    --max-retries 3 \
    --timeout 60 \
    --verbose \
    PMC7181753 PMC3539614 PMC5454911
```

## Input Files

### Text File Format

Create `pmc_ids.txt`:

```
7181753
3539614
5454911
8378853
7462677
```

Then run:

```bash
uv run python -m pmcgrab --input-file pmc_ids.txt --email your-email@example.com
```

### CSV Input

For CSV files with PMC IDs in a specific column:

```bash
# If PMC IDs are in 'pmcid' column
uv run python -m pmcgrab --input-csv articles.csv --pmcid-column pmcid

# If PMC IDs are in 'id' column
uv run python -m pmcgrab --input-csv data.csv --pmcid-column id
```

## Output Files

The CLI creates several output files:

### Individual Article Files

```
output_directory/
├── PMC7181753.json      # Individual article data
├── PMC3539614.json
└── PMC5454911.json
```

### Summary Files

```
output_directory/
├── processing_summary.json    # Processing statistics
├── failed_pmcids.txt         # Failed PMC IDs
└── processing.log            # Detailed log (if --log-file used)
```

## Environment Variables

Set default values using environment variables:

```bash
export PMCGRAB_EMAIL="your-email@example.com"
export PMCGRAB_OUTPUT_DIR="./default_output"
export PMCGRAB_WORKERS=8
export PMCGRAB_BATCH_SIZE=20
export PMCGRAB_TIMEOUT=60
export PMCGRAB_MAX_RETRIES=3

# Now you can run with defaults
uv run python -m pmcgrab PMC7181753
```

## Advanced Usage

### Filtering and Validation

```bash
# Validate XML structure
uv run python -m pmcgrab --validate PMC7181753

# Skip validation for speed
uv run python -m pmcgrab --no-validate PMC7181753

# Download and cache XML files
uv run python -m pmcgrab --download --cache-dir ./xml_cache PMC7181753
```

### Resume Processing

```bash
# Resume from previous failed run
uv run python -m pmcgrab --resume --input-dir ./previous_output PMC7181753 PMC3539614

# Or resume from failed IDs file
uv run python -m pmcgrab --input-file ./previous_output/failed_pmcids.txt
```

### Logging Options

```bash
# Enable detailed logging
uv run python -m pmcgrab --verbose --log-file processing.log PMC7181753

# Different log levels
uv run python -m pmcgrab --log-level DEBUG PMC7181753
uv run python -m pmcgrab --log-level WARNING PMC7181753
```

## Batch Processing Examples

### Small Scale (< 100 articles)

```bash
uv run python -m pmcgrab \
    --input-file small_list.txt \
    --workers 4 \
    --batch-size 10 \
    --email your-email@example.com
```

### Medium Scale (100-1000 articles)

```bash
uv run python -m pmcgrab \
    --input-file medium_list.txt \
    --workers 8 \
    --batch-size 25 \
    --max-retries 3 \
    --timeout 45 \
    --verbose \
    --email your-email@example.com
```

### Large Scale (1000+ articles)

```bash
uv run python -m pmcgrab \
    --input-file large_list.txt \
    --workers 12 \
    --batch-size 50 \
    --max-retries 5 \
    --timeout 90 \
    --cache-dir ./xml_cache \
    --log-file large_processing.log \
    --email your-email@example.com
```

## Error Handling

### Common Exit Codes

- `0`: Success
- `1`: General error
- `2`: Invalid arguments
- `3`: Network error
- `4`: File not found
- `5`: Permission error

### Handling Failures

```bash
# Run with error handling
uv run python -m pmcgrab PMC7181753 PMC3539614
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "Processing completed successfully"
elif [ $EXIT_CODE -eq 3 ]; then
    echo "Network error - check connection and retry"
else
    echo "Processing failed with exit code $EXIT_CODE"
fi
```

### Retry Failed Articles

```bash
# Initial processing
uv run python -m pmcgrab --input-file all_ids.txt --output-dir ./results

# Retry failed articles
if [ -f ./results/failed_pmcids.txt ]; then
    echo "Retrying failed articles..."
    uv run python -m pmcgrab \
        --input-file ./results/failed_pmcids.txt \
        --output-dir ./results \
        --max-retries 5 \
        --timeout 120
fi
```

## Performance Tuning

### Network Optimization

```bash
# For slow networks
uv run python -m pmcgrab \
    --workers 2 \
    --batch-size 5 \
    --timeout 120 \
    --max-retries 10 \
    PMC7181753

# For fast networks
uv run python -m pmcgrab \
    --workers 16 \
    --batch-size 50 \
    --timeout 30 \
    --max-retries 2 \
    PMC7181753
```

### Memory Optimization

```bash
# For memory-constrained systems
uv run python -m pmcgrab \
    --workers 2 \
    --batch-size 5 \
    --no-cache \
    PMC7181753

# For high-memory systems
uv run python -m pmcgrab \
    --workers 16 \
    --batch-size 100 \
    --cache-dir ./large_cache \
    PMC7181753
```

## Integration with Shell Scripts

### Bash Script Example

```bash
#!/bin/bash

# PMCGrab batch processing script
EMAIL="your-email@example.com"
INPUT_FILE="pmc_ids.txt"
OUTPUT_DIR="./batch_$(date +%Y%m%d_%H%M%S)"
LOG_FILE="processing_$(date +%Y%m%d_%H%M%S).log"

echo "Starting PMCGrab batch processing..."
echo "Input file: $INPUT_FILE"
echo "Output directory: $OUTPUT_DIR"
echo "Log file: $LOG_FILE"

uv run python -m pmcgrab \
    --input-file "$INPUT_FILE" \
    --output-dir "$OUTPUT_DIR" \
    --email "$EMAIL" \
    --workers 8 \
    --batch-size 20 \
    --max-retries 3 \
    --verbose \
    --log-file "$LOG_FILE"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "Processing completed successfully!"
    echo "Results in: $OUTPUT_DIR"
    echo "Log file: $LOG_FILE"
else
    echo "Processing failed with exit code: $EXIT_CODE"
    echo "Check log file: $LOG_FILE"
    exit $EXIT_CODE
fi
```

### PowerShell Script Example

```powershell
# PMCGrab batch processing script for Windows
$EMAIL = "your-email@example.com"
$INPUT_FILE = "pmc_ids.txt"
$OUTPUT_DIR = "./batch_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
$LOG_FILE = "processing_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

Write-Host "Starting PMCGrab batch processing..."
Write-Host "Input file: $INPUT_FILE"
Write-Host "Output directory: $OUTPUT_DIR"
Write-Host "Log file: $LOG_FILE"

uv run python -m pmcgrab `
    --input-file $INPUT_FILE `
    --output-dir $OUTPUT_DIR `
    --email $EMAIL `
    --workers 8 `
    --batch-size 20 `
    --max-retries 3 `
    --verbose `
    --log-file $LOG_FILE

if ($LASTEXITCODE -eq 0) {
    Write-Host "Processing completed successfully!" -ForegroundColor Green
    Write-Host "Results in: $OUTPUT_DIR"
    Write-Host "Log file: $LOG_FILE"
} else {
    Write-Host "Processing failed with exit code: $LASTEXITCODE" -ForegroundColor Red
    Write-Host "Check log file: $LOG_FILE"
    exit $LASTEXITCODE
}
```

## Help and Documentation

### Get Help

```bash
# Show help message
uv run python -m pmcgrab --help

# Show version
uv run python -m pmcgrab --version

# Show configuration
uv run python -m pmcgrab --show-config
```

### All Available Options

```
Usage: uv run python -m pmcgrab [OPTIONS] [PMCIDS...]

Options:
  --email TEXT                    Contact email for NCBI API (required)
  --output-dir TEXT              Output directory (default: ./pmc_output)
  --input-file TEXT              File containing PMC IDs (one per line)
  --input-csv TEXT               CSV file containing PMC IDs
  --pmcid-column TEXT            Column name for PMC IDs in CSV (default: pmcid)
  --workers INTEGER              Number of parallel workers (default: 4)
  --batch-size INTEGER           Batch size for processing (default: 10)
  --max-retries INTEGER          Maximum retry attempts (default: 3)
  --timeout INTEGER              Request timeout in seconds (default: 30)
  --validate / --no-validate     Validate XML structure (default: True)
  --download / --no-download     Download and cache XML files (default: False)
  --cache-dir TEXT               Directory for caching XML files
  --verbose / --quiet            Enable/disable verbose output (default: False)
  --log-file TEXT                Log file path
  --log-level TEXT               Log level (DEBUG, INFO, WARNING, ERROR)
  --resume                       Resume from previous failed run
  --input-dir TEXT               Input directory for resume mode
  --version                      Show version and exit
  --help                         Show this message and exit
```

This comprehensive CLI guide should help you use PMCGrab effectively from the command line for any scale of processing.
