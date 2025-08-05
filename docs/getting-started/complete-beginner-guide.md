# Complete Beginner Guide: From Zero to AI-Ready Scientific Literature

**Never used Python package managers or processed scientific literature before?** This guide starts from absolute zero and gets you processing PMC articles in 10 minutes.

## What You'll Accomplish

By the end of this guide, you'll:

1. Have `uv` and `pmcgrab` installed and working
2. Download and parse your first scientific paper from PMC
3. Understand the JSON structure that's perfect for AI/ML workflows
4. Run a complete example that processes multiple papers
5. Know how to use this data for RAG, vector databases, or LLM training

## Prerequisites

- **Python 3.10+** installed on your system
- **Internet connection** (to download papers from PMC)
- **Terminal/Command Prompt** access

!!! tip "Check your Python version"
`bash
    python --version
    # or on some systems:
    python3 --version
    `

## Step 1: Install uv (The Fast Package Manager)

`uv` is a blazing-fast Python package manager that makes installing and managing packages much easier than traditional `pip`.

### Install or Update uv

If you already have `uv` installed, update it first:

```bash
# If installed via pip
curl -LsSf https://astral.sh/uv/install.sh | sh  # upgrade

# Or rerun the install script (macOS/Linux example):
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Otherwise, install uv:

=== "macOS/Linux"
`bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    `

=== "Windows"
`powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    `

=== "Already have pip?"
`bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    `

### Verify installation:

```bash
# Restart your terminal first, then:
uv --version
```

You should see something like `uv 0.4.x` or similar.

## Step 2: Install PMCGrab

Now install PMCGrab using uv:

```bash
uv add pmcgrab
```

!!! note "First time using uv?"
If this is your first time using `uv add`, it might ask to create a virtual environment. Say yes! This keeps your project dependencies clean.

### Verify PMCGrab installation:

```python
# Create a file called test_install.py and run it
import pmcgrab
print("PMCGrab version:", pmcgrab.__version__)
print("Installation successful!")
```

```bash
uv run python test_install.py
```

## Step 3: Your First Paper - Understanding PMC IDs

**PMC IDs** are unique identifiers for papers in PubMed Central. For example:

- URL: `https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7114487/`
- PMC ID: `7114487` (just the number part)

Let's fetch this paper and see what PMCGrab gives us:

```python
# Create first_paper.py
from pmcgrab.application.processing import process_single_pmc

# Process a single paper (this might take 5-10 seconds)
pmcid = "7114487"
print(f"Fetching PMC{pmcid} from PubMed Central...")

data = process_single_pmc(pmcid)

if data:
    print("Success! Here's what we got:")
    print(f"Title: {data['title']}")
    print(f"Journal: {data['journal']}")
    print(f"Number of authors: {len(data['authors'])}")
    print(f"Paper has these sections: {list(data['body'].keys())}")
    print(f"Abstract preview: {data['abstract'][:200]}...")
else:
    print("Failed to fetch the paper")
```

Run it:

```bash
uv run python first_paper.py
```

## Step 4: Understanding the JSON Structure (AI/ML Gold!)

The output from PMCGrab is structured JSON that's perfect for AI workflows. Let's explore it:

```python
# Create explore_structure.py
import json
from pmcgrab.application.processing import process_single_pmc

# Get the data
data = process_single_pmc("7114487")

# Save to a file so we can examine it
with open("sample_paper.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Paper saved to sample_paper.json")
print("\nLet's explore the structure:")

# Top-level structure
print(f"Top-level keys: {list(data.keys())}")

# Authors structure
print(f"\nFirst author: {data['authors'][0]}")

# Body sections (perfect for RAG!)
print(f"\nAvailable sections:")
for section, content in data['body'].items():
    print(f"  - {section}: {len(content)} characters")
    print(f"    Preview: {content[:100]}...\n")
```

Run it:

```bash
uv run python explore_structure.py
```

## Step 5: Batch Processing - The Real Power

Now let's process multiple papers at once. This is where PMCGrab shines for building datasets:

```python
# Create batch_example.py
import json
from pathlib import Path
from pmcgrab.application.processing import process_single_pmc

# Papers related to COVID-19 and machine learning in medicine
INTERESTING_PAPERS = {
    "7114487": "COVID-19 pandemic response",
    "3084273": "Machine learning in genomics",
    "7181753": "Single-cell skin transcriptomics",
    "5707528": "Deep learning applications",
    "7979870": "Bioinformatics methods"
}

