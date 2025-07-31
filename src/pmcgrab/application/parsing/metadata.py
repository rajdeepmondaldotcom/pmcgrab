from __future__ import annotations

"""Metadata extraction helpers.

This module contains *pure* functions that extract high-level bibliographic and
journal metadata from the PMC article XML tree. They are intentionally kept
free of side-effects so they can be unit-tested in isolation.
"""

import datetime
import warnings
from typing import Dict, List, Optional, Union

import lxml.etree as ET

from pmcgrab.constants import (
    UnexpectedMultipleMatchWarning,
    UnexpectedZeroMatchWarning,
)

__all__: list[str] = [
    # article title
    "gather_title",
    # journal section
    "gather_journal_id",
    "gather_journal_title",
    "gather_issn",
    "gather_publisher_name",
    "gather_publisher_location",
    # article identifiers / classification
    "gather_article_id",
    "gather_article_types",
    "gather_article_categories",
    # dates / versions
    "gather_published_date",
    "gather_history_dates",
    # "gather_version_history",  # moved to content.py
    # misc numeric
    "gather_volume",
    "gather_issue",
    # keywords
    "gather_keywords",
]


# ---------------------------------------------------------------------------
# Simple single-value helpers
# ---------------------------------------------------------------------------


def gather_title(root: ET.Element) -> Optional[str]:
    """Return the article title if present."""
    matches: List[str] = root.xpath("//article-title/text()")
    if len(matches) > 1:
        warnings.warn(
            "Multiple titles found; using the first.",
            UnexpectedMultipleMatchWarning,
            stacklevel=2,
        )
    if not matches:
        warnings.warn(
            "No article title found.", UnexpectedZeroMatchWarning, stacklevel=2
        )
        return None
    return matches[0]


# ---------------------------------------------------------------------------
# Journal-level metadata
# ---------------------------------------------------------------------------


def gather_journal_id(root: ET.Element) -> Dict[str, str]:
    ids = root.xpath("//journal-meta/journal-id")
    return {jid.get("journal-id-type"): jid.text for jid in ids}


def gather_journal_title(root: ET.Element) -> Optional[Union[List[str], str]]:
    titles = [t.text for t in root.xpath("//journal-title")]
    if not titles:
        warnings.warn(
            "No journal title found.", UnexpectedZeroMatchWarning, stacklevel=2
        )
        return None
    return titles if len(titles) > 1 else titles[0]


def gather_issn(root: ET.Element) -> Dict[str, str]:
    issns = root.xpath("//journal-meta/issn")
    return {issn.get("pub-type"): issn.text for issn in issns}


def gather_publisher_name(root: ET.Element) -> Union[str, List[str]]:
    pubs = root.xpath("//journal-meta/publisher/publisher-name")
    return pubs[0].text if len(pubs) == 1 else [p.text for p in pubs]


def gather_publisher_location(root: ET.Element) -> Union[str, List[str]]:
    locs = root.xpath("//journal-meta/publisher/publisher-loc")
    if not locs:
        return None
    return locs[0].text if len(locs) == 1 else [l.text for l in locs]


# ---------------------------------------------------------------------------
# Article identifiers & categories
# ---------------------------------------------------------------------------


def gather_article_id(root: ET.Element) -> Dict[str, str]:
    ids = root.xpath("//article-meta/article-id")
    return {aid.get("pub-id-type"): aid.text for aid in ids}


def gather_article_types(root: ET.Element) -> Optional[List[str]]:
    cats = root.xpath("//article-meta/article-categories")
    if not cats:
        warnings.warn(
            "No article-categories found.", UnexpectedZeroMatchWarning, stacklevel=2
        )
        return None
    heading = cats[0].xpath("subj-group[@subj-group-type='heading']/subject")
    texts = [h.text for h in heading]
    if not texts:
        return ["No article type found."]
    return texts


def gather_article_categories(root: ET.Element) -> Optional[List[Dict[str, str]]]:
    cats = root.xpath("//article-meta/article-categories")
    if not cats:
        warnings.warn(
            "No article-categories found.", UnexpectedZeroMatchWarning, stacklevel=2
        )
        return None
    others = cats[0].xpath("subj-group[not(@subj-group-type='heading')]/subject")
    result = [{other.get("subj-group-type"): other.text} for other in others]
    if not result:
        return [{"info": "No extra article categories found."}]
    return result


# ---------------------------------------------------------------------------
# Dates / history
# ---------------------------------------------------------------------------


def gather_published_date(root: ET.Element) -> Dict[str, datetime.date]:
    dates: Dict[str, datetime.date] = {}
    for pd_elem in root.xpath("//article-meta/pub-date"):
        ptype = pd_elem.get("pub-type")
        year = (
            int(pd_elem.xpath("year/text()")[0]) if pd_elem.xpath("year/text()") else 1
        )
        month = (
            int(pd_elem.xpath("month/text()")[0])
            if pd_elem.xpath("month/text()")
            else 1
        )
        day = int(pd_elem.xpath("day/text()")[0]) if pd_elem.xpath("day/text()") else 1
        dates[ptype] = datetime.date(year, month, day)
    return dates


def gather_history_dates(root: ET.Element) -> Optional[Dict[str, datetime.date]]:
    dates: Dict[str, datetime.date] = {}
    for h_elem in root.xpath("//article-meta/history/date"):
        dtype = h_elem.get("date-type") or "unknown"
        year = int(h_elem.xpath("year/text()")[0]) if h_elem.xpath("year/text()") else 1
        month = (
            int(h_elem.xpath("month/text()")[0]) if h_elem.xpath("month/text()") else 1
        )
        day = int(h_elem.xpath("day/text()")[0]) if h_elem.xpath("day/text()") else 1
        dates[dtype] = datetime.date(year, month, day)
    return dates or None


# gather_version_history intentionally left in original parser for now

# ---------------------------------------------------------------------------
# Numbers
# ---------------------------------------------------------------------------


def gather_volume(root: ET.Element) -> Optional[str]:
    vol = root.xpath("//article-meta/volume/text()")
    if not vol:
        warnings.warn("No volume found.", UnexpectedZeroMatchWarning, stacklevel=2)
        return None
    return vol[0]


def gather_issue(root: ET.Element) -> Optional[str]:
    iss = root.xpath("//article-meta/issue/text()")
    if not iss:
        warnings.warn("No issue found.", UnexpectedZeroMatchWarning, stacklevel=2)
        return None
    return iss[0]


# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------


def gather_keywords(root: ET.Element):
    """Return keywords from <kwd-group> and article-categories keyword groups."""
    keywords: list[Union[str, dict[str, list[str]]]] = []

    # kwd-group parsing
    for group in root.xpath("//kwd-group"):
        group_type = group.get("kwd-group-type")
        words = [
            kwd.text.strip()
            for kwd in group.xpath("kwd")
            if kwd.text and kwd.text.strip()
        ]
        if not words:
            continue
        if group_type:
            keywords.append({group_type: words})
        else:
            keywords.extend(words)

    # article-categories keyword groups
    for subj_grp in root.xpath(
        "//article-meta/article-categories/subj-group[@subj-group-type='keyword']"
    ):
        words = [
            subj.text.strip()
            for subj in subj_grp.xpath("subject")
            if subj.text and subj.text.strip()
        ]
        if words:
            keywords.append({"article-categories-keyword": words})

    return keywords or None
