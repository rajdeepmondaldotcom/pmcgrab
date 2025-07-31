"""Application layer orchestrating PMCGrab's core business use cases.

This package implements PMCGrab's application layer, which orchestrates domain
models and common utilities to satisfy the primary use cases of PMC article
processing. The application layer serves as the bridge between pure business
logic and external infrastructure concerns.

The application layer follows clean architecture principles, depending on domain
and common modules while remaining independent of infrastructure details. This
design enables testable, maintainable business logic that can work with different
infrastructure implementations.

Architecture Principles:
    * **Dependency Inversion**: Depends on abstractions, not implementations
    * **Use Case Driven**: Organized around business use cases and workflows
    * **Infrastructure Independent**: No direct infrastructure dependencies
    * **Testable**: Pure business logic easy to test in isolation
    * **Composable**: Functions can be combined for complex workflows

Package Organization:
    * **processing**: Core article processing workflows and orchestration
    * **paper_builder**: High-level Paper object construction and validation
    * **parsing**: Domain-specific content extraction from PMC XML

Core Use Cases:
    * **Single Article Processing**: Convert PMC ID to structured Paper object
    * **Batch Processing**: Process multiple articles with error handling
    * **Content Extraction**: Parse and structure different types of article content
    * **Data Validation**: Ensure processed data meets quality standards
    * **Error Recovery**: Handle and recover from processing failures

Key Features:
    * **Paper Construction**: Build complete Paper objects from PMC data
    * **Content Parsing**: Extract and structure all article content types
    * **Reference Resolution**: Handle cross-references and document links
    * **Quality Assurance**: Validate processed data for completeness
    * **Error Handling**: Comprehensive error management and reporting

Design Patterns:
    * **Orchestration**: Coordinate multiple domain operations
    * **Factory Pattern**: Create complex domain objects from raw data
    * **Strategy Pattern**: Different processing strategies for different content
    * **Pipeline Pattern**: Sequential processing steps with validation
    * **Dependency Injection**: Infrastructure concerns injected from outside

Processing Workflow:
    ```python
    from pmcgrab.application.paper_builder import build_paper_from_pmc
    from pmcgrab.application.processing import process_single_pmc

    # High-level Paper construction
    paper = build_paper_from_pmc("PMC7181753")

    # Application-layer processing with error handling
    result = process_single_pmc("PMC7181753", output_dir="./output")
    ```

Integration Patterns:
    * **Domain Integration**: Uses domain models and value objects
    * **Common Utilities**: Leverages shared processing functions
    * **Infrastructure Injection**: Receives infrastructure services as parameters
    * **CLI Integration**: Provides functions used by command-line interface

Parsing Sub-Package:
    The parsing sub-package contains specialized content extraction functions
    organized by content type (metadata, contributors, sections, content).
    These functions work together to extract comprehensive article information.

Processing Sub-Package:
    Contains the core processing workflows that coordinate parsing, validation,
    and output generation. These functions implement the main use cases of
    PMCGrab for both single article and batch processing scenarios.

Quality Assurance:
    * **Comprehensive Testing**: Full test coverage for all use cases
    * **Error Scenarios**: Robust handling of various failure modes
    * **Data Validation**: Ensures output data meets quality standards
    * **Performance Optimization**: Efficient processing for large-scale use

Example Integration:
    ```python
    # Application layer orchestrates the full workflow
    from pmcgrab.application.processing import process_pmc_ids
    from pmcgrab.application.paper_builder import build_paper_from_pmc

    # Single article processing
    paper = build_paper_from_pmc("PMC7181753")
    print(f"Title: {paper.title}")
    print(f"Authors: {len(paper.authors)}")

    # Batch processing with error handling
    results = process_pmc_ids(["PMC7181753", "PMC3539614"], output_dir="./output")
    ```

Note:
    The application layer is the primary interface for PMCGrab's business
    functionality. It provides clean, testable functions that implement the
    core use cases while remaining independent of specific infrastructure
    implementations. This design enables flexibility in deployment and testing.
"""
