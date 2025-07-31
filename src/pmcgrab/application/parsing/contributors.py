from __future__ import annotations

"""Contributor / author extraction helpers."""

import warnings

import lxml.etree as ET
import pandas as pd

from pmcgrab.constants import (
    UnexpectedMultipleMatchWarning,
    UnexpectedZeroMatchWarning,
)

__all__: list[str] = [
    "extract_contributor_info",
    "gather_authors",
    "gather_non_author_contributors",
]


def extract_contributor_info(
    root: ET.Element, contributors: list[ET.Element]
) -> list[tuple]:
    """Return list of contributor tuples with rich metadata."""
    result = []
    for contrib in contributors:
        ctype = (contrib.get("contrib-type") or "").capitalize().strip()
        first = contrib.findtext(".//given-names")
        first = first.strip() if first else None
        last = contrib.findtext(".//surname")
        last = last.strip() if last else None
        addr = contrib.findtext(".//address/email")
        addr = addr.strip() if addr else None

        # affiliations ------------------------------------------------------
        affils: list[str] = []
        for aff in contrib.xpath(".//xref[@ref-type='aff']"):
            aid = aff.get("rid")
            texts = root.xpath(
                f"//contrib-group/aff[@id='{aid}']/text()[not(parent::label)]"
            )
            if len(texts) > 1:
                warnings.warn(
                    "Multiple affiliations found for one ID.",
                    UnexpectedMultipleMatchWarning,
                    stacklevel=2,
                )
            if not texts:
                texts = ["Affiliation data not found."]
            inst = root.xpath(
                f"//contrib-group/aff[@id='{aid}']/institution-wrap/institution/text()"
            )
            inst_str = " ".join(str(i) for i in inst)
            affils.append(
                f"{aid.strip()}: {inst_str}{texts[0].strip()}"
                if inst_str
                else f"{aid.strip()}: {texts[0].strip()}"
            )

        orcid = contrib.findtext(".//contrib-id[@contrib-id-type='orcid']")
        isni = contrib.findtext(".//contrib-id[@contrib-id-type='isni']")
        equal_flag = contrib.get("equal-contrib") == "yes"

        result.append((ctype, first, last, addr, affils, orcid, isni, equal_flag))
    return result


def gather_authors(root: ET.Element) -> pd.DataFrame | None:
    authors = root.xpath(".//contrib[@contrib-type='author']")
    if not authors:
        warnings.warn("No authors found.", UnexpectedZeroMatchWarning, stacklevel=2)
        return None
    data = extract_contributor_info(root, authors)
    return pd.DataFrame(
        data,
        columns=[
            "Contributor_Type",
            "First_Name",
            "Last_Name",
            "Email_Address",
            "Affiliations",
            "ORCID",
            "ISNI",
            "Equal_Contrib",
        ],
    )


def gather_non_author_contributors(root: ET.Element) -> str | pd.DataFrame:
    non_auth = root.xpath(".//contrib[not(@contrib-type='author')]")
    if non_auth:
        data = extract_contributor_info(root, non_auth)
        return pd.DataFrame(
            data,
            columns=[
                "Contributor_Type",
                "First_Name",
                "Last_Name",
                "Email_Address",
                "Affiliations",
                "ORCID",
                "ISNI",
                "Equal_Contrib",
            ],
        )
    return "No non-author contributors found."
