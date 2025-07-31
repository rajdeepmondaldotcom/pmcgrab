# CLI Examples

Practical command-line examples for common PMCGrab usage scenarios.

## Quick Start Examples

### Single Article Processing

```bash
# Basic usage - process one article
python -m pmcgrab PMC7181753

# With email specification (recommended)
python -m pmcgrab --email researcher@university.edu PMC7181753

# Save to custom directory
python -m pmcgrab --output-dir ./covid_papers --email researcher@university.edu PMC7181753
```

### Multiple Articles

```bash
# Process several articles at once
python -m pmcgrab PMC7181753 PMC3539614 PMC5454911

# With parallel processing
python -m pmcgrab --workers 4 PMC7181753 PMC3539614 PMC5454911 PMC8378853
```

## File Input Examples

### From Text File

Create `paper_list.txt`:

```
7181753
3539614
5454911
8378853
7462677
```

Process the list:

```bash
python -m pmcgrab --input-file paper_list.txt --email researcher@university.edu
```

### From CSV File

Create `research_papers.csv`:

```csv
pmcid,title,category
7181753,COVID-19 Research,virology
3539614,ML in Biology,bioinformatics
5454911,Clinical Trial,medicine
```

Process from CSV:

```bash
python -m pmcgrab --input-csv research_papers.csv --pmcid-column pmcid
```

## Research Workflow Examples

### Literature Review Workflow

```bash
#!/bin/bash
# Literature review processing script

TOPIC="machine_learning_biology"
EMAIL="researcher@university.edu"
OUTPUT_DIR="./literature_review_${TOPIC}"

echo "Processing literature for: $TOPIC"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Process papers with robust settings
python -m pmcgrab \
    --input-file "${TOPIC}_pmcids.txt" \
    --output-dir "$OUTPUT_DIR" \
    --email "$EMAIL" \
    --workers 6 \
    --batch-size 15 \
    --max-retries 3 \
    --timeout 45 \
    --verbose \
    --log-file "${OUTPUT_DIR}/processing.log"

echo "Processing complete. Results in: $OUTPUT_DIR"
```

### Systematic Review Pipeline

```bash
#!/bin/bash
# Systematic review processing pipeline

# Configuration
EMAIL="systematic.reviewer@institution.edu"
BASE_DIR="./systematic_review_$(date +%Y%m%d)"
INPUT_FILE="systematic_review_pmcids.txt"

# Create directory structure
mkdir -p "$BASE_DIR"/{raw_data,processed_data,logs,reports}

echo "Starting systematic review processing..."
echo "Date: $(date)"
echo "Input file: $INPUT_FILE"
echo "Output directory: $BASE_DIR"

# Process articles with high reliability settings
python -m pmcgrab \
    --input-file "$INPUT_FILE" \
    --output-dir "$BASE_DIR/raw_data" \
    --email "$EMAIL" \
    --workers 8 \
    --batch-size 20 \
    --max-retries 5 \
    --timeout 90 \
    --download \
    --cache-dir "$BASE_DIR/xml_cache" \
    --verbose \
    --log-file "$BASE_DIR/logs/processing.log"

# Generate summary report
echo "Processing Summary" > "$BASE_DIR/reports/summary.txt"
echo "==================" >> "$BASE_DIR/reports/summary.txt"
echo "Date: $(date)" >> "$BASE_DIR/reports/summary.txt"
echo "Total files processed: $(ls $BASE_DIR/raw_data/PMC*.json | wc -l)" >> "$BASE_DIR/reports/summary.txt"

if [ -f "$BASE_DIR/raw_data/failed_pmcids.txt" ]; then
    echo "Failed articles: $(wc -l < $BASE_DIR/raw_data/failed_pmcids.txt)" >> "$BASE_DIR/reports/summary.txt"
else
    echo "Failed articles: 0" >> "$BASE_DIR/reports/summary.txt"
fi

echo "Systematic review processing complete!"
```

## Performance Optimization Examples

### High-Throughput Processing

```bash
# For processing thousands of articles
python -m pmcgrab \
    --input-file large_dataset.txt \
    --output-dir ./high_throughput_output \
    --email researcher@university.edu \
    --workers 16 \
    --batch-size 50 \
    --max-retries 3 \
    --timeout 60 \
    --no-validate \
    --log-level WARNING
```

### Memory-Efficient Processing

```bash
# For memory-constrained environments
python -m pmcgrab \
    --input-file paper_list.txt \
    --output-dir ./memory_efficient \
    --email researcher@university.edu \
    --workers 2 \
    --batch-size 5 \
    --max-retries 2 \
    --timeout 30
```

### Network-Optimized Processing

```bash
# For slow or unreliable networks
python -m pmcgrab \
    --input-file paper_list.txt \
    --output-dir ./network_robust \
    --email researcher@university.edu \
    --workers 3 \
    --batch-size 8 \
    --max-retries 10 \
    --timeout 120 \
    --verbose
```

