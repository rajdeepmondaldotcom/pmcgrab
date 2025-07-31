"""PMC ID Converter API wrapper.

Docs: https://pmc.ncbi.nlm.nih.gov/tools/id-converter-api/
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from pmcgrab.http_utils import cached_get

_BASE_URL = "https://pmc.ncbi.nlm.nih.gov/tools/idconv/v1.0/"  # new API path


def convert(ids: List[str]) -> Dict[str, Any]:
    params = {"ids": ",".join(ids), "format": "json"}
    resp = cached_get(
        _BASE_URL + "json/", params=params, headers={"User-Agent": "pmcgrab/0.1"}
    )
    return json.loads(resp.text)
