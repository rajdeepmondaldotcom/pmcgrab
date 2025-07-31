"""XML/HTML processing utilities for text extraction and reference handling.

This module provides specialized XML processing utilities that work with both
parsed XML elements and raw string content. These functions are designed to
support the specific needs of PMC article processing, particularly around
text extraction, reference handling, and markup normalization.

Unlike full DOM-based processing, these utilities focus on specific tasks:
* Extracting complete text content from XML elements
* Processing and normalizing cross-references and citations
* Managing internal placeholder tags for deferred processing
* Cleaning up specialized markup patterns

Key Features:
    * Works with both lxml.etree elements and raw strings
    * Specialized reference extraction and placeholder generation
    * Cross-reference mapping for document structure preservation
    * Lightweight text processing without full DOM overhead
    * Integration with HTML cleaning utilities

Use Cases:
    * Extracting text from PMC XML sections while preserving references
    * Processing cross-references and citations in scientific articles
    * Converting structured XML content to clean text for AI/ML processing
    * Managing complex document structures with internal references

Functions:
    stringify_children: Extract complete text content from XML elements
    split_text_and_refs: Process text and extract cross-references
    generate_typed_mhtml_tag: Create internal placeholder tags
    remove_mhtml_tags: Clean up internal placeholder tags
"""

from __future__ import annotations

import re
from itertools import chain

import lxml.etree as ET

from pmcgrab.common.html_cleaning import strip_html_text_styling
from pmcgrab.constants import logger
from pmcgrab.domain.value_objects import BasicBiMap

__all__: list[str] = [
    "generate_typed_mhtml_tag",
    "remove_mhtml_tags",
    "split_text_and_refs",
    "stringify_children",
]


def stringify_children(node: ET.Element, *, encoding: str = "utf-8") -> str:
    """Extract complete text content from XML element including all child markup.

    Recursively extracts all text content from an XML element, including text
    from child elements and their tails. This function preserves the complete
    textual content while maintaining the original markup structure as a string.

    Args:
        node: XML element to extract text from
        encoding: Character encoding for byte string conversion (default: "utf-8")

    Returns:
        str: Complete text content including child element markup as a single string

    Examples:
        >>> # Simple element with children
        >>> xml = '<p>Hello <b>world</b> from <i>Python</i>!</p>'
        >>> element = ET.fromstring(xml)
        >>> text = stringify_children(element)
        >>> print(text)  # "Hello <b>world</b> from <i>Python</i>!"
        >>>
        >>> # Complex nested structure
        >>> xml = '<section><title>Methods</title><p>See <xref>Fig 1</xref></p></section>'
        >>> element = ET.fromstring(xml)
        >>> content = stringify_children(element)
        >>> print(content)  # "<title>Methods</title><p>See <xref>Fig 1</xref></p>"

    Behavior:
        * Includes the element's direct text content
        * Recursively includes all child elements as markup strings
        * Includes tail text that follows each child element
        * Preserves original XML structure and formatting
        * Strips leading/trailing whitespace from final result

    Use Cases:
        * Extracting section content while preserving internal structure
        * Getting complete markup for further processing
        * Converting XML elements to string format for regex processing
        * Preserving cross-references and internal links during text extraction

    Note:
        This function is particularly useful when you need to process the complete
        content of an XML element while maintaining its internal structure for
        subsequent reference extraction or markup processing.
    """
    chunks = [
        c
        for c in chain(
            (node.text,),
            chain(
                *((ET.tostring(child, with_tail=False), child.tail) for child in node)
            ),
            (node.tail,),
        )
        if c
    ]
    decoded = [c.decode(encoding) if isinstance(c, bytes) else c for c in chunks]
    return "".join(decoded).strip()


_ALLOWED_TAGS = {"xref", "fig", "table-wrap"}
_TAG_PATTERN = re.compile(
    r"<([a-zA-Z][\w-]*)\b[^>]*>(.*?)</\1>|<([a-zA-Z][\w-]*)\b[^/>]*/?>",
    re.DOTALL,
)


