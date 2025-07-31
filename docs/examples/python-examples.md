# Python Examples

Real-world examples showing how to use PMCGrab effectively.

## Basic Examples

### Single Article Retrieval

```python
from pmcgrab import Paper

# Retrieve a paper about COVID-19 research
paper = Paper.from_pmc("7181753", email="researcher@university.edu")

print(f"Title: {paper.title}")
print(f"Journal: {paper.journal}")
print(f"Authors: {len(paper.authors)}")

# Display abstract
for section, content in paper.abstract.items():
    print(f"\n{section}:")
    print(content[:200] + "..." if len(content) > 200 else content)
```

### Exploring Article Sections

```python
from pmcgrab import Paper

paper = Paper.from_pmc("3539614", email="your-email@example.com")

# Print all available sections
print("Available sections:")
for section in paper.body.keys():
    print(f"- {section}")

# Focus on methodology
if 'Methods' in paper.body:
    methods = paper.body['Methods']
    print(f"\nMethods section ({len(methods)} characters):")
    print(methods[:500] + "..." if len(methods) > 500 else methods)
```

## Batch Processing Examples

### Processing a Literature Review Dataset

```python
from pmcgrab import process_pmc_ids_in_batches
import json
import os

# PMC IDs for a systematic review
covid_papers = [
    "7181753", "8378853", "7462677", "7890123", "7456789",
    "8234567", "7123456", "8345678", "7567890", "8456789"
]

# Process in batches
output_dir = "./covid_literature_review"
process_pmc_ids_in_batches(
    pmc_ids=covid_papers,
    output_dir=output_dir,
    batch_size=5,
    max_workers=3,
    email="researcher@university.edu"
)

# Load and analyze results
results = []
for filename in os.listdir(output_dir):
    if filename.endswith('.json') and filename.startswith('PMC'):
        with open(os.path.join(output_dir, filename)) as f:
            paper_data = json.load(f)
            results.append(paper_data)

print(f"Successfully processed {len(results)} papers")
```

### Error-Tolerant Batch Processing

```python
from pmcgrab import Paper
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_paper_list(pmc_ids, email):
    """Process a list of PMC IDs with error handling."""
    successful = []
    failed = []

    for pmcid in pmc_ids:
        try:
            paper = Paper.from_pmc(pmcid, email=email)
            successful.append({
                'pmcid': pmcid,
                'title': paper.title,
                'authors': len(paper.authors),
                'sections': list(paper.body.keys())
            })
            logger.info(f"✓ Processed PMC{pmcid}")

        except Exception as e:
            failed.append({'pmcid': pmcid, 'error': str(e)})
            logger.error(f"✗ Failed PMC{pmcid}: {e}")

    return successful, failed

# Process papers
paper_ids = ["7181753", "invalid_id", "3539614", "another_invalid"]
successful, failed = process_paper_list(paper_ids, "your@email.com")

print(f"Successful: {len(successful)}, Failed: {len(failed)}")
```

## Data Analysis Examples

### Extracting Author Networks

```python
from pmcgrab import Paper
import pandas as pd
from collections import defaultdict

def build_author_network(pmc_ids, email):
    """Build co-authorship network from PMC papers."""
    coauthorships = defaultdict(int)
    all_authors = set()

    for pmcid in pmc_ids:
        try:
            paper = Paper.from_pmc(pmcid, email=email)
            authors = []

            for author in paper.authors:
                name = f"{author.get('FirstName', '')} {author.get('LastName', '')}"
                name = name.strip()
                if name:
                    authors.append(name)
                    all_authors.add(name)

            # Record co-authorships
            for i, author1 in enumerate(authors):
                for author2 in authors[i+1:]:
                    pair = tuple(sorted([author1, author2]))
                    coauthorships[pair] += 1

        except Exception as e:
            print(f"Error processing {pmcid}: {e}")

    return dict(coauthorships), all_authors

# Build network
paper_ids = ["7181753", "3539614", "5454911"]
coauth_network, authors = build_author_network(paper_ids, "your@email.com")

print(f"Found {len(authors)} unique authors")
print(f"Found {len(coauth_network)} co-authorship pairs")
```

