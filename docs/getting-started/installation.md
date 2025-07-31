# Installation

PMCGrab supports Python 3.9+ and can be installed via pip or from source.

## Using pip (Recommended)

```bash
pip install pmcgrab
```

This installs the latest stable version from PyPI along with all required dependencies.

## From Source

If you want the latest development version or need to modify PMCGrab:

```bash
git clone https://github.com/rajdeepmondaldotcom/pmcgrab.git
cd pmcgrab
pip install -e .
```

## Development Installation

For development work, install with development dependencies:

```bash
git clone https://github.com/rajdeepmondaldotcom/pmcgrab.git
cd pmcgrab

# Using uv (recommended)
uv sync --dev

# Or using pip
pip install -e ".[dev]"
```

## Verify Installation

Test your installation:

```python
import pmcgrab
print(pmcgrab.__version__)
```

Or use the command line:

```bash
python -m pmcgrab --help
```

## Dependencies

PMCGrab requires the following packages:

- **beautifulsoup4** (≥4.13.4) - HTML parsing
- **biopython** (≥1.83) - Biological data structures
- **lxml** (≥4.9.0) - XML processing
- **numpy** (≥1.24.0) - Numerical operations
- **pandas** (≥2.0.0) - Data manipulation
- **requests** (≥2.28.0) - HTTP requests
- **tqdm** (≥4.64.0) - Progress bars

## Optional Dependencies

For development and documentation:

```bash
pip install "pmcgrab[dev]"    # Development tools
pip install "pmcgrab[docs]"   # Documentation tools
pip install "pmcgrab[test]"   # Testing dependencies
```

## System Requirements

- **Python**: 3.9, 3.10, 3.11, 3.12, or 3.13
- **Operating System**: Windows, macOS, or Linux
- **Memory**: Minimum 512MB RAM (2GB+ recommended for batch processing)
- **Network**: Internet connection required for PMC article retrieval

## Common Issues

### ImportError with lxml

If you encounter issues with lxml installation:

```bash
# On Ubuntu/Debian
sudo apt-get install libxml2-dev libxslt-dev python3-dev

# On macOS
brew install libxml2 libxslt

# Then reinstall
pip install --force-reinstall lxml
```

### Permission Errors

If you get permission errors during installation:

```bash
pip install --user pmcgrab
```

### Virtual Environment (Recommended)

Always use a virtual environment:

```bash
python -m venv pmcgrab-env
source pmcgrab-env/bin/activate  # On Windows: pmcgrab-env\Scripts\activate
pip install pmcgrab
```

## Next Steps

Once installed, proceed to [Quick Start](quick-start.md) to begin using PMCGrab.
