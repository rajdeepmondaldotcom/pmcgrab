"""Reusable utility functions for text processing, serialization, and XML handling.

This package provides a collection of pure utility functions that support
PMCGrab's core processing pipeline. These functions are designed to be reusable
across different layers of the application while maintaining no external
dependencies or side effects.

The common utilities fill the gap between domain logic and infrastructure
concerns, providing specialized functions for text processing, data serialization,
and XML manipulation that are essential for PMC article processing.

Package Design:
    * **Pure Functions**: No side effects, predictable behavior
    * **No I/O Dependencies**: Self-contained processing functions
    * **Cross-Layer Reusability**: Used by application and infrastructure layers
    * **Focused Modules**: Small, single-purpose modules for specific tasks
    * **High Performance**: Optimized for large-scale article processing

Module Organization:
    * **serialization**: Data normalization and JSON serialization helpers
    * **html_cleaning**: Safe HTML/XML tag removal and text cleaning
    * **xml_processing**: Specialized XML text extraction and reference handling

Key Capabilities:
    * **Text Cleaning**: Remove or transform HTML/XML markup safely
    * **Data Normalization**: Convert complex objects to JSON-serializable formats
    * **Reference Processing**: Handle cross-references in scientific documents
    * **Content Extraction**: Extract clean text while preserving structure
    * **Tag Management**: Process custom internal markup (MHTML tags)

Serialization Module:
    Functions for converting complex Python objects to clean, JSON-serializable
    formats suitable for storage and transmission:

    * `normalize_value()`: Convert various data types to JSON-compatible formats
    * `clean_doc()`: Clean and normalize documentation strings

HTML Cleaning Module:
    Safe and efficient HTML/XML tag processing for scientific content:

    * `remove_html_tags()`: Remove or replace HTML/XML tags with custom rules
    * `strip_html_text_styling()`: Remove text formatting while preserving content

XML Processing Module:
    Specialized functions for PMC XML content processing:

    * `stringify_children()`: Extract text content from XML elements
    * `split_text_and_refs()`: Separate text from cross-references
    * `generate_typed_mhtml_tag()`: Create internal markup tags
    * `remove_mhtml_tags()`: Clean internal markup from processed text

Common Usage Patterns:
    ```python
    from pmcgrab.common import remove_html_tags, normalize_value, split_text_and_refs

    # Clean HTML content
    clean_text = remove_html_tags(raw_html, removals=["<i>", "<b>"])

    # Normalize data for JSON serialization
    json_data = normalize_value(complex_python_object)

    # Process XML with cross-references
    clean_text = split_text_and_refs(xml_element, ref_map)
    ```

Performance Characteristics:
    * **Regex-Based Processing**: Fast text processing without DOM parsing overhead
    * **Memory Efficient**: Streaming-style processing for large documents
    * **Scalable**: Optimized for batch processing of thousands of articles
    * **Cache-Friendly**: Predictable memory access patterns

Integration Points:
    * **Application Layer**: Uses utilities for content processing
    * **Infrastructure Layer**: Uses serialization for data persistence
    * **Domain Layer**: Can use utilities for value object processing
    * **Test Suites**: Extensively tested utility functions

Quality Assurance:
    * **Comprehensive Testing**: Full test coverage for all utility functions
    * **Error Handling**: Graceful handling of edge cases and malformed input
    * **Type Safety**: Full type annotations for reliable integration
    * **Documentation**: Detailed docstrings with examples and use cases

Note:
    These utilities represent the shared foundation for PMCGrab's text processing
    capabilities. They are designed to be reliable, efficient, and easy to use
    across different contexts within the PMCGrab ecosystem.
"""

from pmcgrab.common.html_cleaning import remove_html_tags, strip_html_text_styling
from pmcgrab.common.serialization import clean_doc, normalize_value
from pmcgrab.common.xml_processing import (
    generate_typed_mhtml_tag,
    remove_mhtml_tags,
    split_text_and_refs,
    stringify_children,
)

__all__: list[str] = [
    "clean_doc",
    "generate_typed_mhtml_tag",
    "normalize_value",
    "remove_html_tags",
    "remove_mhtml_tags",
    "split_text_and_refs",
    "stringify_children",
    "strip_html_text_styling",
]
