"""NCBI PMC Open Access Web Service client for article metadata and links.

In addition to the existing single-record :func:`fetch` helper (which flattens
all ``<link>`` elements into a single dict, losing duplicates), this module
exposes :func:`list_oa_links` which preserves every ``<link>`` entry with its
``format``, ``href``, and ``updated`` attributes — required for the asset
fetcher which needs the ``format=tgz`` package link specifically.


This module provides access to NCBI's PMC Open Access Web Service, which
offers metadata and download links for Open Access articles in PubMed Central.
The service provides information about article availability, formats, and
direct download URLs for various file types.

The OA Web Service is particularly useful for determining article availability
and obtaining direct download links for Open Access content in multiple formats
including PDF, XML, and supplementary materials.

Key Features:
    * Article metadata retrieval by PMCID, PMID, or DOI
    * Direct download links for available formats
    * Open Access status verification
    * Cached HTTP requests for improved performance
    * Clean dictionary output for easy integration

Supported Query Types:
    * PMCID: PubMed Central ID (default)
    * PMID: PubMed ID
    * DOI: Digital Object Identifier

Available Information:
    * Article identifiers and cross-references
    * Available file formats (PDF, XML, etc.)
    * Direct download URLs
    * Open Access license information
    * Last updated timestamps

API Documentation:
    https://www.ncbi.nlm.nih.gov/pmc/tools/oa-service/

Functions:
    fetch: Retrieve Open Access metadata and links for an article
    _parse_oa_record: Internal XML parsing helper
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from pmcgrab.http_utils import cached_get

_BASE_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"


def _parse_oa_record(rec: ET.Element) -> dict[str, str]:
    """Parse Open Access service XML record into dictionary format.

    Internal helper function that extracts information from the XML record
    element returned by the PMC OA Web Service API. Combines element
    attributes with child element text content.

    Args:
        rec: XML record element from OA service response

    Returns:
        dict[str, str]: Parsed record data with attribute and element information
    """
    out: dict[str, str] = dict(rec.attrib.items())
    for link in rec:
        out[link.tag] = link.text or ""
    return out


def fetch(article_id: str, id_type: str = "pmcid") -> dict[str, str] | None:
    """Fetch Open Access metadata and download links for a PMC article.

    Retrieves comprehensive Open Access information for the specified article
    including availability status, file format options, and direct download
    URLs. The service provides metadata for Open Access articles and indicates
    availability for non-OA content.

    Args:
        article_id: Article identifier in the format specified by id_type
                   Examples: "PMC7181753", "33087749", "10.1038/s41586-020-2832-5"
        id_type: Type of identifier provided. Supported values:
                - "pmcid": PubMed Central ID (default)
                - "pmid": PubMed ID
                - "doi": Digital Object Identifier

    Returns:
        dict[str, str] | None: Open Access record information containing:
            - Record attributes (status, error codes, etc.)
            - Available file format links (link, pdf, etc.)
            - Metadata fields (title, license, etc.)
            Returns None if no record found or article not available.

    Raises:
        requests.HTTPError: If API request fails due to network issues
        xml.etree.ElementTree.ParseError: If API returns malformed XML
        requests.RequestException: If request fails after retries

    Examples:
        >>> # Fetch OA information by PMC ID
        >>> oa_info = fetch("PMC7181753")
        >>> if oa_info:
        ...     print(f"Status: {oa_info.get('status')}")
        ...     if 'link' in oa_info:
        ...         print(f"XML download: {oa_info['link']}")
        ...     if 'pdf' in oa_info:
        ...         print(f"PDF download: {oa_info['pdf']}")
        >>>
        >>> # Fetch by PubMed ID
        >>> oa_info = fetch("33087749", id_type="pmid")
        >>> if oa_info:
        ...     print("Article is Open Access")
        ... else:
        ...     print("Article not found or not Open Access")
        >>>
        >>> # Fetch by DOI
        >>> oa_info = fetch("10.1038/s41586-020-2832-5", id_type="doi")
        >>> if oa_info and oa_info.get('status') == 'free':
        ...     print("Article is freely available")

    Record Fields:
        Common fields in the returned dictionary include:
        * status: Availability status ("free", "not_found", etc.)
        * link: Direct URL to article XML
        * pdf: Direct URL to article PDF (if available)
        * license: License type (e.g., "CC BY")
        * retmax: Maximum results returned
        * error: Error message (if applicable)

    Note:
        This service only provides information for Open Access articles.
        Non-OA articles may return None or limited metadata. All URLs
        returned are direct download links that can be used programmatically.

        Requests are cached using pmcgrab.http_utils.cached_get for
        improved performance on repeated queries.
    """
    rec = _first_record(article_id, id_type)
    if rec is None:
        return None
    return _parse_oa_record(rec)


def _first_record(article_id: str, id_type: str) -> ET.Element | None:
    """Fetch the OA response and return the first ``<record>`` element, if any.

    The NCBI OA web service treats ``id`` as a polymorphic parameter that
    accepts a PMCID, PMID, or DOI; passing ``pmcid=`` / ``pmid=`` / ``doi=``
    instead returns the catalog summary rather than the requested record,
    so we always use the ``id`` form. ``id_type`` is retained in the
    signature for backward compatibility with callers but is informational.
    """
    from pmcgrab import __version__

    del id_type  # accepted for back-compat; ignored
    resp = cached_get(
        _BASE_URL,
        params={"id": article_id},
        headers={"User-Agent": f"pmcgrab/{__version__}"},
    )
    root = ET.fromstring(resp.content)
    # The OA service wraps records inside a <records> container, but the
    # historical fetch() code calls root.find("record"). Support both.
    records_container = root.find("records")
    if records_container is not None:
        return records_container.find("record")
    return root.find("record")


def list_oa_links(article_id: str, id_type: str = "pmcid") -> list[dict[str, str]]:
    """Return every ``<link>`` element from the OA service response.

    Unlike :func:`fetch`, this helper preserves multiplicity: a record with
    both ``format=tgz`` and ``format=pdf`` links yields a two-element list.
    Each dict carries the link's attributes (``format``, ``href``, ``updated``,
    etc.) plus any text content under the key ``"text"``.

    Args:
        article_id: Article identifier in the format specified by id_type.
        id_type: ``"pmcid"`` (default), ``"pmid"``, or ``"doi"``.

    Returns:
        list[dict[str, str]]: Ordered list of link metadata dicts. Empty if
        the record exists but has no ``<link>`` children, or if no record
        was found.
    """
    rec = _first_record(article_id, id_type)
    if rec is None:
        return []
    links: list[dict[str, str]] = []
    for link in rec.findall("link"):
        entry: dict[str, str] = dict(link.attrib.items())
        text = (link.text or "").strip()
        if text:
            entry["text"] = text
        links.append(entry)
    return links


def tgz_url_for(pmcid: int | str) -> str | None:
    """Return the HTTPS-rewritten URL of the OA tar.gz package for *pmcid*.

    NCBI publishes the OA package URL with an ``ftp://`` scheme pointing at
    ``ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package/...``. The same file is served
    over HTTPS, but as of the 2024-2025 PMC infrastructure migration the
    canonical path moved under ``/pub/pmc/deprecated/oa_package/``. The
    legacy ``/pub/pmc/oa_package/`` URL returns 404 over HTTPS today. We
    rewrite both the scheme and the path so the asset fetcher can stream the
    tar.gz directly.

    Args:
        pmcid: PMC ID (with or without the ``PMC`` prefix).

    Returns:
        str | None: HTTPS URL of the tar.gz package, or ``None`` if the
        article is not in the OA subset / has no package link.
    """
    normalized = str(pmcid)
    if not normalized.upper().startswith("PMC"):
        normalized = f"PMC{normalized}"
    links = list_oa_links(normalized)
    for link in links:
        if link.get("format", "").lower() == "tgz" and link.get("href"):
            return _rewrite_oa_url(link["href"])
    return None


def _rewrite_oa_url(href: str) -> str:
    """Rewrite an OA package URL from FTP to the current HTTPS path.

    Handles two transformations:
      * ``ftp://ftp.ncbi.nlm.nih.gov/...`` -> ``https://ftp.ncbi.nlm.nih.gov/...``
      * ``/pub/pmc/oa_package/...`` -> ``/pub/pmc/deprecated/oa_package/...``
    """
    if href.startswith("ftp://ftp.ncbi.nlm.nih.gov/"):
        href = "https://" + href[len("ftp://") :]
    href = href.replace(
        "/pub/pmc/oa_package/",
        "/pub/pmc/deprecated/oa_package/",
    )
    return href
