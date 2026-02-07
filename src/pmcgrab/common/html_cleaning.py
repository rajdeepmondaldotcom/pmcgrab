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


# Pre-compiled default patterns for strip_html_text_styling (avoids recompilation per call)
_DEFAULT_REMOVALS = ["<italic>", "<i>", "<bold>", "<b>", "<underline>", "<u>"]
_DEFAULT_REPLACEMENTS = {"<sub>": "_", "<sup>": "^", "<ext-link>": "[External URI:]"}
_DEFAULT_REMOVE_PATTERNS, _DEFAULT_REPLACE_PATTERNS = _compile_patterns(
    _DEFAULT_REMOVALS, _DEFAULT_REPLACEMENTS
)
_DEFAULT_COMBINED_REMOVE_RE = re.compile(
    "|".join(_DEFAULT_REMOVE_PATTERNS), re.IGNORECASE
)


def _build_single_pass_re(
    remove_patterns: list[str], replace_patterns: dict[str, str]
) -> tuple[re.Pattern, dict[str, str]]:
    """Build a single compiled regex that handles both removals and replacements.

    Returns a compiled pattern and a mapping from named groups to replacement
    strings.  Groups that have no entry in the mapping are removals (replaced
    with ``""``).
    """
    parts: list[str] = []
    group_map: dict[str, str] = {}

    for idx, pat in enumerate(remove_patterns):
        group_name = f"_rm{idx}"
        parts.append(f"(?P<{group_name}>{pat})")
        group_map[group_name] = ""

    for idx, (pat, rep) in enumerate(replace_patterns.items()):
        group_name = f"_rp{idx}"
        parts.append(f"(?P<{group_name}>{pat})")
        group_map[group_name] = rep

    combined = re.compile("|".join(parts), re.IGNORECASE)
    return combined, group_map


# Pre-build the single-pass regex for the default rules
_SINGLE_PASS_RE, _SINGLE_PASS_MAP = _build_single_pass_re(
    _DEFAULT_REMOVE_PATTERNS, _DEFAULT_REPLACE_PATTERNS
)


def _single_pass_replacer(match: re.Match) -> str:
    """Replacement callback for the single-pass regex."""
    for name, rep in _SINGLE_PASS_MAP.items():
        if match.group(name) is not None:
            return rep
    return ""


def strip_html_text_styling(
    text: str,
    replacements: dict[str, str] | None = None,
    *,
    verbose: bool = False,
) -> str:
    """Remove common text styling tags and convert special elements to plain text.

    Uses a single-pass compiled regex for maximum performance.

    Args:
        text: HTML/XML text to clean
        replacements: Additional or override replacements for default rules.
        verbose: If True, emit debug logging about tag processing

    Returns:
        str: Cleaned text with styling removed and special elements converted
    """
    if replacements:
        merged = dict(_DEFAULT_REPLACEMENTS)
        merged.update(replacements)
        return remove_html_tags(text, _DEFAULT_REMOVALS, merged, verbose=verbose)

    # Fast single-pass path using pre-compiled combined regex
    if verbose:
        logger.info("Using single-pass cleaning regex")

    return _SINGLE_PASS_RE.sub(_single_pass_replacer, text)
