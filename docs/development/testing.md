# Testing

Comprehensive testing guide for PMCGrab development.

## Test Structure

```
tests/
├── conftest.py              # Shared test configuration
├── test_model.py           # Paper model tests
├── test_parser.py          # Parser tests
├── test_cli_complete.py    # CLI integration tests
├── test_processing.py      # Processing pipeline tests
└── fixtures/               # Test data and fixtures
    ├── sample_articles/
    └── mock_responses/
```

## Running Tests

### Basic Test Execution

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_model.py

# Run specific test function
uv run pytest tests/test_model.py::test_paper_creation
```

### Coverage Analysis

```bash
# Run tests with coverage
uv run pytest --cov=pmcgrab

# Generate HTML coverage report
uv run pytest --cov=pmcgrab --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Performance Testing

```bash
# Run performance tests
uv run pytest -m performance

# Profile test execution
uv run pytest --profile

# Benchmark tests
uv run pytest --benchmark-only
```

## Test Categories

### Unit Tests

Test individual components in isolation:

```python
def test_paper_title_extraction():
    """Test paper title extraction from XML."""
    xml_content = """
    <article>
        <front>
            <article-meta>
                <title-group>
                    <article-title>Test Article Title</article-title>
                </title-group>
            </article-meta>
        </front>
    </article>
    """

    paper = Paper.from_xml(xml_content, email="test@example.com")
    assert paper.title == "Test Article Title"
```

### Integration Tests

Test component interactions:

```python
def test_full_paper_processing():
    """Test complete paper processing pipeline."""
    pmcid = "7181753"

    with patch('pmcgrab.fetch.get_xml') as mock_get_xml:
        mock_get_xml.return_value = load_fixture('sample_article.xml')

        paper = Paper.from_pmc(pmcid, email="test@example.com")

        assert paper.pmcid == f"PMC{pmcid}"
        assert paper.title is not None
        assert len(paper.authors) > 0
```

### End-to-End Tests

Test complete workflows:

```python
def test_cli_batch_processing(tmp_path):
    """Test CLI batch processing functionality."""
    # Create test input file
    input_file = tmp_path / "test_ids.txt"
    input_file.write_text("7181753\n3539614\n")

    # Run CLI command
    result = run_cli([
        "--input-file", str(input_file),
        "--output-dir", str(tmp_path),
        "--email", "test@example.com"
    ])

    assert result.exit_code == 0
    assert (tmp_path / "PMC7181753.json").exists()
    assert (tmp_path / "PMC3539614.json").exists()
```

## Test Fixtures

### Creating Test Data

```python
# conftest.py
@pytest.fixture
def sample_paper_xml():
    """Sample PMC article XML for testing."""
    return """
    <article>
        <front>
            <article-meta>
                <article-id pub-id-type="pmcid">PMC7181753</article-id>
                <title-group>
                    <article-title>Sample Article</article-title>
                </title-group>
            </article-meta>
        </front>
        <body>
            <sec sec-type="intro">
                <title>Introduction</title>
                <p>Sample introduction text.</p>
            </sec>
        </body>
    </article>
    """

@pytest.fixture
def mock_paper():
    """Mock Paper object for testing."""
    return Paper(
        pmcid="PMC7181753",
        title="Test Article",
        authors=[],
        abstract={},
        body={"Introduction": "Test content"},
        citations=[],
        tables=[],
        figures=[]
    )
```

### External Service Mocking

```python
@pytest.fixture
def mock_ncbi_response():
    """Mock NCBI API response."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = load_fixture('sample_article.xml')
        mock_get.return_value = mock_response
        yield mock_get

def test_article_fetching(mock_ncbi_response):
    """Test article fetching with mocked NCBI response."""
    xml_content = get_xml("7181753", email="test@example.com")
    assert xml_content is not None
    mock_ncbi_response.assert_called_once()
```

## Testing Best Practices

### Test Organization

```python
class TestPaperModel:
    """Test cases for Paper model."""

    def test_paper_creation(self):
        """Test basic paper creation."""
        pass

    def test_paper_serialization(self):
        """Test paper to JSON serialization."""
        pass

    def test_paper_validation(self):
        """Test paper data validation."""
        pass

class TestPaperParsing:
    """Test cases for paper parsing."""

    def test_metadata_parsing(self):
        """Test metadata extraction."""
        pass

    def test_content_parsing(self):
        """Test content extraction."""
        pass
```

