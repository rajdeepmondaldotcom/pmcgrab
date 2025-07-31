# Output Format

PMCGrab produces structured JSON output that's optimized for AI and machine learning applications.

## JSON Structure Overview

Each processed PMC article is saved as a JSON file with the following structure:

```json
{
  "PMCID": "PMC7181753",
  "Title": "Article Title",
  "Authors": [...],
  "Abstract": {...},
  "Body": {...},
  "Citations": [...],
  "Tables": [...],
  "Figures": [...],
  "Journal": "Journal Name",
  "PubDate": "2024-01-15",
  "DOI": "10.1000/example",
  "Keywords": [...],
  "MeshTerms": [...],
  "Funding": [...],
  "Ethics": {...}
}
```

## Detailed Field Descriptions

### Basic Metadata

```json
{
  "PMCID": "PMC7181753", // PubMed Central ID
  "Title": "Article Title", // Full article title
  "DOI": "10.1000/example", // Digital Object Identifier
  "Journal": "Nature", // Journal name
  "PubDate": "2024-01-15", // Publication date (ISO format)
  "Volume": "595", // Journal volume
  "Issue": "7866", // Journal issue
  "Pages": "123-130" // Page numbers
}
```

### Authors Array

```json
{
  "Authors": [
    {
      "FirstName": "John",
      "LastName": "Doe",
      "Initials": "J.D.",
      "Affiliation": "University of Example, Department of Biology",
      "ORCID": "0000-0000-0000-0000",
      "Email": "john.doe@example.com"
    },
    {
      "FirstName": "Jane",
      "LastName": "Smith",
      "Initials": "J.S.",
      "Affiliation": "Research Institute Example"
    }
  ]
}
```

### Abstract Structure

The abstract is broken down by section:

```json
{
  "Abstract": {
    "Background": "Background text...",
    "Objective": "Objective text...",
    "Methods": "Methods text...",
    "Results": "Results text...",
    "Conclusions": "Conclusions text..."
  }
}
```

Common abstract sections include:

- Background
- Objective/Purpose
- Methods/Methodology
- Results/Findings
- Conclusions/Discussion
- Keywords

### Body Content

The main article content is organized by section:

```json
{
  "Body": {
    "Introduction": "Introduction text with proper paragraph breaks...",
    "Methods": "Detailed methodology...",
    "Results": "Results and findings...",
    "Discussion": "Discussion of results...",
    "Conclusion": "Final conclusions...",
    "Acknowledgments": "Acknowledgments text...",
    "References": "Reference list..."
  }
}
```

### Citations Array

```json
{
  "Citations": [
    {
      "id": "ref1",
      "Authors": "Smith J, Doe J",
      "Title": "Referenced Article Title",
      "Journal": "Science",
      "Year": "2023",
      "Volume": "380",
      "Pages": "123-125",
      "DOI": "10.1126/science.example",
      "PMID": "12345678"
    }
  ]
}
```

### Tables Array

Tables are converted to structured data:

```json
{
  "Tables": [
    {
      "Label": "Table 1",
      "Caption": "Demographic characteristics of study participants",
      "Data": [
        ["Characteristic", "Group A (n=50)", "Group B (n=48)", "P-value"],
        ["Age (years)", "65.2 ± 12.1", "67.8 ± 10.9", "0.23"],
        ["Gender (M/F)", "28/22", "26/22", "0.85"]
      ],
      "Footer": "Data presented as mean ± SD or n. P-values from t-test."
    }
  ]
}
```

### Figures Array

```json
{
  "Figures": [
    {
      "Label": "Figure 1",
      "Caption": "Experimental setup and workflow",
      "Description": "Detailed figure description...",
      "URL": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7181753/bin/figure1.jpg"
    }
  ]
}
```

### Keywords and Mesh Terms

```json
{
  "Keywords": [
    "machine learning",
    "bioinformatics",
    "genomics",
    "artificial intelligence"
  ],
  "MeshTerms": [
    {
      "Term": "Machine Learning",
      "MajorTopic": true,
      "Qualifiers": ["methods", "statistics & numerical data"]
    }
  ]
}
```

### Funding Information

```json
{
  "Funding": [
    {
      "Agency": "National Institutes of Health",
      "GrantNumber": "R01GM123456",
      "Country": "United States"
    },
    {
      "Agency": "European Research Council",
      "GrantNumber": "ERC-2020-STG-123456",
      "Country": "European Union"
    }
  ]
}
```

### Ethics and Compliance

```json
{
  "Ethics": {
    "IRB_Approval": "Study approved by University IRB (Protocol #2023-001)",
    "Ethics_Statement": "All procedures performed in accordance with ethical standards...",
    "Consent": "Written informed consent obtained from all participants",
    "Animal_Welfare": "Animal studies conducted according to institutional guidelines"
  }
}
```

## Special Formatting

### HTML Cleaning

PMCGrab automatically cleans HTML tags and formatting:

