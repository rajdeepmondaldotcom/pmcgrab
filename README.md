# PMCGrab - From PubMed Central ID to AI-Ready JSON in Seconds

[![PyPI](https://img.shields.io/pypi/v/pmcgrab.svg)](https://pypi.org/project/pmcgrab/) [![Python](https://img.shields.io/pypi/pyversions/pmcgrab.svg)](https://pypi.org/project/pmcgrab/) [![Docs](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://rajdeepmondaldotcom.github.io/pmcgrab/) [![CI](https://github.com/rajdeepmondaldotcom/pmcgrab/workflows/CI/badge.svg)](https://github.com/rajdeepmondaldotcom/pmcgrab/actions) [![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/rajdeepmondaldotcom/pmcgrab/blob/main/LICENSE)

Every AI workflow that touches biomedical literature hits the same wall:

1. **Download** PMC XML hoping it’s “structured.”
2. **Fight** nested tags, footnotes, figure refs, and half-broken links.
3. **Hope** your regex didn’t blow away the Methods section you actually need.

That wall steals hours from **RAG pipelines, knowledge-graph builds, LLM fine-tuning-any downstream AI task**.
**PMCGrab knocks it down.** Feed the tool a list of PMC IDs and get back clean, section-aware JSON you can drop straight into a vector DB or LLM prompt.

---

## The Hidden Cost of “I’ll Just Parse It Myself”

| Task                        | Manual / ad-hoc         | **PMCGrab**                    |
| --------------------------- | ----------------------- | ------------------------------ |
| Install dependencies        | 5–10 min                | **≈ 2 s** (`uv add pmcgrab`)   |
| Convert one article to JSON | 15–30 min               | **≈ 3 s**                      |
| Capture every IMRaD section | Hope & regex            | **98 % detection accuracy\***  |
| Parallel processing         | Bash loops & temp files | `--workers N` flag             |
| Edge-case maintenance       | Yours forever           | **200 + tests**, active upkeep |

**_Evaluated on 7,500 PMC papers used in a disease-specific knowledge-graph pipeline._**

At \$50 /hour, hand-parsing 100 papers burns **\$1,000+**.
PMCGrab does the same job for \$0-within minutes-so you can focus on _using_ the information instead of extracting it.

---

## Quick Install

Install via **uv** (make sure `uv` itself is up to date first)

```bash
uv add pmcgrab
```

Python ≥ 3.10 required.

---

## Ways to Use

### 1 · Python API (recommended)

```python
from pmcgrab import Paper

paper = Paper.from_pmc("7181753", suppress_warnings=True)

print(paper.title)
print(paper.abstract_as_str()[:200])

for section, text in paper.body_as_dict().items():
    print(f"{section}: {len(text.split())} words")

# Save to JSON
paper.to_json()
```

### 2 · Dict-based API (for data pipelines)

```python
from pmcgrab.application.processing import process_single_pmc

data = process_single_pmc("7181753")

print(data["title"])
print(data["abstract_text"])       # plain-text abstract (string)
print(data["abstract"])            # structured abstract (dict)
print(list(data["body"].keys()))   # section titles
```

### 3 · Command Line

```bash
# Single or multiple PMC IDs
pmcgrab --pmcids 7181753 3539614 --output-dir ./results

# From a file of IDs
pmcgrab --from-id-file ids.txt --output-dir ./results

# Local XML files (no network)
pmcgrab --from-dir ./xml_bulk/ --output-dir ./results
```

Use the numeric part of the PMC ID only (e.g. `7181753`, not `PMC7181753`).

---

## Output Example

```json
{
  "pmc_id": "7181753",
  "title": "Single-cell transcriptomes of the human skin reveal ...",
  "abstract_text": "Human skin provides a protective barrier ...",
  "abstract": {
    "Background": "Human skin provides a protective barrier ...",
    "Results": "We generated single-cell transcriptomes ..."
  },
  "body": {
    "Background": "...",
    "Results": "...",
    "Discussion": "...",
    "Methods": "..."
  },
  "authors": [{"First_Name": "...", "Last_Name": "...", ...}],
  "journal_title": "Genome Biology",
  "full_text": "..."
}
```

---

## Context Engineering: Why This Matters for LLMs

Large-language-model performance lives or dies on **context quality**-the snippets you retrieve and feed back into the model:

- **RAG pipelines** need precise, de-duplicated passages to ground answers.
- **Knowledge-graph population** demands reliable section boundaries (e.g., Methods vs. Results) to classify triples accurately.
- **Fine-tuning & few-shot prompting** work best with noise-free, domain-specific examples.

PMCGrab _is_ a context-engineering tool: it converts messy XML into **clean, section-aware, UTF-8 JSON** that slots directly into embeddings, vector stores, or prompt templates. No preprocessing gymnastics, no guessing where the Methods section starts, no hallucinations from half-garbled text. Better input → better retrieval → better answers.

---

## Why PMCGrab Beats Home-Grown Scripts

1. **Section-Aware Parsing**
   Detects IMRaD plus custom subsections like _Statistical Analysis_-crucial for accurate retrieval scoring.

2. **Resilient XML Cleaning**
   Removes cross-refs and figure stubs without dropping scientific content, preserving token-level fidelity for embeddings.

3. **True Concurrency**
   `--workers` fan-outs across all CPU cores; automatic email rotation respects NCBI rate limits so large harvests don’t throttle.

4. **Modern Python Stack**
   Type-safe (`mypy`), linted (`ruff`), CI-checked on Ubuntu, macOS, and Windows.

---

## Proof at a Glance

| Metric                      | Value              |
| --------------------------- | ------------------ |
| Unit tests                  | **218**            |
| Branch coverage             | **95 %**           |
| Section detection accuracy  | **98 %**           |
| Median parse time / article | **3.1 s**          |
| Largest batch processed     | **7,500 articles** |

---

## Promise to you

If PMCGrab doesn’t save you hours on day one, delete it-no questions asked.
Once you see clean JSON in seconds, you’ll never fight PMC XML again.

---

## Install Now & Ship Real Results

```bash
uv add pmcgrab
```

Stop paying the **XML tax**. Start engineering context-and building AI products that matter.
