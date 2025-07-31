from __future__ import annotations

"""Miscellaneous content extraction helpers (permissions, funding, etc.)."""

import datetime
import textwrap
import uuid
import warnings
from typing import List, Optional, Union, Dict

import lxml.etree as ET
import pandas as pd  # Required only for type hints – no heavy ops here

from pmcgrab.constants import (
    UnexpectedMultipleMatchWarning,
    UnexpectedZeroMatchWarning,
    UnhandledTextTagWarning,
    UnmatchedCitationWarning,
    UnmatchedTableWarning,
)
from pmcgrab.model import TextParagraph, TextTable, TextFigure
from pmcgrab.utils import BasicBiMap

__all__: list[str] = [
    "gather_permissions",
    "gather_funding",
    "gather_version_history",
    "gather_equations",
    "gather_supplementary_material",
    "gather_ethics_disclosures",
    "gather_footnote",
    "gather_acknowledgements",
    "gather_notes",
    "gather_custom_metadata",
    # helper
    "stringify_note",
]

# ----------------------------------------------------------------------------
# Permissions / funding / versions
# ----------------------------------------------------------------------------

def gather_permissions(root: ET.Element) -> Optional[Dict[str, str]]:
    cp = root.xpath("//article-meta/permissions/copyright-statement/text()")
    cp_stmt = cp[0] if cp else "No copyright statement found."
    lic_elems = root.xpath("//article-meta/permissions/license")
    if not lic_elems:
        warnings.warn("No license found.", UnexpectedZeroMatchWarning, stacklevel=2)
        return None
    if len(lic_elems) > 1:
        warnings.warn(
            "Multiple licenses found; using the first.",
            UnexpectedMultipleMatchWarning,
            stacklevel=2,
        )
    lic_elem = lic_elems[0]
    lic_type = lic_elem.get("license-type", "Not Specified")
    lic_text = "\n".join(
        str(TextParagraph(child)) for child in lic_elem if child.tag == "license-p"
    )
    return {
        "Copyright Statement": cp_stmt,
        "License Type": lic_type,
        "License Text": lic_text,
    }


def gather_funding(root: ET.Element) -> Optional[List[str]]:
    fund: List[str] = []
    for group in root.xpath("//article-meta/funding-group"):
        fund.extend(group.xpath("award-group/funding-source/institution/text()"))
    return fund or None


def gather_version_history(root: ET.Element) -> Optional[List[Dict[str, str]]]:
    versions: List[Dict[str, str]] = []
    for ver in root.xpath("//article-meta/article-version"):
        ver_num = ver.get("version") or ver.findtext("version")
        date_elem = ver.find("date")
        date_str = None
        if date_elem is not None:
            year = date_elem.findtext("year")
            month = date_elem.findtext("month") or "1"
            day = date_elem.findtext("day") or "1"
            if year:
                date_str = f"{year}-{int(month):02d}-{int(day):02d}"
        versions.append({"Version": ver_num, "Date": date_str})
    return versions or None

# ----------------------------------------------------------------------------
# Equations & supplementary material
# ----------------------------------------------------------------------------

def gather_equations(root: ET.Element) -> Optional[List[str]]:
    eqs = []
    for math in root.xpath(
        "//mml:math", namespaces={"mml": "http://www.w3.org/1998/Math/MathML"}
    ):
        eqs.append(ET.tostring(math, encoding="unicode"))
    return eqs or None


def gather_supplementary_material(root: ET.Element) -> Optional[List[Dict[str, str]]]:
    items: List[Dict[str, str]] = []
    for supp in root.xpath("//supplementary-material|//media"):
        label = supp.findtext("label") or supp.get("id")
        caption_elem = supp.find("caption")
        caption = None
        if caption_elem is not None:
            caption = " ".join(caption_elem.itertext()).strip()
        href = supp.get("xlink:href")
        if not href:
            ext = supp.find("ext-link")
            if ext is not None and ext.get("xlink:href"):
                href = ext.get("xlink:href")
        items.append({
            "Label": label,
            "Caption": caption,
            "Href": href,
            "Tag": supp.tag,
        })
    return items or None

# ----------------------------------------------------------------------------
# Ethics / footnotes / acknowledgements / notes
# ----------------------------------------------------------------------------

def gather_ethics_disclosures(root: ET.Element) -> Optional[Dict[str, str]]:
    fields: Dict[str, tuple[str, list[str]]] = {
        "Conflicts of Interest": ("//conflict-of-interest", []),
        "Ethics Statement": ("//ethics-statement", []),
        "Clinical Trial Registration": (
            "//clinical-trial-number|//other-id[@other-id-type='clinical-trial-number']",
            [],
        ),
        "Data Availability": ("//data-availability", []),
        "Author Contributions": ("//author-notes", []),
        "Patient Consent": ("//patient-consent", []),
    }
    result: Dict[str, str] = {}
    for key, (xpath, _) in fields.items():
        texts = [" ".join(el.itertext()).strip() for el in root.xpath(xpath)]
        if texts:
            result[key] = "\n".join(texts)
    if "Conflicts of Interest" not in result:
        texts = [
            " ".join(fn.itertext()).strip() for fn in root.xpath("//fn[@fn-type='conflict']")
        ]
        if texts:
            result["Conflicts of Interest"] = "\n".join(texts)
    return result or None


def gather_footnote(root: ET.Element) -> Optional[str]:
    foot: List[str] = []
    for fn in root.xpath("//back/fn-group/fn"):
        for child in fn:
            if child.tag == "p":
                foot.append(str(TextParagraph(child)))
            else:
                warnings.warn(
                    f"Unexpected tag {child.tag} in footnote.",
                    UnhandledTextTagWarning,
                    stacklevel=2,
                )
    return " - ".join(foot) if foot else None


def gather_acknowledgements(root: ET.Element) -> Union[List[str], str]:
    return [" ".join(match.itertext()).strip() for match in root.xpath("//ack")]


def stringify_note(root: ET.Element) -> str:
    note = ""
    for child in root:
        if child.tag == "title":
            note += f"Title: {child.text}\n"
        elif child.tag == "p":
            note += child.text or ""
        elif child.tag == "notes":
            note += "\n" + textwrap.indent(stringify_note(child), " " * 4)
    return note.strip()


def gather_notes(root: ET.Element) -> List[str]:
    return [
        stringify_note(note)
        for note in root.xpath("//notes")
        if note.getparent().tag != "notes"
    ]

# ----------------------------------------------------------------------------
# Custom meta
# ----------------------------------------------------------------------------

def gather_custom_metadata(root: ET.Element) -> Optional[Dict[str, str]]:
    custom: Dict[str, str] = {}
    for meta in root.xpath("//custom-meta"):
        name = meta.findtext("meta-name")
        value = (
            " ".join(meta.find("meta-value").itertext())
            if meta.find("meta-value") is not None
            else None
        )
        if value:
            if name is None:
                name = str(uuid.uuid4())
            custom[name] = value
    return custom or None
