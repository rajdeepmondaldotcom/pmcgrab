"""HTML / XML tag removal and simplification utilities.

These helpers intentionally *do not* parse the document into a full DOM – they
operate via lightweight regex for speed and to avoid external library
dependencies for simple clean-ups.
"""

from __future__ import annotations

import re

from pmcgrab.constants import logger

__all__: list[str] = [
    "remove_html_tags",
    "strip_html_text_styling",
]


def _compile_patterns(removals: list[str], replaces: dict[str, str]):
    """Return (patterns_to_remove, patterns_to_replace) compiled from user input.

    For *replaces* we need to substitute **both** the opening **and** the matching
    closing tag so that wrappers like ``<b>bold</b>`` become ``**bold**`` (or any
    other replacement string) instead of losing the closing marker.
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
    """Remove or replace selected tags from *text*.

    Parameters
    ----------
    text : str
        Raw HTML / XML string.
    removals : list[str]
        Tags to be removed entirely (opening + closing forms).
    replaces : dict[str, str]
        Mapping ``tag → replacement_text`` where tag is specified in its *opening*
        form (e.g. ``"<sub>"``). The closing tag is automatically handled.
    verbose : bool, default False
        If *True*, debug-level messages are emitted via the shared *logger*.
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
    """Simplify emphasis tags and drop purely presentational markup."""
    removals = ["<italic>", "<i>", "<bold>", "<b>", "<underline>", "<u>"]
    default_replacements = {"<sub>": "_", "<sup>": "^", "<ext-link>": "[External URI:]"}
    if replacements:
        default_replacements.update(replacements)
    return remove_html_tags(text, removals, default_replacements, verbose=verbose)
