# Interactive Jupyter Notebook Tutorial

**Want hands-on experience with PMCGrab?** Our interactive Jupyter notebook provides a complete walkthrough from installation to building AI-ready datasets.

## What's Inside

The notebook covers:

- **Single Paper Processing**: Start with one paper and explore the output
- **Batch Processing**: Build a multi-paper dataset
- **AI/ML Preparation**: Structure data for RAG, vector databases, and LLM training
- **Data Export**: Save everything in organized formats
- **Analysis**: Visualize and understand your dataset

## Quick Start

1. **Download the notebook**:
   - **[View on GitHub](https://github.com/rajdeepmondaldotcom/pmcgrab/blob/main/examples/pmcgrab_tutorial.ipynb)** (renders properly)
   - **[Direct download](../../examples/pmcgrab_tutorial.ipynb)** (local file)

2. **Install dependencies**:

   ```bash
   # Update uv first (or install if you don't have it)
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Install PMCGrab and Jupyter
   uv add pmcgrab jupyter pandas matplotlib seaborn
   ```

3. **Launch Jupyter**:

   ```bash
   uv run jupyter notebook
   ```

4. **Open the notebook** and start processing papers!

## Prerequisites

- **Python 3.10+**
- **Internet connection** (to fetch papers from PMC)
- **Basic Python knowledge** (helpful but not required)

## What You'll Build

By the end of the notebook, you'll have:

- **Individual Paper JSONs**: Clean, structured data for each paper
- **RAG Chunks**: Ready for vector database ingestion
- **Training Examples**: Structured for LLM fine-tuning
- **Dataset Analysis**: Statistical overview of your collection

## Perfect For

- **First-time users** wanting interactive exploration
- **Data scientists** building biomedical datasets
- **AI researchers** preparing training data
- **Students** learning about scientific text processing

## Troubleshooting

### Common Issues:

**"Failed to process PMC..."**

- Network connectivity issue
- Paper may not be open access
- Try a different PMC ID

**"ModuleNotFoundError"**

- Make sure you're using `uv run jupyter notebook`
- Verify installation: `uv run python -c "import pmcgrab; print('OK')"`

**Notebook won't start**

- Check Python version: `python --version` (need 3.10+)
- Try: `uv run pip install jupyter` then `uv run jupyter notebook`

## Advanced Usage

Once you're comfortable with the basics:

- **Scale up**: Process 100s or 1000s of papers using the CLI
- **Integrate**: Connect to your vector database or ML pipeline
- **Customize**: Modify the notebook for your specific use case

## Next Steps

After completing the notebook:

- **[Complete Beginner Guide](complete-beginner-guide.md)**: More detailed explanations
- **[CLI Reference](../user-guide/cli.md)**: Command-line usage
- **[Advanced Examples](../examples/advanced-usage.md)**: Production workflows

## Need Help?

- [Full Documentation](https://rajdeepmondaldotcom.github.io/pmcgrab/)
- [Report Issues](https://github.com/rajdeepmondaldotcom/pmcgrab/issues)
- [GitHub Discussions](https://github.com/rajdeepmondaldotcom/pmcgrab/discussions)

---

**Ready to turn scientific literature into AI-ready data?**

- **[View notebook on GitHub](https://github.com/rajdeepmondaldotcom/pmcgrab/blob/main/examples/pmcgrab_tutorial.ipynb)** (fully rendered)
- **[Download notebook](../../examples/pmcgrab_tutorial.ipynb)** and start exploring!