def generate_typed_mhtml_tag(tag_type: str, value: str) -> str:
    """Generate internal placeholder tag for deferred processing.

    Creates standardized placeholder tags used internally by PMCGrab to mark
    locations where complex elements (like cross-references, figures, tables)
    should be processed later. These tags allow text processing to proceed
    while preserving the ability to reconstruct the original structure.

    Args:
        tag_type: Type of placeholder (e.g., "dataref", "figure", "table")
        value: Value or identifier for the placeholder

    Returns:
        str: Formatted placeholder tag in format [MHTML::TYPE::VALUE]

    Examples:
        >>> # Generate reference placeholder
        >>> tag = generate_typed_mhtml_tag("dataref", "5")
        >>> print(tag)  # "[MHTML::DATAREF::5]"
        >>>
        >>> # Generate figure placeholder
        >>> tag = generate_typed_mhtml_tag("figure", "fig1")
        >>> print(tag)  # "[MHTML::FIGURE::FIG1]"

    Format:
        The generated tags follow the pattern: [MHTML::TYPE::VALUE]
        - TYPE is always converted to uppercase for consistency
        - VALUE is preserved as provided
        - Brackets and double colons are literal separators

    Use Cases:
        * Marking cross-reference locations during text processing
        * Preserving figure and table references in extracted text
        * Creating placeholders for complex elements requiring special handling
        * Enabling two-phase processing: text extraction then element reconstruction

    Note:
        These placeholder tags are designed to be easily identifiable and
        processed by regex patterns while being unlikely to conflict with
        natural text content in scientific articles.
    """
    return f"[MHTML::{tag_type.upper()}::{value}]"


def split_text_and_refs(
    tree_text: str | ET._Element,
    ref_map: BasicBiMap,
    *,
    element_id: str | None = None,
    on_unknown: str = "keep",
) -> str:
    """Extract text content while processing cross-references and creating placeholders.

    Core function for processing PMC XML content that contains cross-references,
    citations, and other internal links. Extracts clean text while building a
    mapping of references and replacing them with standardized placeholders for
    later processing.

    Args:
        tree_text: XML element or string containing text with references
        ref_map: Bidirectional map to store reference mappings
        element_id: Optional identifier for debugging/logging purposes
        on_unknown: How to handle unrecognized tags:
                   - "keep": Include tag content in output (default)
                   - Other values: Remove tag content

    Returns:
        str: Processed text with references replaced by placeholder tags

    Processing Rules:
        Allowed tags (processed as references):
            * <xref>: Cross-references - content included, reference mapped
            * <fig>: Figure references - processed as placeholders
            * <table-wrap>: Table references - processed as placeholders

        Unknown tags:
            * Content handling determined by on_unknown parameter
            * Logged for debugging when element_id provided

    Examples:
        >>> # Process text with cross-references
        >>> text = "See <xref ref-type='fig' rid='fig1'>Figure 1</xref> for details"
        >>> ref_map = BasicBiMap()
        >>> result = split_text_and_refs(text, ref_map)
        >>> print(result)  # "See Figure 1[MHTML::DATAREF::0] for details"
        >>> print(ref_map[0])  # Original xref tag
        >>>
        >>> # Process XML element
        >>> xml = '<p>Results shown in <fig id="F1">Figure 1</fig></p>'
        >>> element = ET.fromstring(xml)
        >>> ref_map = BasicBiMap()
        >>> result = split_text_and_refs(element, ref_map)
        >>> print(result)  # "Results shown in [MHTML::DATAREF::0]"

    Reference Mapping:
        * Each unique reference tag gets a numeric identifier
        * ref_map stores bidirectional mapping: number ↔ original tag
        * Same tag appearing multiple times reuses the same number
        * Placeholders use format [MHTML::DATAREF::number]

    Text Processing:
        * HTML text styling is stripped using strip_html_text_styling()
        * Element text content is extracted using stringify_children()
        * Leading/trailing whitespace is normalized

    Use Cases:
        * Processing PMC article sections with internal references
        * Extracting clean text while preserving document structure
        * Building reference maps for later reconstruction
        * Converting structured content to AI/ML-ready text format

    Note:
        This function is central to PMCGrab's approach of separating text
        extraction from reference processing, enabling clean text output
        while maintaining the ability to reconstruct document structure.
    """
    if isinstance(tree_text, ET._Element):
        text = stringify_children(tree_text)
    else:
        text = str(tree_text)
    text = text.strip()
    text = strip_html_text_styling(text)

    cleaned: list[str] = []
    while text:
        match = _TAG_PATTERN.search(text)
        if not match:
            cleaned.append(text)
            break

        tag_name = match.group(1) or match.group(3)
        tag_contents = match.group(2) or ""
        full_tag = match.group()

        cleaned.append(text[: match.start()])

        if tag_name not in _ALLOWED_TAGS:
            logger.debug(
                "Encountered disallowed tag '%s' in element %s", tag_name, element_id
            )
            if on_unknown == "keep":
                cleaned.append(tag_contents)
            text = text[match.end() :]
            continue

        # Allowed tags -----------------------------------------------------
        if tag_name == "xref":
            cleaned.append(tag_contents)  # Inline citation text

        if full_tag in ref_map.reverse:
            ref_num = ref_map.reverse[full_tag]
        else:
            ref_num = len(ref_map)
            ref_map[ref_num] = full_tag

        cleaned.append(generate_typed_mhtml_tag("dataref", str(ref_num)))
        text = text[match.end() :]

    return "".join(cleaned)


