"""Text section parsing for PMC article abstract and body content.

This module provides specialized functions for parsing the main textual content
of PMC articles: abstracts and body sections. It converts raw XML structures
into PMCGrab's structured text representation using TextSection and TextParagraph
objects that preserve semantic structure while enabling clean text extraction.

The module handles the hierarchical nature of scientific article structure,
including nested sections, cross-references, and various content types found
in scholarly publications.

Key Features:
    * **Structured Text Representation**: Converts XML to semantic text objects
    * **Reference Preservation**: Maintains cross-references during processing
    * **Hierarchical Structure**: Preserves section organization and nesting
    * **Warning System**: Alerts for unexpected content structures
    * **Clean Separation**: Separates abstract from body content appropriately

Processing Approach:
    * Identifies and processes section (`<sec>`) and paragraph (`<p>`) elements
    * Builds TextSection objects that maintain title and content relationships
    * Creates TextParagraph objects for standalone paragraph content
    * Handles cross-references through provided reference maps
    * Issues warnings for unexpected XML structures

Content Types Handled:
    * **Abstract Sections**: Structured abstracts with labeled sections
    * **Body Sections**: Main article content organized hierarchically
    * **Mixed Content**: Combinations of sections and standalone paragraphs
    * **Cross-References**: Internal references to figures, tables, citations

Functions:
    gather_abstract: Parse abstract into structured text elements
    gather_body: Parse article body into structured sections
    _collect_sections: Internal helper for building section collections
    _gather_sections: Internal helper with common section processing logic
"""

from __future__ import annotations

import warnings

import lxml.etree as ET

from pmcgrab.constants import (
    UnexpectedMultipleMatchWarning,
    UnexpectedZeroMatchWarning,
    UnhandledTextTagWarning,
)
from pmcgrab.domain.value_objects import BasicBiMap
from pmcgrab.model import TextParagraph, TextSection

__all__: list[str] = [
    "gather_abstract",
    "gather_body",
]


# ----------------------------------------------------------------------------
# Internal helpers (kept private)
# ----------------------------------------------------------------------------


def _collect_sections(
    parent: ET.Element, context: str, ref_map: BasicBiMap
) -> list[TextSection | TextParagraph]:
    """Build structured text element list from XML parent element.

    Internal helper function that processes child elements of a parent XML node,
    converting them into appropriate TextSection or TextParagraph objects.
    Handles the mixed content structure common in PMC articles.

    Args:
        parent: XML element containing section or paragraph children
        context: Context name for warning messages (e.g., "abstract", "body")
        ref_map: Reference map for cross-reference handling

    Returns:
        list[TextSection | TextParagraph]: List of structured text elements

    Processing Rules:
        * `<sec>` elements become TextSection objects with full hierarchy
        * `<p>` elements become TextParagraph objects
        * Unexpected elements trigger warnings but don't halt processing
        * All elements receive the same reference map for consistency

    Warnings:
        * UnhandledTextTagWarning: For unexpected XML tags in the structure

    Note:
        This function is the core converter from XML structure to PMCGrab's
        semantic text representation, enabling consistent text processing
        while preserving document structure and cross-references.
    """
    sections: list[TextSection | TextParagraph] = []
    for child in parent:
        if child.tag == "sec":
            sections.append(TextSection(child, ref_map=ref_map))
        elif child.tag == "p":
            sections.append(TextParagraph(child, ref_map=ref_map))
        else:
            warnings.warn(
                f"Unexpected tag {child.tag} in {context}.",
                UnhandledTextTagWarning,
                stacklevel=2,
            )
    return sections


def _gather_sections(
    root: ET.Element,
    *,
    xpath: str,
    missing_warning: str,
    context: str,
    ref_map: BasicBiMap,
) -> list[TextSection | TextParagraph] | None:
    """Generic section gathering with error handling and validation.

    Internal helper function that provides common logic for extracting
    section content from PMC XML. Handles validation, error reporting,
    and delegates to _collect_sections for actual processing.

    Args:
        root: Root XML element to search within
        xpath: XPath expression to locate target section
        missing_warning: Warning message for missing sections
        context: Context name for warning messages
        ref_map: Reference map for cross-reference handling

    Returns:
        list[TextSection | TextParagraph] | None: Structured text elements
                                                  or None if section not found

    Warnings:
        * UnexpectedZeroMatchWarning: When target section is not found
        * UnexpectedMultipleMatchWarning: When multiple target sections exist (uses first)

    Processing Flow:
        1. Search for target section using provided XPath
        2. Validate that exactly one section exists (with warnings for edge cases)
        3. Delegate to _collect_sections for content processing
        4. Return structured text elements or None

    Note:
        This function standardizes the section extraction process and provides
        consistent error handling across different section types (abstract, body).
    """
    nodes = root.xpath(xpath)
    if not nodes:
        warnings.warn(missing_warning, UnexpectedZeroMatchWarning, stacklevel=2)
        return None
    if len(nodes) > 1:
        warnings.warn(
            f"Multiple {context} tags found; using the first.",
            UnexpectedMultipleMatchWarning,
            stacklevel=2,
        )
    return _collect_sections(nodes[0], context, ref_map)


