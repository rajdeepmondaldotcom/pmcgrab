"""HTML/XML tag removal and text simplification utilities.

This module provides lightweight HTML and XML tag cleaning utilities optimized
for speed and minimal dependencies. Rather than parsing documents into full DOM
structures, these functions use regex-based approaches for efficient text
cleaning operations commonly needed when processing scientific articles.

The utilities are particularly useful for:
* Cleaning PMC XML content for text analysis
* Removing formatting tags while preserving content structure
* Converting styled text to plain text for AI/ML processing
* Normalizing markup from different sources

Key Features:
    * Regex-based processing for speed and low memory usage
    * Selective tag removal with customizable rules
    * Tag replacement with alternative representations
    * Verbose mode for debugging tag processing
    * No external DOM library dependencies

Design Philosophy:
    These functions prioritize speed and simplicity over comprehensive HTML parsing.
    They are designed for cleaning scientific article content where perfect HTML
    compliance is less important than fast, reliable text extraction.

Functions:
    remove_html_tags: Core tag removal and replacement engine
    strip_html_text_styling: Specialized function for common text styling cleanup
    _compile_patterns: Internal pattern compilation helper
"""

from __future__ import annotations

import re

from pmcgrab.constants import logger

__all__: list[str] = [
    "remove_html_tags",
    "strip_html_text_styling",
]


def _compile_patterns(removals: list[str], replaces: dict[str, str]):
    """Compile tag lists into regex patterns for removal and replacement.

    Internal helper function that converts user-specified tag lists into
    optimized regex patterns. Handles both opening and closing tag variants
    and creates patterns that match tags with attributes.

    Args:
        removals: List of tags to remove completely (e.g., ["<i>", "<b>"])
        replaces: Dictionary mapping tags to replacement strings

    Returns:
        tuple: (patterns_to_remove, patterns_to_replace) where:
            - patterns_to_remove: List of regex patterns for tags to remove
            - patterns_to_replace: Dict mapping regex patterns to replacements

    Note:
        For replacement tags, both opening and closing tags are handled.
        For example, "<b>" becomes patterns for both "<b...>" and "</b>".
        This ensures proper replacement of complete tag pairs.
    """
    # Closing tags corresponding to *removals* only – replacement tags are handled separately
    close_tags = [f"</{tag[1:]}" for tag in removals]
    to_remove = removals + close_tags

    patterns_to_remove = [f"{tag[:-1]}\\b[^>]*{tag[-1]}" for tag in to_remove]
    # For replacements – create patterns for both opening and matching closing tag
    patterns_to_replace = {}
    for tag, rep in replaces.items():
        open_pat = f"{tag[:-1]}\\b[^>]*{tag[-1]}"
        close_pat = f"</{tag[1:-1]}\\b[^>]*>"
        patterns_to_replace[open_pat] = rep
        patterns_to_replace[close_pat] = rep
    return patterns_to_remove, patterns_to_replace


