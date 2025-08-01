"""NCBI PMC Open Access Web Service client for article metadata and links.

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
    resp = cached_get(
        _BASE_URL, params={id_type: article_id}, headers={"User-Agent": "pmcgrab/0.5.5"}
    )
    root = ET.fromstring(resp.content)
    rec = root.find("record")
    if rec is None:
        return None
    return _parse_oa_record(rec)
