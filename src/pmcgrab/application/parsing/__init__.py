"""Specialized PMC XML parsing modules for comprehensive content extraction.

This package provides focused, domain-specific parsing functions organized into
cohesive sub-modules that handle different aspects of PMC article processing.
Each module contains pure functions designed for reliable extraction of specific
content types from PMC XML documents.

The parsing modules are designed with separation of concerns, where each module
handles a specific domain of content extraction. This modular approach enables
selective usage, easier testing, and cleaner maintenance of parsing logic.

Module Organization:
    * **content**: Specialized content extraction (permissions, funding, equations, etc.)
    * **contributors**: Author and contributor information parsing with affiliations
    * **metadata**: Core bibliographic metadata extraction (titles, dates, identifiers)
    * **sections**: Text section parsing for abstracts and body content

Design Principles:
    * Pure functions with no side effects for predictable behavior
    * Comprehensive error handling with informative warnings
    * Structured output optimized for downstream processing
    * Consistent interfaces across all parsing modules
    * Full preservation of cross-references and document structure

Key Features:
    * **Specialized Extraction**: Each module focuses on specific content domains
    * **Cross-Reference Handling**: Maintains document links and references
    * **Warning System**: Comprehensive feedback on data quality issues
    * **Structured Output**: JSON-serializable data structures for all content
    * **Extensible Architecture**: Easy to add new parsing capabilities

Common Use Cases:
    * Research article analysis and indexing
    * Bibliographic database construction
    * Content migration and transformation
    * AI/ML dataset preparation
    * Citation and reference analysis

Integration Pattern:
    All parsing modules work together through shared infrastructure:
    * Reference maps for cross-reference resolution
    * Consistent warning and error handling
    * Standardized return types and data structures
    * Compatible with PMCGrab's main processing pipeline

Example Usage:
    ```python
    from pmcgrab.application.parsing import metadata, content, contributors, sections
    from pmcgrab.domain.value_objects import BasicBiMap

    # Parse different aspects of an article
    root = ET.fromstring(pmc_xml)
    ref_map = BasicBiMap()

    title = metadata.gather_title(root)
    authors = contributors.gather_authors(root)
    abstract = sections.gather_abstract(root, ref_map)
    funding = content.gather_funding(root)
    ```

Note:
    This package is part of PMCGrab's application layer and depends on domain
    models and common utilities. The parsing functions are designed to be used
    together but can also be used independently for specific extraction needs.
"""
