"""HTML / XML tag removal and simplification utilities.

These helpers intentionally *do not* parse the document into a full DOM – they
operate via lightweight regex for speed and to avoid external library
dependencies for simple clean-ups.
"""

from __future__ import annotations

import re
from typing import Dict, List

from pmcgrab.constants import logger

__all__: list[str] = [
    "remove_html_tags",
    "strip_html_text_styling",
]


def _compile_patterns(removals: List[str], replaces: Dict[str, str]):
    # Closing tags corresponding to *removals* and *replaces*
    close_tags = [f"</{tag[1:]}" for tag in removals + list(replaces.keys())]
    to_remove = removals + close_tags

    patterns_to_remove = [f"{tag[:-1]}\\b[^>]*{tag[-1]}" for tag in to_remove]
    patterns_to_replace = {
        f"{tag[:-1]}\\b[^>]*{tag[-1]}": rep for tag, rep in replaces.items()
    }
    return patterns_to_remove, patterns_to_replace


def remove_html_tags(
    text: str,
    removals: List[str],
    replaces: Dict[str, str],
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
    patterns_to_remove, patterns_to_replace = _compile_patterns(removals, replaces)

    if verbose:
        logger.info("Removing tags: %s", patterns_to_remove)
        logger.info("Replacing tags: %s", patterns_to_replace)

    combined_remove_pattern = "|".join(patterns_to_remove)
    cleaned = re.sub(combined_remove_pattern, "", text, flags=re.IGNORECASE)

    for pattern, replacement in patterns_to_replace.items():
        cleaned = re.sub(pattern, replacement, cleaned)

    return cleaned


def strip_html_text_styling(text: str, *, verbose: bool = False) -> str:
    """Simplify emphasis tags and drop purely presentational markup."""
    removals = ["<italic>", "<i>", "<bold>", "<b>", "<underline>", "<u>"]
    replacements = {"<sub>": "_", "<sup>": "^", "<ext-link>": "[External URI:]"}
    return remove_html_tags(text, removals, replacements, verbose=verbose)
