"""Wrapper for the Literature Citation Exporter (lit/ctxp) API.

Example: https://api.ncbi.nlm.nih.gov/lit/ctxp/v1/pmc/?format=medline&id=PMC12345
"""

from __future__ import annotations

from pmcgrab.http_utils import cached_get

_BASE_URL = "https://api.ncbi.nlm.nih.gov/lit/ctxp/v1/pmc/"


def export(pmcid: str, fmt: str = "medline") -> str:
    params: dict[str, str] = {"format": fmt, "id": pmcid}
    resp = cached_get(_BASE_URL, params=params, headers={"User-Agent": "pmcgrab/0.1"})
    return resp.text
