# Basic Usage

This guide covers the fundamental ways to use PMCGrab for retrieving and processing PMC articles.

## Single Article Processing

### Using the Paper Class

The `Paper` class is the most convenient way to work with individual articles:

```python
from pmcgrab import Paper

# Basic usage
paper = Paper.from_pmc("7181753", email="your-email@example.com")

# Access article metadata
print(f"Title: {paper.title}")
print(f"PMCID: {paper.pmcid}")
print(f"Journal: {paper.journal}")
print(f"Publication Date: {paper.pub_date}")
```

### Exploring Article Structure

```python
# Authors and contributors
print(f"Number of authors: {len(paper.authors)}")
for author in paper.authors[:3]:  # First 3 authors
    name = f"{author.get('FirstName', '')} {author.get('LastName', '')}"
    affiliation = author.get('Affiliation', 'N/A')
    print(f"- {name} ({affiliation})")

# Abstract sections
print("\nAbstract sections:")
for section, content in paper.abstract.items():
    print(f"- {section}: {len(content)} characters")

# Body sections
print("\nBody sections:")
for section, content in paper.body.items():
    print(f"- {section}: {len(content)} characters")
```

### Working with References

```python
# Citations
print(f"Number of citations: {len(paper.citations)}")
for i, citation in enumerate(paper.citations[:3]):
    print(f"{i+1}. {citation}")

# Tables
print(f"Number of tables: {len(paper.tables)}")
for i, table in enumerate(paper.tables):
    print(f"Table {i+1}: {table.shape}")  # pandas DataFrame

# Figures
print(f"Number of figures: {len(paper.figures)}")
for i, figure in enumerate(paper.figures):
    print(f"Figure {i+1}: {figure.get('Label', 'N/A')}")
```

## Using Raw Dictionaries

If you prefer working with dictionaries instead of objects:

```python
from pmcgrab import paper_dict_from_pmc

# Get structured dictionary
article = paper_dict_from_pmc(
    7181753,
    email="your-email@example.com",
    validate=True,    # Validate XML structure
    verbose=True      # Show progress
)

# Access data
print(article['Title'])
print(article['Abstract']['Background'])
print(article['Body']['Introduction'][:500])
```

## Configuration Options

### Caching and Validation

```python
paper = Paper.from_pmc(
    "7181753",
    email="your-email@example.com",
    download=True,        # Cache XML locally
    validate=True,        # Perform DTD validation
    verbose=True          # Show progress messages
)
```

### Error Handling

```python
from pmcgrab import Paper

try:
    paper = Paper.from_pmc("7181753", email="your-email@example.com")
    print(f"Successfully processed: {paper.title}")

except ValueError as e:
    print(f"Invalid input: {e}")

except ConnectionError as e:
    print(f"Network error: {e}")

except Exception as e:
    print(f"Unexpected error: {e}")
```

### Suppressing Warnings and Errors

```python
# Suppress parsing warnings
paper = Paper.from_pmc(
    "7181753",
    email="your-email@example.com",
    suppress_warnings=True
)

# Return None instead of raising errors
paper = Paper.from_pmc(
    "invalid_id",
    email="your-email@example.com",
    suppress_errors=True
)
if paper is None:
    print("Failed to process article")
```

## Working with Article Content

### Accessing Specific Sections

```python
# Get introduction
intro = paper.body.get('Introduction', '')
if intro:
    print(f"Introduction: {intro[:200]}...")

# Get methods
methods = paper.body.get('Methods', '')
if methods:
    print(f"Methods: {methods[:200]}...")

# Handle missing sections gracefully
discussion = paper.body.get('Discussion', 'No discussion section found')
print(discussion[:200])
```

### Cleaning HTML Content

PMCGrab provides utilities to clean HTML tags and references:

```python
from pmcgrab.common.html_cleaning import clean_html_tags, remove_references

# Clean HTML tags
clean_text = clean_html_tags(paper.body['Introduction'])

# Remove reference markers
no_refs = remove_references(clean_text)
print(no_refs[:200])
```

### Working with Tables

Tables are returned as pandas DataFrames:

```python
import pandas as pd

if paper.tables:
    first_table = paper.tables[0]
    print(f"Table shape: {first_table.shape}")
    print(f"Columns: {list(first_table.columns)}")

    # Save table to CSV
    first_table.to_csv('table_1.csv', index=False)

    # Display first few rows
    print(first_table.head())
```

## Low-Level API

For advanced use cases, you can use the low-level parsing functions:

```python
from pmcgrab.fetch import get_xml
from pmcgrab.parser import build_complete_paper_dict

# Fetch XML directly
xml_root = get_xml("7181753", email="your-email@example.com")

# Parse with custom options
paper_dict = build_complete_paper_dict(
    xml_root,
    suppress_warnings=False,
    suppress_errors=False
)
```

## Next Steps

- **[Batch Processing](batch-processing.md)**: Process multiple articles efficiently
- **[Command Line Interface](cli.md)**: Use PMCGrab from the command line
- **[Output Format](output-format.md)**: Understand the output structure
- **[Examples](../examples/python-examples.md)**: See real-world usage examples