def remove_html_tags(
    text: str,
    removals: list[str] | None = None,
    replaces: dict[str, str] | None = None,
    *,
    verbose: bool = False,
) -> str:
    """Remove or replace HTML/XML tags in text with customizable rules.

    Core function for cleaning HTML and XML markup from text. Provides flexible
    control over which tags to remove completely and which to replace with
    alternative representations. Uses efficient regex processing for speed.

    Args:
        text: Raw HTML/XML string to clean
        removals: List of tags to remove entirely (e.g., ["<i>", "<b>", "<em>"]).
                 Both opening and closing forms are automatically handled.
        replaces: Dictionary mapping opening tags to replacement text.
                 Example: {"<sub>": "_", "<sup>": "^", "<ext-link>": "[Link:] "}
                 Closing tags are automatically handled.
        verbose: If True, emit debug logging about tag processing

    Returns:
        str: Cleaned text with specified tags removed or replaced

    Behavior:
        * If neither removals nor replaces are specified, removes ALL HTML/XML tags
        * Tags in removals are completely removed (both opening and closing)
        * Tags in replaces have both opening and closing forms replaced
        * Tag attributes are handled automatically (e.g., <b class="bold"> matches)
        * Processing is case-insensitive for tag matching

    Examples:
        >>> # Remove all HTML tags
        >>> clean_text = remove_html_tags("<p>Hello <b>world</b></p>")
        >>> print(clean_text)  # "Hello world"
        >>>
        >>> # Remove specific tags only
        >>> text = "<p>Text with <i>italics</i> and <b>bold</b></p>"
        >>> clean = remove_html_tags(text, removals=["<i>", "<b>"])
        >>> print(clean)  # "<p>Text with italics and bold</p>"
        >>>
        >>> # Replace tags with alternatives
        >>> text = "H<sub>2</sub>O and E=mc<sup>2</sup>"
        >>> clean = remove_html_tags(text, replaces={"<sub>": "_", "<sup>": "^"})
        >>> print(clean)  # "H_2_O and E=mc^2^"
        >>>
        >>> # Combined removal and replacement
        >>> text = "<p><b>Bold</b> text with H<sub>2</sub>O</p>"
        >>> clean = remove_html_tags(
        ...     text,
        ...     removals=["<p>", "<b>"],
        ...     replaces={"<sub>": "_"}
        ... )
        >>> print(clean)  # "Bold text with H_2_O"

    Performance Notes:
        * Uses compiled regex patterns for efficient processing
        * Single-pass processing for removals, separate pass for replacements
        * Optimized for common HTML/XML cleaning tasks in scientific text
        * No DOM parsing overhead - direct string manipulation

    Common Use Cases:
        * Cleaning PMC XML for text analysis
        * Converting scientific notation (subscripts/superscripts)
        * Removing formatting while preserving content
        * Preparing text for AI/ML processing

    Note:
        This function uses regex-based processing rather than full HTML parsing.
        It's designed for speed and common use cases rather than perfect HTML
        compliance. For complex HTML documents, consider using dedicated HTML
        parsing libraries.
    """
    # If the caller didn't specify any tag lists, perform a *blanket* removal
    # of all HTML/XML markup.
    if removals is None and replaces is None:
        return re.sub(r"<[^>]+>", "", text)

    removals = removals or []
    replaces = replaces or {}

    patterns_to_remove, patterns_to_replace = _compile_patterns(removals, replaces)

    if verbose:
        logger.info("Removing tags: %s", patterns_to_remove)
        logger.info("Replacing tags: %s", patterns_to_replace)

    combined_remove_pattern = "|".join(patterns_to_remove)
    cleaned = re.sub(combined_remove_pattern, "", text, flags=re.IGNORECASE)

    for pattern, replacement in patterns_to_replace.items():
        cleaned = re.sub(pattern, replacement, cleaned)

    return cleaned


def strip_html_text_styling(
    text: str,
    replacements: dict[str, str] | None = None,
    *,
    verbose: bool = False,
) -> str:
    """Remove common text styling tags and convert special elements to plain text.

    Convenience function that applies common HTML/XML cleaning rules optimized
    for scientific article text. Removes visual formatting tags while converting
    structural elements like subscripts and external links to readable alternatives.

    Args:
        text: HTML/XML text to clean
        replacements: Additional or override replacements for default rules.
                     These will be merged with (and override) the default replacements.
        verbose: If True, emit debug logging about tag processing

    Returns:
        str: Cleaned text with styling removed and special elements converted

    Default Processing Rules:
        Removed tags (styling only):
            * <italic>, <i>: Italic formatting
            * <bold>, <b>: Bold formatting
            * <underline>, <u>: Underline formatting

        Converted tags (structural meaning preserved):
            * <sub>content</sub> → _content_: Subscripts
            * <sup>content</sup> → ^content^: Superscripts
            * <ext-link>URL</ext-link> → [External URI:]URL: External links

    Examples:
        >>> # Basic styling removal
        >>> text = "<b>Important:</b> H<sub>2</sub>O is <i>water</i>"
        >>> clean = strip_html_text_styling(text)
        >>> print(clean)  # "Important: H_2_O is water"
        >>>
        >>> # Custom replacements
        >>> text = "See <ext-link>example.com</ext-link> for details"
        >>> clean = strip_html_text_styling(text, {"<ext-link>": "[Link] "})
        >>> print(clean)  # "See [Link] example.com for details"
        >>>
        >>> # Scientific notation handling
        >>> text = "CO<sub>2</sub> + H<sub>2</sub>O → H<sub>2</sub>CO<sub>3</sub>"
        >>> clean = strip_html_text_styling(text)
        >>> print(clean)  # "CO_2_ + H_2_O → H_2_CO_3_"

    Use Cases:
        * Cleaning PMC article abstracts and bodies for text analysis
        * Preparing scientific text for AI/ML processing
        * Converting formatted text to plain text while preserving meaning
        * Normalizing text from different XML sources

    Customization:
        Override or extend default replacements by providing a replacements dict:

        >>> custom_rules = {"<ext-link>": "[See: ", "<sub>": "_{", "<sup>": "^{"}
        >>> clean = strip_html_text_styling(text, custom_rules)

    Note:
        This function is specifically designed for scientific article content
        where subscripts, superscripts, and external links are common. The
        default replacement patterns maintain readability while removing markup.
    """
    removals = ["<italic>", "<i>", "<bold>", "<b>", "<underline>", "<u>"]
    default_replacements = {"<sub>": "_", "<sup>": "^", "<ext-link>": "[External URI:]"}
    if replacements:
        default_replacements.update(replacements)
    return remove_html_tags(text, removals, default_replacements, verbose=verbose)