### Keyword and Topic Analysis

```python
from pmcgrab import Paper
from collections import Counter
import re

def extract_keywords_from_papers(pmc_ids, email):
    """Extract and count keywords from paper abstracts."""
    all_text = []
    paper_data = []

    for pmcid in pmc_ids:
        try:
            paper = Paper.from_pmc(pmcid, email=email)

            # Combine abstract sections
            abstract_text = " ".join(paper.abstract.values())
            all_text.append(abstract_text.lower())

            paper_data.append({
                'pmcid': pmcid,
                'title': paper.title,
                'abstract_length': len(abstract_text),
                'sections': list(paper.body.keys())
            })

        except Exception as e:
            print(f"Error with {pmcid}: {e}")

    # Simple keyword extraction (you might want to use NLTK/spaCy)
    combined_text = " ".join(all_text)
    words = re.findall(r'\b[a-z]+\b', combined_text)

    # Filter common words and short words
    stopwords = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                'of', 'with', 'by', 'is', 'are', 'was', 'were', 'been', 'be'}
    keywords = [w for w in words if len(w) > 3 and w not in stopwords]

    return Counter(keywords), paper_data

# Analyze keywords
paper_ids = ["7181753", "3539614", "5454911"]
keyword_counts, papers = extract_keywords_from_papers(paper_ids, "your@email.com")

print("Top 10 keywords:")
for keyword, count in keyword_counts.most_common(10):
    print(f"- {keyword}: {count}")
```

## Content Processing Examples

### Extracting Methodology Sections

```python
from pmcgrab import Paper
from pmcgrab.common.html_cleaning import clean_html_tags

def extract_methodologies(pmc_ids, email):
    """Extract and clean methodology sections."""
    methodologies = []

    for pmcid in pmc_ids:
        try:
            paper = Paper.from_pmc(pmcid, email=email)

            # Look for methods in various section names
            methods_text = None
            for section_name in ['Methods', 'Materials and Methods',
                               'Methodology', 'Experimental Procedures']:
                if section_name in paper.body:
                    methods_text = paper.body[section_name]
                    break

            if methods_text:
                # Clean HTML and format
                clean_methods = clean_html_tags(methods_text)

                methodologies.append({
                    'pmcid': pmcid,
                    'title': paper.title,
                    'methods': clean_methods,
                    'methods_length': len(clean_methods)
                })

        except Exception as e:
            print(f"Error with {pmcid}: {e}")

    return methodologies

# Extract methodologies
paper_ids = ["7181753", "3539614", "5454911"]
methods_data = extract_methodologies(paper_ids, "your@email.com")

for paper in methods_data:
    print(f"\n{paper['title']} (PMC{paper['pmcid']}):")
    print(f"Methods length: {paper['methods_length']} characters")
    print(paper['methods'][:200] + "..." if len(paper['methods']) > 200 else paper['methods'])
```

### Table Data Extraction

```python
from pmcgrab import Paper
import pandas as pd
import os

def extract_all_tables(pmc_ids, email, output_dir="tables"):
    """Extract all tables from papers and save as CSV files."""
    os.makedirs(output_dir, exist_ok=True)
    table_info = []

    for pmcid in pmc_ids:
        try:
            paper = Paper.from_pmc(pmcid, email=email)

            for i, table in enumerate(paper.tables):
                # Save table as CSV
                filename = f"PMC{pmcid}_table_{i+1}.csv"
                filepath = os.path.join(output_dir, filename)
                table.to_csv(filepath, index=False)

                table_info.append({
                    'pmcid': pmcid,
                    'paper_title': paper.title,
                    'table_number': i + 1,
                    'filename': filename,
                    'rows': len(table),
                    'columns': len(table.columns),
                    'column_names': list(table.columns)
                })

        except Exception as e:
            print(f"Error with {pmcid}: {e}")

    return table_info

# Extract tables
paper_ids = ["7181753", "3539614"]  # Papers known to have tables
table_data = extract_all_tables(paper_ids, "your@email.com")

print(f"Extracted {len(table_data)} tables:")
for table in table_data:
    print(f"- PMC{table['pmcid']} Table {table['table_number']}: "
          f"{table['rows']}x{table['columns']} -> {table['filename']}")
```

