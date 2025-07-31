"""Wrapper around PMC OA Web Service (utils/oa/oa.fcgi).

Returns dicts keyed by PMCID/PMID.
Documentation: https://www.ncbi.nlm.nih.gov/pmc/tools/oa-service/
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from pmcgrab.http_utils import cached_get

_BASE_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"


def _parse_oa_record(rec: ET.Element) -> dict[str, str]:
    out: dict[str, str] = dict(rec.attrib.items())
    for link in rec:
        out[link.tag] = link.text or ""
    return out


def fetch(article_id: str, id_type: str = "pmcid") -> dict[str, str] | None:
    """Fetch OA service record for a single article.

    id_type is one of pmcid|pmid|doi.
    """
    resp = cached_get(
        _BASE_URL, params={id_type: article_id}, headers={"User-Agent": "pmcgrab/0.1"}
    )
    root = ET.fromstring(resp.content)
    rec = root.find("record")
    if rec is None:
        return None
    return _parse_oa_record(rec)