## Subject-Specific Examples

### COVID-19 Research

```bash
#!/bin/bash
# Process COVID-19 related papers

echo "Processing COVID-19 research papers..."

python -m pmcgrab \
    --input-file covid19_papers.txt \
    --output-dir ./covid19_research \
    --email covid.researcher@institution.edu \
    --workers 8 \
    --batch-size 25 \
    --max-retries 3 \
    --download \
    --cache-dir ./covid19_xml_cache \
    --verbose

# Create research summary
echo "COVID-19 Research Dataset" > ./covid19_research/DATASET_INFO.txt
echo "=========================" >> ./covid19_research/DATASET_INFO.txt
echo "Processing date: $(date)" >> ./covid19_research/DATASET_INFO.txt
echo "Number of papers: $(ls ./covid19_research/PMC*.json | wc -l)" >> ./covid19_research/DATASET_INFO.txt
```

### Cancer Research

```bash
#!/bin/bash
# Process cancer research papers by category

CATEGORIES=("breast_cancer" "lung_cancer" "prostate_cancer" "colorectal_cancer")
EMAIL="cancer.researcher@oncology.edu"
BASE_OUTPUT="./cancer_research"

for category in "${CATEGORIES[@]}"; do
    echo "Processing $category papers..."

    python -m pmcgrab \
        --input-file "${category}_pmcids.txt" \
        --output-dir "$BASE_OUTPUT/$category" \
        --email "$EMAIL" \
        --workers 6 \
        --batch-size 20 \
        --max-retries 3 \
        --verbose \
        --log-file "$BASE_OUTPUT/$category/processing.log"

    echo "Completed $category: $(ls $BASE_OUTPUT/$category/PMC*.json | wc -l) papers"
done

echo "All cancer research categories processed!"
```

### Bioinformatics Papers

```bash
#!/bin/bash
# Process bioinformatics and computational biology papers

python -m pmcgrab \
    --input-file bioinformatics_pmcids.txt \
    --output-dir ./bioinformatics_papers \
    --email bioinformatics@computational.bio \
    --workers 10 \
    --batch-size 30 \
    --max-retries 3 \
    --timeout 45 \
    --download \
    --validate \
    --verbose \
    --log-file ./bioinformatics_papers/processing.log

# Post-processing: count papers by journal
echo "Journal Distribution:" > ./bioinformatics_papers/journal_stats.txt
grep -h '"Journal"' ./bioinformatics_papers/PMC*.json | \
    sort | uniq -c | sort -rn >> ./bioinformatics_papers/journal_stats.txt
```

## Error Handling and Recovery

### Robust Processing with Retry

```bash
#!/bin/bash
# Robust processing with automatic retry of failed articles

EMAIL="researcher@university.edu"
INPUT_FILE="paper_list.txt"
OUTPUT_DIR="./robust_processing"
MAX_ATTEMPTS=3

for attempt in $(seq 1 $MAX_ATTEMPTS); do
    echo "Processing attempt $attempt..."

    python -m pmcgrab \
        --input-file "$INPUT_FILE" \
        --output-dir "$OUTPUT_DIR" \
        --email "$EMAIL" \
        --workers 6 \
        --batch-size 15 \
        --max-retries 5 \
        --timeout 60 \
        --verbose

    # Check if any articles failed
    if [ ! -f "$OUTPUT_DIR/failed_pmcids.txt" ]; then
        echo "All articles processed successfully!"
        break
    fi

    # Use failed list as input for next attempt
    FAILED_COUNT=$(wc -l < "$OUTPUT_DIR/failed_pmcids.txt")
    echo "Attempt $attempt: $FAILED_COUNT articles failed, retrying..."

    if [ $attempt -lt $MAX_ATTEMPTS ]; then
        cp "$OUTPUT_DIR/failed_pmcids.txt" "$INPUT_FILE"
    fi
done

echo "Processing complete after $attempt attempts"
```

### Resume Interrupted Processing

```bash
#!/bin/bash
# Resume processing from a previous interrupted run

ORIGINAL_LIST="all_papers.txt"
OUTPUT_DIR="./resume_processing"
EMAIL="researcher@university.edu"

# Find successfully processed papers
find "$OUTPUT_DIR" -name "PMC*.json" -exec basename {} .json \; | \
    sed 's/PMC//' > processed_papers.txt

# Create list of remaining papers
comm -23 <(sort "$ORIGINAL_LIST") <(sort processed_papers.txt) > remaining_papers.txt

REMAINING_COUNT=$(wc -l < remaining_papers.txt)
echo "Found $REMAINING_COUNT papers remaining to process"

if [ $REMAINING_COUNT -gt 0 ]; then
    python -m pmcgrab \
        --input-file remaining_papers.txt \
        --output-dir "$OUTPUT_DIR" \
        --email "$EMAIL" \
        --workers 8 \
        --batch-size 20 \
        --max-retries 3 \
        --verbose
else
    echo "All papers already processed!"
fi

# Cleanup temporary files
rm processed_papers.txt remaining_papers.txt
```

