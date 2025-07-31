"""Wrapper for PMC OAI-PMH service.

The PMC endpoint: https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi
Implements minimal verbs required for harvesting.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Generator, Iterator

from pmcgrab.http_utils import cached_get

_BASE_URL = "https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi"


class OAIPMHError(RuntimeError):
    """Raised on protocol errors."""


# ---------------------- Low-level helpers -----------------------------


def _request(verb: str, **params) -> ET.Element:
    q = {"verb": verb, **params}
    resp = cached_get(_BASE_URL, params=q, headers={"User-Agent": "pmcgrab/0.1"})
    root = ET.fromstring(resp.content)
    error = root.find("{*}error")
    if error is not None:
        raise OAIPMHError(error.text or "Unknown OAI-PMH error")
    return root


def _extract_records(root: ET.Element) -> list[ET.Element]:
    return root.findall("{*}ListRecords/{*}record")


def _get_resumption_token(root: ET.Element) -> str | None:
    token = root.find(".//{*}resumptionToken")
    return token.text if token is not None and token.text else None


# ---------------------- Public API ------------------------------------


def list_records(
    metadata_prefix: str = "pmc",
    from_: str | None = None,
    until: str | None = None,
    set_: str | None = None,
) -> Iterator[ET.Element]:
    """Yield <record> elements lazily, transparently handling resumption tokens."""
    params: dict[str, str] = {"metadataPrefix": metadata_prefix}
    if from_:
        params["from"] = from_
    if until:
        params["until"] = until
    if set_:
        params["set"] = set_

    root = _request("ListRecords", **params)
    while True:
        yield from _extract_records(root)
        token = _get_resumption_token(root)
        if not token:
            break
        root = _request("ListRecords", resumptionToken=token)


def get_record(identifier: str, metadata_prefix: str = "pmc") -> ET.Element:
    root = _request("GetRecord", identifier=identifier, metadataPrefix=metadata_prefix)
    return root.find("{*}GetRecord/{*}record")  # type: ignore


def list_identifiers(
    metadata_prefix: str = "pmc",
    from_: str | None = None,
    until: str | None = None,
    set_: str | None = None,
) -> Generator[str, None, None]:
    params: dict[str, str] = {"metadataPrefix": metadata_prefix}
    if from_:
        params["from"] = from_
    if until:
        params["until"] = until
    if set_:
        params["set"] = set_
    root = _request("ListIdentifiers", **params)
    while True:
        for header in root.findall("{*}ListIdentifiers/{*}header"):
            yield header.findtext("{*}identifier")  # type: ignore
        token = _get_resumption_token(root)
        if not token:
            break
        root = _request("ListIdentifiers", resumptionToken=token)


def list_sets() -> list[dict[str, str]]:
    root = _request("ListSets")
    sets = []
    for s in root.findall("{*}ListSets/{*}set"):
        sets.append(
            {
                "setSpec": s.findtext("{*}setSpec"),
                "setName": s.findtext("{*}setName"),
            }
        )
    return sets