## Integration Examples

### Building a RAG Dataset

```python
from pmcgrab import Paper
import json
import hashlib

def create_rag_chunks(paper, chunk_size=500, overlap=50):
    """Split paper content into overlapping chunks for RAG."""
    chunks = []

    # Process each section
    for section_name, content in paper.body.items():
        if not content.strip():
            continue

        # Split into chunks
        words = content.split()
        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)

            # Create unique chunk ID
            chunk_id = hashlib.md5(
                f"{paper.pmcid}_{section_name}_{i}".encode()
            ).hexdigest()[:16]

            chunks.append({
                'id': chunk_id,
                'pmcid': paper.pmcid,
                'title': paper.title,
                'section': section_name,
                'content': chunk_text,
                'metadata': {
                    'journal': paper.journal,
                    'authors': [f"{a.get('FirstName', '')} {a.get('LastName', '')}"
                              for a in paper.authors[:3]],  # First 3 authors
                    'pub_date': getattr(paper, 'pub_date', ''),
                    'chunk_index': i // (chunk_size - overlap)
                }
            })

    return chunks

def build_rag_dataset(pmc_ids, email, output_file="rag_dataset.jsonl"):
    """Build a complete RAG dataset."""
    with open(output_file, 'w') as f:
        total_chunks = 0

        for pmcid in pmc_ids:
            try:
                paper = Paper.from_pmc(pmcid, email=email)
                chunks = create_rag_chunks(paper)

                for chunk in chunks:
                    f.write(json.dumps(chunk) + '\n')
                    total_chunks += 1

                print(f"✓ PMC{pmcid}: {len(chunks)} chunks")

            except Exception as e:
                print(f"✗ PMC{pmcid}: {e}")

    print(f"\nRAG dataset created: {total_chunks} total chunks in {output_file}")

# Build RAG dataset
paper_ids = ["7181753", "3539614", "5454911"]
build_rag_dataset(paper_ids, "your@email.com")
```

### Exporting to Different Formats

```python
from pmcgrab import Paper
import json
import xml.etree.ElementTree as ET
import csv

def export_paper_metadata(pmc_ids, email, format='json'):
    """Export paper metadata in various formats."""
    papers_data = []

    for pmcid in pmc_ids:
        try:
            paper = Paper.from_pmc(pmcid, email=email)

            paper_info = {
                'pmcid': paper.pmcid,
                'title': paper.title,
                'journal': paper.journal,
                'authors': [f"{a.get('FirstName', '')} {a.get('LastName', '')}"
                           for a in paper.authors],
                'abstract_sections': list(paper.abstract.keys()),
                'body_sections': list(paper.body.keys()),
                'num_citations': len(paper.citations),
                'num_tables': len(paper.tables),
                'num_figures': len(paper.figures)
            }
            papers_data.append(paper_info)

        except Exception as e:
            print(f"Error with {pmcid}: {e}")

    # Export based on format
    if format == 'json':
        with open('papers_metadata.json', 'w') as f:
            json.dump(papers_data, f, indent=2)

    elif format == 'csv':
        with open('papers_metadata.csv', 'w', newline='') as f:
            if papers_data:
                writer = csv.DictWriter(f, fieldnames=papers_data[0].keys())
                writer.writeheader()
                for paper in papers_data:
                    # Convert lists to strings for CSV
                    paper_copy = paper.copy()
                    for key, value in paper_copy.items():
                        if isinstance(value, list):
                            paper_copy[key] = '; '.join(map(str, value))
                    writer.writerow(paper_copy)

    return papers_data

# Export metadata
paper_ids = ["7181753", "3539614", "5454911"]
metadata = export_paper_metadata(paper_ids, "your@email.com", format='csv')
print(f"Exported metadata for {len(metadata)} papers")
```

These examples demonstrate the flexibility and power of PMCGrab for various research and data processing tasks. You can combine and modify these patterns to suit your specific needs.
