from __future__ import annotations

"""Abstract / body text section parsing helpers."""

import warnings
from typing import List, Optional, Union

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
) -> List[Union[TextSection, TextParagraph]]:
    """Build list of `TextSection`/`TextParagraph` from *parent* element."""
    sections: List[Union[TextSection, TextParagraph]] = []
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
) -> Optional[List[Union[TextSection, TextParagraph]]]:
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
) -> Optional[List[Union[TextSection, TextParagraph]]]:
    """Parse the `<abstract>` element into structured text elements."""
    return _gather_sections(
        root,
        xpath="//abstract",
        missing_warning="No abstract found.",
        context="abstract",
        ref_map=ref_map,
    )


def gather_body(
    root: ET.Element, ref_map: BasicBiMap
) -> Optional[List[Union[TextSection, TextParagraph]]]:
    """Parse the `<body>` element into structured sections."""
    return _gather_sections(
        root,
        xpath="//body",
        missing_warning="No <body> tag found.",
        context="body",
        ref_map=ref_map,
    )
