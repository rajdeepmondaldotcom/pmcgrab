# CLI Examples

Practical command-line examples for common PMCGrab usage scenarios.

## Basic Usage

### Single Article Processing

```bash
# Basic usage - process one article
python -m pmcgrab PMC7181753

# With email specification (recommended)
python -m pmcgrab --email researcher@university.edu PMC7181753

# Save to custom directory
python -m pmcgrab --output-dir ./papers --email researcher@university.edu PMC7181753
```

### Multiple Articles

```bash
# Process several articles at once
python -m pmcgrab PMC7181753 PMC3539614 PMC5454911

# With parallel processing
python -m pmcgrab --workers 4 PMC7181753 PMC3539614 PMC5454911
```

## File Input

### From Text File

Create `pmcids.txt`:

```
7181753
3539614
5454911
7979870
```

Process the list:

```bash
python -m pmcgrab --input-file pmcids.txt --email researcher@university.edu
```

## Advanced Options

### Batch Processing with Configuration

```bash
# Process with custom settings
python -m pmcgrab \
    --input-file pmcids.txt \
    --output-dir ./output \
    --email researcher@university.edu \
    --workers 4 \
    --batch-size 10 \
    --max-retries 2 \
    --verbose
```

### Common Parameters

| Parameter       | Description                     | Example                    |
| --------------- | ------------------------------- | -------------------------- |
| `--email`       | Your email for NCBI requests    | `--email user@example.com` |
| `--output-dir`  | Output directory for JSON files | `--output-dir ./papers`    |
| `--workers`     | Number of parallel workers      | `--workers 4`              |
| `--batch-size`  | Articles per batch              | `--batch-size 10`          |
| `--max-retries` | Retry failed requests           | `--max-retries 2`          |
| `--verbose`     | Detailed output                 | `--verbose`                |
| `--input-file`  | Read PMC IDs from file          | `--input-file list.txt`    |

## Output

PMCGrab saves each article as a JSON file:

```
output/
├── PMC7181753.json
├── PMC3539614.json
└── PMC5454911.json
```

Each JSON file contains structured article data including title, abstract, body sections, authors, and metadata.
