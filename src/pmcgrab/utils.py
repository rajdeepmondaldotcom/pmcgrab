import datetime
import re
import warnings
from inspect import cleandoc
from itertools import chain
from typing import Optional

import lxml.etree as ET
import pandas as pd

from pmcgrab.constants import (
    ReversedBiMapComparisonWarning,
    UnexpectedTagWarning,
    logger,
)


def clean_doc(s: str) -> str:
    """Collapse indentation and remove newlines from ``s``."""
    return cleandoc(s).replace("\n", "")


def make_hashable(value):
    """Convert nested lists/dicts to tuples so they can be hashed."""
    if isinstance(value, dict):
        return tuple(sorted((k, make_hashable(v)) for k, v in value.items()))
    if isinstance(value, list):
        return tuple(make_hashable(item) for item in value)
    return value


def normalize_value(val):
    """Convert complex objects to serializable representations."""
    if isinstance(val, (datetime.date, datetime.datetime)):
        return val.isoformat()
    if isinstance(val, pd.DataFrame):
        return val.to_dict(orient="records")
    if isinstance(val, dict):
        return {k: normalize_value(v) for k, v in val.items()}
    if isinstance(val, list):
        return [normalize_value(item) for item in val]
    return val


class BasicBiMap(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reverse = {make_hashable(v): k for k, v in self.items()}

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.reverse[make_hashable(value)] = key

    def __eq__(self, other) -> bool:
        if not isinstance(other, dict):
            return False
        if not super().__eq__(other):
            if isinstance(other, BasicBiMap) and other.reverse == dict(self):
                warnings.warn(
                    "BasicBiMap reversed key/value equivalence.",
                    ReversedBiMapComparisonWarning,
                    stacklevel=2,
                )
            return False
        return True


def stringify_children(node: ET.Element, encoding: str = "utf-8") -> str:
    """Return the XML text for ``node`` including all children."""
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


def remove_html_tags(
    text: str, removals: list[str], replaces: dict[str, str], verbose: bool = False
) -> str:
    """Remove or replace specific HTML tags in ``text``.

    Args:
        text: Input HTML string.
        removals: Tags to remove entirely.
        replaces: Mapping of tags to replacement text.
        verbose: Log actions when ``True``.

    Returns:
        Sanitised string with specified tags removed or replaced.
    """
    to_remove = (
        removals
        + [f"</{tag[1:]}" for tag in removals]
        + [f"</{tag[1:]}" for tag in replaces]
    )
    to_remove = [tag[:-1] + r"\b[^>]*" + tag[-1] for tag in to_remove]
    to_replace = {tag[:-1] + r"\b[^>]*" + tag[-1]: rep for tag, rep in replaces.items()}
    if verbose:
        logger.info("Removing tags: %s", to_remove)
        logger.info("Replacing tags: %s", to_replace)
    pat = "|".join(to_remove)
    text = re.sub(pat, "", text, flags=re.IGNORECASE)
    for p, r in to_replace.items():
        text = re.sub(p, r, text)
    return text


def strip_html_text_styling(text: str, verbose: bool = False) -> str:
    """Simplify emphasis tags and remove styling from HTML text.

    Args:
        text: HTML text to clean.
        verbose: Log removed and replaced tags when ``True``.

    Returns:
        Sanitised text with simplified styling.
    """
    removes = ["<italic>", "<i>", "<bold>", "<b>", "<underline>", "<u>"]
    reps = {"<sub>": "_", "<sup>": "^", "<ext-link>": "[External URI:]"}
    return remove_html_tags(text, removes, reps, verbose)


def split_text_and_refs(
    tree_text: str,
    ref_map: BasicBiMap,
    id: Optional[str] = None,
    on_unknown: str = "keep",
) -> str:
    """Replace reference tags with placeholders and build a mapping.

    Args:
        tree_text: Raw HTML/XML string containing reference tags.
        ref_map: ``BasicBiMap`` for storing original tag text.
        id: Optional identifier for debugging purposes.
        on_unknown: Behaviour when encountering an unexpected tag;
            ``"keep"`` retains the tag contents.

    Returns:
        String with reference placeholders substituted.
    """
    allowed_tags = ["xref", "fig", "table-wrap"]
    pattern = r"<([a-zA-Z][\w-]*)\b[^>]*>(.*?)</\1>|<([a-zA-Z][\w-]*)\b[^/>]*/?>"
    tag_r = re.compile(pattern, re.DOTALL)
    text = tree_text.strip()
    text = strip_html_text_styling(text)
    cleaned_text = ""
    while text:
        match = tag_r.search(text)
        if match:
            tag_name = match.group(1) or match.group(3)
            tag_contents = match.group(2) if match.group(2) else ""
            full_tag = match.group()
            cleaned_text += text[: match.start()]
            if tag_name not in allowed_tags:
                warnings.warn(
                    f"Tag {tag_name} not allowed. Behavior: {on_unknown}.",
                    UnexpectedTagWarning,
                    stacklevel=2,
                )
                if on_unknown == "keep":
                    cleaned_text += tag_contents
                text = text[match.end() :]
            else:
                if tag_name == "xref":
                    cleaned_text += tag_contents
                if full_tag in ref_map.reverse:
                    ref_num = ref_map.reverse[full_tag]
                else:
                    ref_num = len(ref_map)
                    ref_map[ref_num] = full_tag
                data_ref_tag = generate_typed_mhtml_tag("dataref", str(ref_num))
                cleaned_text += data_ref_tag
                text = text[match.end() :]
        else:
            cleaned_text += text
            break
    return cleaned_text


def generate_typed_mhtml_tag(tag_type: str, s: str) -> str:
    """Create a marker string used to reference text elements."""
    return f"[MHTML::{tag_type}::{s}]"


def remove_mhtml_tags(text: str) -> str:
    """Remove MHTML placeholder tags from ``text``."""
    pat = r"\[MHTML::([^:\[\]]+)::([^:\[\]]+)\]|\[MHTML::([^:\[\]]+)\]"
    return re.sub(pat, "", text)


def define_data_dict() -> dict[str, str]:
    """Return documentation strings for Paper fields."""
    return {
        "PMCID": "PMCID of the PMC article. Unique.",
        "Title": "Title of the PMC article.",
        "Authors": clean_doc(
            "DataFrame of PMC Authors including names, emails, and affiliations."
        ),
        "Non-Author Contributors": clean_doc(
            "DataFrame of non-author contributors with names, emails, and affiliations."
        ),
        "Abstract": clean_doc(
            "List of TextSections parsed from the abstract. Use Paper.abstract_as_str() for a simple view."
        ),
        "Body": clean_doc(
            "List of TextSections parsed from the body. Use Paper.body_as_str() for a simple view."
        ),
        "Journal ID": clean_doc(
            "Dict of journal ID types and values (e.g. NLM-TA, ISO-ABBREV)."
        ),
        "Journal Title": "Journal title in text.",
        "ISSN": "Dict of ISSN types and values.",
        "Publisher Name": "Name of the publisher.",
        "Publisher Location": "Location of the publisher.",
        "Article ID": clean_doc(
            "Dict of article ID types and values. e.g., p.article_id['pmc'] returns the PMCID."
        ),
        "Article Types": "List of header article types.",
        "Article Categories": "List of non-header article types.",
        "Keywords": "Keywords or subject terms for the article. Strings or grouped dicts.",
        "Published Date": clean_doc(
            "Dict of publication dates (e.g., electronic, print)."
        ),
        "History Dates": clean_doc(
            "Dict of manuscript history dates (received, accepted, revised, etc.)."
        ),
        "Volume": clean_doc("Volume number."),
        "Issue": clean_doc("Issue number."),
        "FPage": "First page of publication.",
        "LPage": "Last page of publication.",
        "First Page": "First page of publication (alias).",
        "Last Page": "Last page of publication (alias).",
        "Permissions": clean_doc(
            "Summary of copyright, license type, and full license text."
        ),
        "Copyright Statement": clean_doc(
            "Copyright statement, typically a short phrase."
        ),
        "License": clean_doc("License type (e.g., Open Access)."),
        "Funding": clean_doc("List of funding groups, important for bias detection."),
        "Ethics": clean_doc("Dict of ethics / disclosure statements (conflicts, ethics statement, trial registration, etc.)."),
        "Footnote": "Text of any footnotes provided with the article.",
        "Acknowledgements": clean_doc("List of acknowledgement statements."),
        "Notes": "List of notes included with the article.",
        "Custom Meta": clean_doc("Dict of custom metadata key/value pairs."),
        "Citations": "List of parsed citation dictionaries or strings.",
        "Tables": "List of pandas DataFrame objects parsed from tables.",
        "Figures": "List of figure metadata dictionaries (Label, Caption, Link).",
        "Supplementary Material": "List of supplementary-material/media objects with Label, Caption, Href.",
        "Equations": "List of MathML equation strings present in the article.",
        "Ref Map": clean_doc(
            "Dict mapping reference indices to reference data for linking text with citations, tables, etc."
        ),
    }