# Create output directory
output_dir = Path("processed_papers")
output_dir.mkdir(exist_ok=True)

print("Starting batch processing...")
print(f"Results will be saved to: {output_dir}")
print("=" * 50)

successful = 0
failed = 0

for pmcid, description in INTERESTING_PAPERS.items():
    print(f"\nProcessing PMC{pmcid}: {description}")

    try:
        data = process_single_pmc(pmcid)

        if data:
            # Save as JSON
            output_file = output_dir / f"PMC{pmcid}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"   Success! Title: {data['title'][:60]}...")
            print(f"   {len(data['authors'])} authors, {len(data['body'])} sections")
            print(f"   Saved to: {output_file}")
            successful += 1
        else:
            print(f"   Failed to process PMC{pmcid}")
            failed += 1

    except Exception as e:
        print(f"   Error processing PMC{pmcid}: {e}")
        failed += 1

print("\n" + "=" * 50)
print(f"Batch processing complete!")
print(f"Successful: {successful}")
print(f"Failed: {failed}")
print(f"Check the '{output_dir}' folder for your JSON files")
```

Run it:

```bash
uv run python batch_example.py
```

## Step 6: What Can You Do With This Data?

The JSON files you now have are **perfect for AI workflows**:

### RAG (Retrieval-Augmented Generation)

```python
# Example: Extract content for vector database
sections_for_rag = []
for section, content in data['body'].items():
    sections_for_rag.append({
        "source": f"PMC{data['pmc_id']}",
        "section": section,
        "content": content,
        "metadata": {
            "title": data['title'],
            "journal": data['journal'],
            "authors": [f"{a['First_Name']} {a['Last_Name']}" for a in data['authors']]
        }
    })
```

### LLM Training Data

```python
# Create training examples
training_examples = []
for pmcid, paper_data in all_papers.items():
    training_examples.append({
        "input": f"Summarize this {paper_data['journal']} paper about {paper_data['title']}",
        "output": paper_data['abstract']
    })
```

### Research Analysis

```python
# Analyze paper characteristics
import pandas as pd

paper_stats = []
for file in Path("processed_papers").glob("*.json"):
    with open(file) as f:
        paper = json.load(f)

    paper_stats.append({
        "pmcid": paper['pmc_id'],
        "title": paper['title'],
        "journal": paper['journal'],
        "num_authors": len(paper['authors']),
        "num_sections": len(paper['body']),
        "abstract_length": len(paper['abstract']),
        "total_content": sum(len(content) for content in paper['body'].values())
    })

df = pd.DataFrame(paper_stats)
print(df.describe())
```

## Step 7: Command Line Power User

PMCGrab also works from the command line for quick processing:

```bash
# Process single paper
uv run python -m pmcgrab --pmcids 7114487

# Process multiple papers with 4 workers (parallel processing)
uv run python -m pmcgrab --pmcids 7114487 3084273 7181753 --workers 4

# Custom output directory
uv run python -m pmcgrab --pmcids 7114487 --output-dir ./my_papers
```

## Next Steps: Level Up Your Usage

Now that you've got the basics down:

1. **[Advanced Usage Guide](../examples/advanced-usage.md)** - Error handling, custom processing
2. **[Jupyter Notebook Tutorial](jupyter-tutorial.md)** - Interactive exploration
3. **[CLI Reference](../user-guide/cli.md)** - Complete command-line options
4. **[API Documentation](../api/core.md)** - Full API reference

## Troubleshooting

### Common Issues:

**"Failed to process PMC..."**

- The paper might not be open access
- Network connectivity issues
- Invalid PMC ID

**"Import Error"**

- Make sure you're using `uv run python` instead of just `python`
- Verify installation: `uv run python -c "import pmcgrab; print('OK')"`

**"No sections found"**

- Some papers have non-standard structures
- Check if the paper is a research article (not editorial, letter, etc.)

### Getting Help:

- [Full Documentation](https://rajdeepmondaldotcom.github.io/pmcgrab/)
- 🐛 [Report Issues](https://github.com/rajdeepmondaldotcom/pmcgrab/issues)
- 💬 [Discussions](https://github.com/rajdeepmondaldotcom/pmcgrab/discussions)

## Congratulations!

You now know how to:

- Install and use PMCGrab
- Process scientific papers into AI-ready JSON
- Handle batch processing for building datasets
- Structure data for RAG, LLMs, and research analysis

**Start building amazing AI applications with scientific literature!**