# ----------------------------------------------------------------------------
# Public gatherers
# ----------------------------------------------------------------------------


def gather_abstract(
    root: ET.Element, ref_map: BasicBiMap
) -> list[TextSection | TextParagraph] | None:
    """Extract and parse article abstract into structured text elements.

    Processes the PMC article abstract, which may be either a simple paragraph
    or a structured abstract with labeled sections (Background, Methods, Results,
    Conclusions, etc.). The function preserves the abstract's organization while
    enabling clean text extraction.

    Args:
        root: Root element of the PMC XML document
        ref_map: Reference map for handling cross-references within the abstract

    Returns:
        list[TextSection | TextParagraph] | None: List of structured abstract elements:
            - TextSection objects for structured abstract sections
            - TextParagraph objects for simple paragraph abstracts
            - None if no abstract is found

    Warnings:
        * UnexpectedZeroMatchWarning: When no abstract element is found
        * UnexpectedMultipleMatchWarning: When multiple abstracts exist (uses first)
        * UnhandledTextTagWarning: For unexpected XML tags within the abstract

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> ref_map = BasicBiMap()
        >>> abstract_elements = gather_abstract(root, ref_map)
        >>> if abstract_elements:
        ...     for element in abstract_elements:
        ...         if isinstance(element, TextSection):
        ...             print(f"Section: {element.title}")
        ...             print(f"Content: {element.get_section_text()[:100]}...")
        ...         elif isinstance(element, TextParagraph):
        ...             print(f"Paragraph: {str(element)[:100]}...")

    Abstract Types:
        * **Structured Abstracts**: Multiple labeled sections
            - Background/Objective
            - Methods/Design
            - Results/Findings
            - Conclusions/Significance
        * **Unstructured Abstracts**: Single paragraph or simple text
        * **Mixed Format**: Combination of sections and paragraphs

    Content Processing:
        * Preserves section hierarchy and titles
        * Maintains cross-references to figures, tables, citations
        * Handles formatting and emphasis markup
        * Provides clean text extraction while preserving structure

    Use Cases:
        * Abstract-based article classification and indexing
        * Content summarization and analysis
        * Search and recommendation systems
        * Citation context analysis

    Note:
        Abstracts are crucial for article discovery and initial assessment.
        The structured representation enables both human-readable formatting
        and machine processing for AI/ML applications.
    """
    return _gather_sections(
        root,
        xpath="//abstract",
        missing_warning="No abstract found.",
        context="abstract",
        ref_map=ref_map,
    )


def gather_body(
    root: ET.Element, ref_map: BasicBiMap
) -> list[TextSection | TextParagraph] | None:
    """Extract and parse article body content into structured sections.

    Processes the main content of the PMC article, organizing it into a
    hierarchical structure of sections and paragraphs. This captures the
    logical organization of scientific articles while preserving all
    cross-references and structural information.

    Args:
        root: Root element of the PMC XML document
        ref_map: Reference map for handling cross-references throughout the body

    Returns:
        list[TextSection | TextParagraph] | None: List of structured body elements:
            - TextSection objects for major sections (Introduction, Methods, etc.)
            - TextParagraph objects for standalone paragraphs
            - None if no body content is found

    Warnings:
        * UnexpectedZeroMatchWarning: When no body element is found
        * UnexpectedMultipleMatchWarning: When multiple body elements exist (uses first)
        * UnhandledTextTagWarning: For unexpected XML tags within the body

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> ref_map = BasicBiMap()
        >>> body_elements = gather_body(root, ref_map)
        >>> if body_elements:
        ...     for element in body_elements:
        ...         if isinstance(element, TextSection):
        ...             print(f"Section: {element.title}")
        ...             print(f"Content length: {len(element.get_section_text())}")
        ...         elif isinstance(element, TextParagraph):
        ...             print(f"Standalone paragraph: {str(element)[:50]}...")

    Common Section Structure:
        * **Introduction**: Background and motivation
        * **Methods/Materials**: Experimental procedures and setup
        * **Results**: Findings and analysis
        * **Discussion**: Interpretation and implications
        * **Conclusion**: Summary and future work
        * **Additional**: Acknowledgments, supplementary information

    Content Features:
        * Hierarchical section nesting (sections within sections)
        * Cross-references to figures, tables, equations, and citations
        * Mathematical expressions and scientific notation
        * Structured lists and formatted content
        * Links to supplementary materials

    Processing Benefits:
        * Maintains semantic structure for AI/ML processing
        * Enables section-specific analysis and extraction
        * Preserves scientific article organization
        * Supports both full-text and section-based search

    Use Cases:
        * Full-text indexing and search
        * Section-specific content analysis
        * Citation context extraction
        * Research methodology analysis
        * Results and findings extraction

    Note:
        The body content represents the core scholarly contribution and
        is essential for comprehensive article analysis. The structured
        representation enables sophisticated content processing while
        maintaining readability and scientific context.
    """
    return _gather_sections(
        root,
        xpath="//body",
        missing_warning="No <body> tag found.",
        context="body",
        ref_map=ref_map,
    )
