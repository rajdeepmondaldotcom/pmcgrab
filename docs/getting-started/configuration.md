# Configuration

PMCGrab provides several configuration options to customize its behavior.

## Environment Variables

You can set configuration via environment variables:

```bash
export PMCGRAB_EMAIL="your-email@example.com"
export PMCGRAB_MAX_WORKERS=8
export PMCGRAB_TIMEOUT=30
export PMCGRAB_CACHE_DIR="./pmcgrab_cache"
```

## Email Configuration

NCBI requires an email address for API access:

```python
from pmcgrab import Paper

# Method 1: Pass email directly
paper = Paper.from_pmc("7181753", email="your-email@example.com")

# Method 2: Set environment variable
import os
os.environ['PMCGRAB_EMAIL'] = 'your-email@example.com'
paper = Paper.from_pmc("7181753")  # Email from environment
```

## Batch Processing Settings

### Worker Configuration

```python
from pmcgrab import process_pmc_ids_in_batches

process_pmc_ids_in_batches(
    pmc_ids=["7181753", "3539614"],
    output_dir="./output",
    max_workers=8,      # Number of parallel workers
    batch_size=10,      # Articles per batch
    timeout=30,         # Request timeout in seconds
    max_retries=3       # Retry failed downloads
)
```

### Performance Tuning

```python
# For high-throughput processing
process_pmc_ids_in_batches(
    pmc_ids=large_id_list,
    output_dir="./output",
    max_workers=16,     # More workers for I/O bound tasks
    batch_size=50,      # Larger batches
    timeout=60,         # Longer timeout for reliability
    max_retries=5       # More retries for unreliable networks
)

# For memory-constrained environments
process_pmc_ids_in_batches(
    pmc_ids=large_id_list,
    output_dir="./output",
    max_workers=2,      # Fewer workers
    batch_size=5,       # Smaller batches
    timeout=30,
    max_retries=3
)
```

## Caching Configuration

Enable local caching to avoid re-downloading articles:

```python
from pmcgrab import Paper

# Enable caching
paper = Paper.from_pmc(
    "7181753",
    email="your-email@example.com",
    download=True,      # Cache XML files locally
    cache_dir="./cache" # Custom cache directory
)
```

## Validation Settings

Control XML validation behavior:

```python
# Strict validation (default)
paper = Paper.from_pmc(
    "7181753",
    email="your-email@example.com",
    validate=True      # Perform DTD validation
)

# Skip validation for speed
paper = Paper.from_pmc(
    "7181753",
    email="your-email@example.com",
    validate=False     # Skip validation
)
```

## Error Handling Configuration

### Suppressing Warnings

```python
import warnings
from pmcgrab import Paper

# Method 1: PMCGrab-specific suppression
paper = Paper.from_pmc(
    "7181753",
    email="your-email@example.com",
    suppress_warnings=True
)

# Method 2: Global warning suppression
warnings.filterwarnings('ignore')
paper = Paper.from_pmc("7181753", email="your-email@example.com")
```

### Error Recovery

```python
# Return None instead of raising exceptions
paper = Paper.from_pmc(
    "invalid_id",
    email="your-email@example.com",
    suppress_errors=True
)

if paper is None:
    print("Failed to process article")
else:
    print(f"Successfully processed: {paper.title}")
```

## Logging Configuration

Set up detailed logging:

```python
import logging
from pmcgrab import Paper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable verbose output
paper = Paper.from_pmc(
    "7181753",
    email="your-email@example.com",
    verbose=True
)
```

### Custom Logger

```python
import logging
from pmcgrab import process_pmc_ids_in_batches

# Create custom logger
logger = logging.getLogger('pmcgrab.custom')
logger.setLevel(logging.DEBUG)

# Add file handler
handler = logging.FileHandler('pmcgrab.log')
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# Process with logging
process_pmc_ids_in_batches(
    pmc_ids=["7181753", "3539614"],
    output_dir="./output",
    verbose=True
)
```

## Configuration Files

### JSON Configuration

Create `pmcgrab_config.json`:

```json
{
  "email": "your-email@example.com",
  "max_workers": 8,
  "batch_size": 20,
  "timeout": 45,
  "max_retries": 3,
  "cache_dir": "./pmcgrab_cache",
  "validate": true,
  "verbose": false
}
```

Load configuration:

```python
import json
from pmcgrab import process_pmc_ids_in_batches

# Load config
with open('pmcgrab_config.json') as f:
    config = json.load(f)

# Use config
process_pmc_ids_in_batches(
    pmc_ids=["7181753", "3539614"],
    output_dir="./output",
    **config
)
```

### YAML Configuration

Create `pmcgrab_config.yaml`:

```yaml
email: your-email@example.com
max_workers: 8
batch_size: 20
timeout: 45
max_retries: 3
cache_dir: ./pmcgrab_cache
validate: true
verbose: false
```

Load with PyYAML:

```python
import yaml
from pmcgrab import process_pmc_ids_in_batches

# Load config
with open('pmcgrab_config.yaml') as f:
    config = yaml.safe_load(f)

# Use config
process_pmc_ids_in_batches(
    pmc_ids=["7181753", "3539614"],
    output_dir="./output",
    **config
)
```

## Command Line Configuration

Override settings via command line:

```bash
# Set environment variables
export PMCGRAB_EMAIL="your-email@example.com"
export PMCGRAB_MAX_WORKERS=8

# Use in command
python -m pmcgrab PMC7181753 PMC3539614

# Or pass directly
python -m pmcgrab \
    --email your-email@example.com \
    --workers 8 \
    --batch-size 20 \
    --timeout 45 \
    --max-retries 3 \
    --output-dir ./results \
    PMC7181753 PMC3539614
```

## Best Practices

### Production Settings

```python
# Recommended production configuration
production_config = {
    'max_workers': 8,           # Balance speed and server load
    'batch_size': 25,           # Efficient batching
    'timeout': 60,              # Generous timeout
    'max_retries': 5,           # Robust retry logic
    'validate': True,           # Ensure data quality
    'download': True,           # Cache for reprocessing
    'suppress_warnings': False, # Log all issues
    'verbose': True             # Detailed logging
}
```

### Development Settings

```python
# Recommended development configuration
dev_config = {
    'max_workers': 2,           # Don't overwhelm during testing
    'batch_size': 5,            # Small batches for quick feedback
    'timeout': 30,              # Faster feedback on failures
    'max_retries': 2,           # Quick failure detection
    'validate': False,          # Speed up development
    'download': False,          # Don't clutter filesystem
    'suppress_warnings': False, # See all issues
    'verbose': True             # Detailed output
}
```

## Performance Optimization

### Network Optimization

```python
# For unreliable networks
slow_network_config = {
    'max_workers': 4,      # Fewer concurrent requests
    'timeout': 120,        # Longer timeout
    'max_retries': 10,     # More retries
    'batch_size': 10       # Smaller batches
}

# For fast, reliable networks
fast_network_config = {
    'max_workers': 16,     # More concurrency
    'timeout': 30,         # Shorter timeout
    'max_retries': 3,      # Fewer retries needed
    'batch_size': 50       # Larger batches
}
```

### Memory Optimization

```python
# For memory-constrained environments
memory_optimized_config = {
    'max_workers': 2,      # Limit concurrent processing
    'batch_size': 5,       # Process fewer at once
    'download': False,     # Don't cache XML
    'validate': False      # Skip validation overhead
}
```
