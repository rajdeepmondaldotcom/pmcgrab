"""Simple wrapper for the BioC RESTful API for PMC OA subset.

Example endpoint:
https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/PMC12345

This module returns the raw JSON dict.
"""

from __future__ import annotations

import json
from typing import Any

from pmcgrab.http_utils import cached_get

_BASE_URL = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/"


def fetch_json(pmcid: str) -> dict[str, Any]:
    url = _BASE_URL + pmcid
    resp = cached_get(url, headers={"User-Agent": "pmcgrab/0.1"})
    return json.loads(resp.text)