### Parameterized Tests

```python
@pytest.mark.parametrize("pmcid,expected_title", [
    ("7181753", "COVID-19 Research Article"),
    ("3539614", "Machine Learning Study"),
    ("5454911", "Clinical Trial Results")
])
def test_multiple_articles(pmcid, expected_title):
    """Test processing multiple articles."""
    with patch('pmcgrab.fetch.get_xml') as mock_get_xml:
        mock_get_xml.return_value = create_mock_xml(expected_title)

        paper = Paper.from_pmc(pmcid, email="test@example.com")
        assert paper.title == expected_title
```

### Error Testing

```python
def test_invalid_pmcid():
    """Test handling of invalid PMC IDs."""
    with pytest.raises(ValueError, match="Invalid PMC ID"):
        Paper.from_pmc("invalid_id", email="test@example.com")

def test_network_error():
    """Test handling of network errors."""
    with patch('requests.get', side_effect=requests.ConnectionError):
        with pytest.raises(NetworkError):
            get_xml("7181753", email="test@example.com")
```

### Async Testing

```python
@pytest.mark.asyncio
async def test_async_processing():
    """Test asynchronous processing."""
    processor = AsyncProcessor(email="test@example.com")

    with patch.object(processor, 'process_single') as mock_process:
        mock_process.return_value = mock_paper()

        results = await processor.process_batch(["7181753", "3539614"])
        assert len(results) == 2
```

## Mock Strategies

### HTTP Mocking with Responses

```python
import responses

@responses.activate
def test_api_integration():
    """Test API integration with responses library."""
    responses.add(
        responses.GET,
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
        body=load_fixture('sample_article.xml'),
        status=200,
        content_type='application/xml'
    )

    xml_content = get_xml("7181753", email="test@example.com")
    assert xml_content is not None
```

### Database Mocking

```python
@pytest.fixture
def mock_database():
    """Mock database for testing."""
    with patch('pmcgrab.storage.DatabaseConnection') as mock_db:
        mock_db.return_value.execute.return_value = []
        yield mock_db

def test_database_operations(mock_database):
    """Test database operations."""
    storage = PaperStorage()
    storage.save_paper(mock_paper())

    mock_database.return_value.execute.assert_called_once()
```

## Continuous Integration

### GitHub Actions Configuration

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.10, 3.11, 3.12]

    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: uv sync --dev --all-groups

      - name: Run tests
        run: uv run pytest --cov=pmcgrab

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Test Markers

```python
# Mark slow tests
@pytest.mark.slow
def test_large_batch_processing():
    """Test processing large batches (slow)."""
    pass

# Mark integration tests
@pytest.mark.integration
def test_full_workflow():
    """Test complete workflow (integration)."""
    pass

# Mark performance tests
@pytest.mark.performance
def test_processing_speed():
    """Test processing performance."""
    pass
```

Run specific test categories:

```bash
# Skip slow tests
uv run pytest -m "not slow"

# Run only integration tests
uv run pytest -m integration

# Run performance tests
uv run pytest -m performance
```

## Debugging Tests

### Running Tests in Debug Mode

```bash
# Run with debugging
uv run pytest --pdb

# Run with debugging on first failure
uv run pytest --pdb -x

# Run with verbose output
uv run pytest -v -s
```

### Test Debugging Tips

1. **Use print statements** for quick debugging
2. **Set breakpoints** with `pytest --pdb`
3. **Isolate failing tests** with specific test selection
4. **Check test logs** for detailed error information
5. **Use mock.assert_called_with()** to verify interactions

## Performance Testing

### Benchmarking

```python
import time
import pytest

def test_parsing_performance():
    """Benchmark paper parsing performance."""
    xml_content = load_large_fixture('large_article.xml')

    start_time = time.time()
    paper = Paper.from_xml(xml_content, email="test@example.com")
    end_time = time.time()

    processing_time = end_time - start_time
    assert processing_time < 5.0  # Should complete within 5 seconds
    assert paper is not None
```

### Memory Testing

```python
import psutil
import os

def test_memory_usage():
    """Test memory usage during processing."""
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss

    # Process large batch
    results = process_large_batch(large_pmc_ids)

    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory

    # Memory increase should be reasonable
    assert memory_increase < 500 * 1024 * 1024  # Less than 500MB
```

This comprehensive testing framework ensures PMCGrab maintains high quality and reliability across all components and use cases.
