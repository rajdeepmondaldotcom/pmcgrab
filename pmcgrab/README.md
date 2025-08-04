# pmcgrab

**Your gateway to AI-ready scientific literature from PubMed Central.**

`pmcgrab` is a powerful Python toolkit for downloading, parsing, and structuring articles from PubMed Central (PMC). It transforms raw XML from PMC into a highly curated, AI-ready JSON format, specifically designed to be easily consumed by Large Language Models (LLMs) for robust Retrieval-Augmented Generation (RAG) applications.

## Why `pmcgrab`?

While the NCBI Entrez API provides access to article data, `pmcgrab` excels by intelligently processing the raw XML into a semantically rich and immediately usable format. Instead of dealing with complex XML schemas or flat text, you get a clean, structured JSON that preserves the distinct sections of a scientific paper, making it perfect for advanced AI tasks.

The core strength of `pmcgrab` lies in its output. It produces a detailed JSON object where the paper's body is pre-segmented by its natural sections (e.g., Introduction, Methods, Results), which is critical for enabling LLMs to perform targeted context retrieval.

## Key Features

- **Effortless Article Retrieval**: Fetch full-text articles using just a PubMed Central ID (PMCID) via the NCBI Entrez API.
- **AI-Optimized JSON Output**: Generates a meticulously structured JSON that separates high-level metadata, the abstract, and sectioned body text for optimal use in RAG pipelines.
- **Robust Batch Processing**: Process thousands of articles concurrently with configurable retries and error handling, ideal for building large-scale datasets.
- **Data Integrity**: Includes optional DTD validation to ensure all XML inputs are well-formed before processing.
- **Content Utilities**: Provides functions for cleaning embedded HTML tags and resolving in-text citations and references.

## Installation

Install the package directly from PyPI:

```bash
pip install pmcgrab
```

Or from a local clone of the repository:

```bash
pip install .
```

## Quick Start

Fetch a single article and access its structured data with just two lines of code.

```python
from pmcgrab import Paper

# The email is required by the NCBI API for identification.
paper = Paper.from_pmc("7181753", "sachinrajdeeptendulkar@gmail.com")

print(f"Title: {paper.title}")
print(f"Journal: {paper.journal_title}")
print(f"Published Date: {paper.published_date.get('epub')}")

# Access specific sections of the paper's body
if "Introduction" in paper.body:
    print("\n--- Introduction Snippet ---")
    print(paper.body["Introduction"][:300] + "...")
```

## Batch Processing

For building larger datasets, `pmcgrab` can process a list of PMCIDs concurrently and save each result as a separate JSON file. This is ideal for populating a vector database for a RAG system.

```python
from pmcgrab.processing import process_in_batches_with_retry

pmc_ids = ["7181753", "PMC3539614", "PMC5454911"]

# This will fetch all articles and save them as JSON files
# in the 'output_papers' directory.
process_in_batches_with_retry(
    pmc_ids=pmc_ids,
    output_dir="output_papers",
    email="your.name@example.com"
)
```

Each article is written to `output_papers/PMC.json`.

## Logging

`pmcgrab` uses Python's built-in `logging` module. The library does not
configure logging for you, so to see informational or debugging output
you should set up logging in your application before calling `pmcgrab`:

```python
import logging

logging.basicConfig(level=logging.INFO)  # use DEBUG for more detail
```

Once configured, log messages from the `pmcgrab` logger will be emitted
according to your chosen logging level.

## The AI-Ready Output Structure

The output JSON is designed for easy parsing and direct ingestion into AI pipelines. It separates key metadata from the core content and, most importantly, structures the body of the paper into its constituent parts.

### Output Schema Highlights:

- **Top-Level Metadata**: Clean, accessible fields like `pmc_id`, `title`, `doi`, and `pmid`.
- **Structured Authorship**: A list of `authors` with their full name and `Affiliations`.
- **Sectioned Body**: The `body` is a dictionary where keys are the paper's section titles (e.g., `Introduction`, `Methods`, `Results`, `Discussion`) and values are the text within them. This allows an AI application to search for information within a specific context.
- **Enriched Information**: The parser also extracts and structures supplementary data, including `funding` information, `acknowledgements`, `license`, and `permissions`.

### Example Output Snippet

Below is a condensed example of the JSON structure generated for PMCID `7181753`.

```json
{
  "pmc_id": "7181753",
  "title": "Single-cell transcriptomes of the human skin reveal age-related loss of fibroblast priming",
  "abstract": "Fibroblasts are an essential cell population for human skin architecture and function. While fibroblast heterogeneity is well established, this phenomenon has not been analyzed systematically yet...",
  "authors": [
    {
      "Contributor_Type": "Author",
      "First_Name": "Llorenç",
      "Last_Name": "Solé-Boldo",
      "Affiliations": [
        "Aff1: Division of Epigenetics, DKFZ-ZMBH Alliance,  German Cancer Research Center, 69120 Heidelberg, Germany"
      ]
    }
  ],
  "body": {
    "Introduction": "SECTION: Introduction:\\n\\n    The skin is the outermost protective barrier of the organism and comprises two main layers, the epidermis and the dermis...",
    "Results": "SECTION: Results:\\n\\n    SECTION: scRNA-seq analysis of sun-protected human skin:\\n\\n        The anatomy of the skin can vary considerably depending on a number of endogenous and environmental factors...",
    "Discussion": "SECTION: Discussion:\\n\\n    Single-cell transcriptomics currently represents the most effective method to define cell populations in a given tissue...",
    "Methods": "SECTION: Methods:\\n\\n    SECTION: Clinical samples:\\n\\n        Skin specimens for single-cell RNA sequencing (see Supplementary Table 1) were obtained from patients undergoing routine surgery..."
  },
  "published_date": {
    "epub": "2020-04-23",
    "collection": "2020-01-01"
  },
  "journal_title": "Communications Biology"
}
```

## License

`pmcgrab` is licensed under the Apache 2.0 License.