def remove_mhtml_tags(text: str) -> str:
    """Remove all internal MHTML placeholder tags from text.

    Strips all PMCGrab internal placeholder tags from text, leaving only the
    clean content. This function is typically used in the final processing
    stage when placeholder tags are no longer needed.

    Args:
        text: Text containing MHTML placeholder tags to remove

    Returns:
        str: Clean text with all placeholder tags removed

    Examples:
        >>> # Remove reference placeholders
        >>> text = "See Figure 1[MHTML::DATAREF::0] for details[MHTML::DATAREF::1]"
        >>> clean = remove_mhtml_tags(text)
        >>> print(clean)  # "See Figure 1 for details"
        >>>
        >>> # Remove various placeholder types
        >>> text = "Results[MHTML::FIGURE::F1] show[MHTML::TABLE::T1] improvement"
        >>> clean = remove_mhtml_tags(text)
        >>> print(clean)  # "Results show improvement"
        >>>
        >>> # Handle mixed content
        >>> text = "Normal text[MHTML::DATAREF::5] and more[MHTML::OTHER] content"
        >>> clean = remove_mhtml_tags(text)
        >>> print(clean)  # "Normal text and more content"

    Supported Tag Formats:
        * [MHTML::TYPE::VALUE] - Full format with type and value
        * [MHTML::TYPE] - Short format with type only
        * Case-insensitive type matching
        * Any characters allowed in type and value (except :, [, ])

    Use Cases:
        * Final text cleaning after reference processing is complete
        * Converting processed text to plain format for display
        * Removing all internal markup for AI/ML processing
        * Generating clean text output for end users

    Pattern Matching:
        The function uses regex to match both full and abbreviated placeholder
        formats, ensuring all internal tags are removed regardless of their
        specific type or content.

    Note:
        This function removes ALL MHTML placeholder tags, regardless of type.
        If you need selective removal, process the placeholders individually
        before using this function for final cleanup.
    """
    pat = r"\[MHTML::([^:\[\]]+)::([^:\[\]]+)\]|\[MHTML::([^:\[\]]+)\]"
    return re.sub(pat, "", text)