## Quality Control Examples

### Validation and Quality Checks

```bash
#!/bin/bash
# Process with strict validation and quality checks

python -m pmcgrab \
    --input-file curated_papers.txt \
    --output-dir ./quality_controlled \
    --email quality.control@research.edu \
    --workers 4 \
    --batch-size 10 \
    --validate \
    --download \
    --max-retries 5 \
    --timeout 90 \
    --verbose \
    --log-file ./quality_controlled/detailed.log

# Post-processing quality checks
echo "Quality Control Report" > ./quality_controlled/quality_report.txt
echo "=====================" >> ./quality_controlled/quality_report.txt

# Count files
TOTAL_FILES=$(ls ./quality_controlled/PMC*.json | wc -l)
echo "Total processed files: $TOTAL_FILES" >> ./quality_controlled/quality_report.txt

# Check for empty or malformed files
EMPTY_FILES=$(find ./quality_controlled -name "PMC*.json" -size 0 | wc -l)
echo "Empty files: $EMPTY_FILES" >> ./quality_controlled/quality_report.txt

# Validate JSON format
echo "JSON validation:" >> ./quality_controlled/quality_report.txt
for file in ./quality_controlled/PMC*.json; do
    if ! python -m json.tool "$file" > /dev/null 2>&1; then
        echo "  Invalid JSON: $(basename $file)" >> ./quality_controlled/quality_report.txt
    fi
done

echo "Quality control complete!"
```

## Integration Examples

### Database Integration

```bash
#!/bin/bash
# Process papers and load into database

DB_NAME="research_papers"
DB_USER="researcher"
OUTPUT_DIR="./db_integration"

# Process papers
python -m pmcgrab \
    --input-file papers_for_db.txt \
    --output-dir "$OUTPUT_DIR" \
    --email db.loader@research.edu \
    --workers 8 \
    --batch-size 25 \
    --max-retries 3

# Load into PostgreSQL database
for json_file in "$OUTPUT_DIR"/PMC*.json; do
    pmcid=$(basename "$json_file" .json | sed 's/PMC//')

    echo "Loading PMC$pmcid into database..."

    # Extract data and insert (example using jq and psql)
    title=$(jq -r '.Title' "$json_file")
    journal=$(jq -r '.Journal' "$json_file")
    pub_date=$(jq -r '.PubDate' "$json_file")

    psql -d "$DB_NAME" -U "$DB_USER" -c \
        "INSERT INTO articles (pmcid, title, journal, pub_date, data) VALUES ('PMC$pmcid', '$title', '$journal', '$pub_date', '$(cat $json_file | sed "s/'/''/g")');"
done

echo "Database loading complete!"
```

### Export to Different Formats

```bash
#!/bin/bash
# Process papers and export to multiple formats

OUTPUT_DIR="./multi_format_export"
EMAIL="format.exporter@research.edu"

# Process papers
python -m pmcgrab \
    --input-file export_papers.txt \
    --output-dir "$OUTPUT_DIR/json" \
    --email "$EMAIL" \
    --workers 6 \
    --batch-size 20

# Convert to CSV format
echo "PMCID,Title,Journal,PubDate,AuthorCount" > "$OUTPUT_DIR/papers.csv"
for json_file in "$OUTPUT_DIR"/json/PMC*.json; do
    pmcid=$(jq -r '.PMCID' "$json_file")
    title=$(jq -r '.Title' "$json_file")
    journal=$(jq -r '.Journal' "$json_file")
    pub_date=$(jq -r '.PubDate' "$json_file")
    author_count=$(jq '.Authors | length' "$json_file")

    echo "\"$pmcid\",\"$title\",\"$journal\",\"$pub_date\",$author_count" >> "$OUTPUT_DIR/papers.csv"
done

echo "Multi-format export complete!"
```

## Monitoring and Logging

### Advanced Logging Setup

```bash
#!/bin/bash
# Process with comprehensive logging

LOG_DIR="./logs/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

# Set up log rotation
exec 1> >(tee -a "$LOG_DIR/stdout.log")
exec 2> >(tee -a "$LOG_DIR/stderr.log")

echo "Starting PMCGrab processing with advanced logging..."
echo "Log directory: $LOG_DIR"

python -m pmcgrab \
    --input-file comprehensive_list.txt \
    --output-dir ./comprehensive_output \
    --email comprehensive@research.edu \
    --workers 8 \
    --batch-size 25 \
    --max-retries 3 \
    --verbose \
    --log-file "$LOG_DIR/pmcgrab.log" \
    --log-level DEBUG

echo "Processing complete. All logs saved to: $LOG_DIR"
```

These examples provide practical templates for common PMCGrab usage scenarios. Modify the parameters and paths to suit your specific research needs.
