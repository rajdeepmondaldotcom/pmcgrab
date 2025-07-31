"""Command-line interface for PMCGrab batch processing and article retrieval.

This package provides the command-line interface (CLI) for PMCGrab, enabling
users to process PMC articles in batch mode with progress tracking, error
handling, and comprehensive output generation.

The CLI is designed for both interactive use and automated workflows, providing
a robust interface for large-scale PMC article processing with features like
parallel processing, retry logic, and detailed progress reporting.

CLI Features:
    * **Batch Processing**: Process multiple PMC IDs efficiently
    * **Parallel Execution**: Configurable thread pools for concurrent processing
    * **Progress Tracking**: Real-time progress bars with tqdm integration
    * **Error Handling**: Comprehensive error reporting and retry mechanisms
    * **Flexible Output**: Configurable output directories and file organization
    * **Legacy Support**: Backward compatibility with existing command formats

Key Components:
    * **pmcgrab_cli**: Main CLI implementation with argument parsing
    * **Progress Reporting**: Integration with tqdm for user feedback
    * **Error Management**: Robust handling of network and parsing failures
    * **Output Organization**: Structured file output with summary generation

Command-Line Interface:
    The CLI provides a simple but powerful interface for PMC processing:

    ```bash
    # Process single PMC article
    python -m pmcgrab PMC7181753

    # Batch process multiple articles
    python -m pmcgrab PMC7181753 PMC3539614 PMC5454911

    # Custom output directory and parallel workers
    python -m pmcgrab --output-dir ./results --workers 8 PMC7181753

    # Process from file with retry logic
    python -m pmcgrab --input-file pmc_ids.txt --max-retries 3
    ```

Processing Features:
    * **Concurrent Processing**: Configurable number of worker threads
    * **Chunked Processing**: Efficient handling of large ID lists
    * **Automatic Retry**: Built-in retry logic for failed articles
    * **Progress Reporting**: Real-time status updates and completion estimates
    * **Summary Generation**: Detailed processing reports and statistics

Output Management:
    * **Structured Output**: Organized file hierarchy for processed articles
    * **JSON Format**: Clean, structured output for downstream processing
    * **Error Logging**: Comprehensive logging of processing issues
    * **Summary Reports**: Batch processing statistics and success rates

Integration Points:
    * **Application Layer**: Uses core PMCGrab processing functions
    * **Infrastructure**: Leverages settings and configuration management
    * **Domain Models**: Operates on PMCGrab's core data structures
    * **Common Utilities**: Uses shared formatting and validation functions

Use Cases:
    * **Research Datasets**: Build large datasets of processed PMC articles
    * **Content Migration**: Migrate PMC content to structured formats
    * **Batch Analysis**: Process articles for bibliometric studies
    * **Data Pipeline**: Integrate PMC processing into larger workflows
    * **Quality Assurance**: Validate PMC processing across article collections

Example Integration:
    ```python
    from pmcgrab.cli.pmcgrab_cli import main

    # Programmatic CLI usage
    import sys
    sys.argv = ['pmcgrab', 'PMC7181753', '--output-dir', './output']
    main()
    ```

Note:
    The CLI is the primary user interface for PMCGrab and is designed to be
    both user-friendly for interactive use and robust for automated processing
    workflows. It provides comprehensive feedback and error handling for
    production use cases.
"""