**Input (XML):**

```xml
<p>The results show that <italic>p</italic> &lt; 0.05 for <bold>significant</bold> findings.</p>
```

**Output (JSON):**

```json
{
  "text": "The results show that p < 0.05 for significant findings."
}
```

### Reference Cleaning

Citations and cross-references are cleaned:

**Input:**

```
"As shown in previous studies [1,2,3], the method..."
```

**Output:**

```json
{
  "text": "As shown in previous studies, the method...",
  "references": ["ref1", "ref2", "ref3"]
}
```

### Section Normalization

Section headings are normalized to standard names:

| Input Variations                                  | Normalized Output |
| ------------------------------------------------- | ----------------- |
| "INTRODUCTION", "Introduction", "1. Introduction" | "Introduction"    |
| "METHODS", "Materials and Methods", "Methodology" | "Methods"         |
| "RESULTS", "Results and Discussion"               | "Results"         |
| "DISCUSSION", "Discussion and Conclusions"        | "Discussion"      |

## File Organization

### Individual Files

Each article is saved as a separate JSON file:

```
output_directory/
├── PMC7181753.json
├── PMC3539614.json
├── PMC5454911.json
└── ...
```

### Batch Processing Output

Batch processing creates additional files:

```
output_directory/
├── PMC7181753.json
├── PMC3539614.json
├── processing_summary.json    # Processing statistics
├── failed_pmcids.txt         # Failed PMC IDs
└── batch_metadata.json       # Batch processing info
```

### Processing Summary

```json
{
  "batch_id": "batch_20241215_143022",
  "start_time": "2024-12-15T14:30:22Z",
  "end_time": "2024-12-15T14:45:18Z",
  "total_requested": 100,
  "successfully_processed": 95,
  "failed": 5,
  "success_rate": 0.95,
  "processing_time_seconds": 896,
  "articles_per_second": 0.106,
  "settings": {
    "batch_size": 20,
    "max_workers": 8,
    "timeout": 60,
    "max_retries": 3
  },
  "failed_pmcids": ["1234567", "2345678", "3456789", "4567890", "5678901"]
}
```

## Data Types and Formats

### Date Formats

All dates use ISO 8601 format:

```json
{
  "PubDate": "2024-01-15", // Publication date
  "ReceivedDate": "2023-10-20", // Manuscript received
  "AcceptedDate": "2023-12-08", // Manuscript accepted
  "EpubDate": "2024-01-10" // Electronic publication
}
```

### Numeric Data

Numbers are preserved as appropriate types:

```json
{
  "Volume": 595, // Integer
  "Impact_Factor": 42.778, // Float
  "Page_Count": 8, // Integer
  "Word_Count": 4750 // Integer
}
```

### Text Encoding

All text is UTF-8 encoded and handles special characters:

```json
{
  "Title": "α-Synuclein aggregation in β-cells: implications for diabetes",
  "Abstract": "...temperature was 37°C ± 0.5°C..."
}
```

## Usage Examples

### Loading JSON Data

```python
import json

# Load single article
with open('PMC7181753.json', 'r', encoding='utf-8') as f:
    article = json.load(f)

print(f"Title: {article['Title']}")
print(f"Authors: {len(article['Authors'])}")
```

### Processing Multiple Articles

```python
import json
import glob

# Load all articles in directory
articles = []
for filename in glob.glob('./output/*.json'):
    if filename.endswith('.json') and 'PMC' in filename:
        with open(filename, 'r', encoding='utf-8') as f:
            articles.append(json.load(f))

print(f"Loaded {len(articles)} articles")
```

### Extracting Specific Data

```python
# Extract abstracts for analysis
abstracts = []
for article in articles:
    abstract_text = " ".join(article['Abstract'].values())
    abstracts.append({
        'pmcid': article['PMCID'],
        'title': article['Title'],
        'abstract': abstract_text
    })
```

## Integration with Other Tools

### Pandas DataFrame

```python
import pandas as pd
import json

# Convert to DataFrame
records = []
for filename in glob.glob('./output/PMC*.json'):
    with open(filename, 'r') as f:
        article = json.load(f)
        records.append({
            'pmcid': article['PMCID'],
            'title': article['Title'],
            'journal': article['Journal'],
            'pub_date': article['PubDate'],
            'num_authors': len(article['Authors']),
            'num_citations': len(article['Citations']),
            'word_count': len(' '.join(article['Body'].values()).split())
        })

df = pd.DataFrame(records)
print(df.head())
```

### Database Storage

```sql
-- Example table schema for PostgreSQL
CREATE TABLE articles (
    pmcid VARCHAR(20) PRIMARY KEY,
    title TEXT NOT NULL,
    journal VARCHAR(255),
    pub_date DATE,
    authors JSONB,
    abstract JSONB,
    body JSONB,
    citations JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

This structured output format makes PMCGrab data immediately usable for downstream AI/ML applications, research analysis, and database storage.
