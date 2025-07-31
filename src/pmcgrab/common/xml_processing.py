"""XML / HTML processing helpers that *do not* depend on lxml objects.

They work with raw strings so that they can be used before a full parse or for
lightweight post-processing.
"""

from __future__ import annotations

import re
from itertools import chain
from typing import Optional

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
    """Return *node*'s text **including** all child markup as a single string."""
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
    """Return the placeholder tag (upper-case for consistency with tests)."""
    return f"[MHTML::{tag_type.upper()}::{value}]"


def split_text_and_refs(
    tree_text: str | ET._Element,
    ref_map: BasicBiMap,
    *,
    element_id: Optional[str] = None,
    on_unknown: str = "keep",
) -> str:
    """Replace reference tags with internal placeholders and populate *ref_map*."""
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
    """Drop internal MHTML placeholder tags from *text*."""
    pat = r"\[MHTML::([^:\[\]]+)::([^:\[\]]+)\]|\[MHTML::([^:\[\]]+)\]"
    return re.sub(pat, "", text)
