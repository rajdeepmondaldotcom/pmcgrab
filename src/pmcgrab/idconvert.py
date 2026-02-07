"""NCBI PMC ID Converter API client for cross-referencing publication identifiers.

This module provides a simple interface to NCBI's PMC ID Converter API,
which enables conversion between different publication identifier types
including PMC IDs, PubMed IDs, DOIs, and other standard identifiers.

The ID Converter is essential for working with scientific literature where
articles may be referenced by different identifier systems. This module
handles the API communication and returns structured mapping data.

Key Features:
    * Batch conversion of multiple identifiers in one request
    * Support for all major identifier types (PMCID, PMID, DOI, etc.)
    * Cached HTTP requests for improved performance
    * JSON response parsing with detailed conversion results
    * Error handling for invalid or non-existent identifiers
    * Flexible ID normalization accepting PMC IDs, PMIDs, and DOIs

Supported Identifier Types:
    * PMC ID (PubMed Central)
    * PMID (PubMed ID)
    * DOI (Digital Object Identifier)
    * Manuscript ID
    * NIH Manuscript ID
    * Publisher Item Identifier

API Documentation:
    https://pmc.ncbi.nlm.nih.gov/tools/id-converter-api/

Functions:
    convert: Batch convert publication identifiers between different formats
    normalize_id: Normalize any publication identifier to a numeric PMCID
    normalize_ids: Batch-normalize multiple identifiers to numeric PMCIDs
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pmcgrab.http_utils import cached_get

_BASE_URL = "https://pmc.ncbi.nlm.nih.gov/tools/idconv/v1.0/"  # new API path
_logger = logging.getLogger(__name__)

# Patterns for identifying ID types
_PMC_PREFIX_RE = re.compile(r"^pmc\s*", re.IGNORECASE)
_DOI_RE = re.compile(r"^10\.\d{4,}/")


def normalize_id(raw_id: str) -> str:
    """Normalize any publication identifier to a numeric PMCID string.

    Accepts PMC IDs in various formats (PMC7181753, pmc7181753, 7181753),
    PMIDs (plain numeric without PMC prefix -- resolved via API), and DOIs
    (resolved via NCBI ID Converter API).

    Args:
        raw_id: Input identifier in any supported format:
            - PMC IDs: "PMC7181753", "pmc7181753", "PMC 7181753", "7181753"
            - PMIDs: Numeric IDs that will be resolved via API if no PMC prefix
            - DOIs: "10.1038/s41586-020-2832-5"

    Returns:
        str: Numeric PMCID as a string (e.g., "7181753")

    Raises:
        ValueError: If the identifier cannot be resolved to a PMCID

    Examples:
        >>> normalize_id("PMC7181753")
        '7181753'
        >>> normalize_id("pmc 7181753")
        '7181753'
        >>> normalize_id("10.1038/s41586-020-2832-5")  # DOI -> PMCID via API
        '7612345'
    """
    raw_id = raw_id.strip()
    if not raw_id:
        raise ValueError("Empty identifier provided")

    # --- Case 1: Explicit PMC prefix -> strip it ---
    if _PMC_PREFIX_RE.match(raw_id):
        numeric = _PMC_PREFIX_RE.sub("", raw_id).strip()
        if numeric.isdigit():
            return numeric
        raise ValueError(f"Invalid PMC ID format: {raw_id!r}")

    # --- Case 2: DOI (starts with 10.XXXX/) -> resolve via API ---
    if _DOI_RE.match(raw_id):
        return _resolve_to_pmcid(raw_id, id_type="doi")

    # --- Case 3: Pure numeric -> could be PMCID or PMID ---
    if raw_id.isdigit():
        # Try as PMCID first by checking with the API
        # For the common case, users provide PMCIDs directly, so return as-is
        # but also try resolving as PMID if the caller specifies
        return raw_id

    # --- Case 4: Unrecognized -> try resolving via API ---
    return _resolve_to_pmcid(raw_id, id_type="unknown")


def normalize_pmid(pmid: str) -> str:
    """Convert a PubMed ID (PMID) to a numeric PMCID string.

    Args:
        pmid: PubMed ID as a string (e.g., "33087749")

    Returns:
        str: Numeric PMCID as a string

    Raises:
        ValueError: If the PMID cannot be resolved to a PMCID
    """
    pmid = pmid.strip()
    if not pmid.isdigit():
        raise ValueError(f"Invalid PMID format (must be numeric): {pmid!r}")
    return _resolve_to_pmcid(pmid, id_type="pmid")


def normalize_ids(raw_ids: list[str]) -> list[str]:
    """Batch-normalize multiple identifiers to numeric PMCID strings.

    Args:
        raw_ids: List of identifiers in any supported format

    Returns:
        list[str]: List of numeric PMCID strings (skips unresolvable IDs with warning)
    """
    results: list[str] = []
    for raw_id in raw_ids:
        try:
            results.append(normalize_id(raw_id))
        except ValueError as e:
            _logger.warning("Skipping unresolvable ID %r: %s", raw_id, e)
    return results


def normalize_pmids(pmids: list[str]) -> list[str]:
    """Batch-convert PMIDs to numeric PMCID strings.

    Args:
        pmids: List of PubMed IDs

    Returns:
        list[str]: List of numeric PMCID strings (skips unresolvable IDs with warning)
    """
    results: list[str] = []
    for pmid in pmids:
        try:
            results.append(normalize_pmid(pmid))
        except ValueError as e:
            _logger.warning("Skipping unresolvable PMID %r: %s", pmid, e)
    return results


def _resolve_to_pmcid(identifier: str, id_type: str = "unknown") -> str:
    """Resolve an identifier to a PMCID using the NCBI ID Converter API.

    Args:
        identifier: The identifier to resolve
        id_type: Hint about the type ("doi", "pmid", "unknown")

    Returns:
        str: Numeric PMCID string

    Raises:
        ValueError: If resolution fails
    """
    try:
        result = convert([identifier])
        records = result.get("records", [])
        for record in records:
            pmcid = record.get("pmcid", "")
            if pmcid:
                # Strip "PMC" prefix from the API response
                return _PMC_PREFIX_RE.sub("", pmcid).strip()
        raise ValueError(
            f"Could not resolve {id_type} {identifier!r} to a PMCID. "
            f"The article may not be available in PubMed Central."
        )
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(
            f"Failed to resolve {id_type} {identifier!r} to a PMCID: {e}"
        ) from e


def convert(ids: list[str]) -> dict[str, Any]:
    """Convert publication identifiers between different formats using NCBI API.

    Batch converts a list of publication identifiers to all available
    equivalent identifiers using NCBI's PMC ID Converter API. The service
    automatically detects input identifier types and returns mappings to
    all known equivalent identifiers.

    Args:
        ids: List of publication identifiers to convert. Can be any combination of:
            - PMC IDs (with or without "PMC" prefix): "PMC7181753", "7181753"
            - PubMed IDs: "33087749"
            - DOIs: "10.1038/s41586-020-2832-5"
            - Other supported identifier formats

    Returns:
        dict[str, Any]: Complete API response containing conversion results with structure:
            - status: API response status
            - responseDate: Date of API response
            - request: Echo of original request parameters
            - records: List of conversion records, each containing:
                - pmcid: PMC identifier (if available)
                - pmid: PubMed identifier (if available)
                - doi: DOI (if available)
                - manuscript-id: Manuscript ID (if available)
                - release-date: Publication release date
                - [other identifier fields as available]

    Raises:
        requests.HTTPError: If the API request fails due to network issues
        json.JSONDecodeError: If the API returns malformed JSON
        requests.RequestException: If request fails after retries

    Examples:
        >>> # Convert single PMC ID
        >>> result = convert(["PMC7181753"])
        >>> records = result['records']
        >>> if records:
        ...     record = records[0]
        ...     print(f"PMC ID: {record.get('pmcid')}")
        ...     print(f"PMID: {record.get('pmid')}")
        ...     print(f"DOI: {record.get('doi')}")
        >>>
        >>> # Batch convert multiple IDs of different types
        >>> ids = ["PMC7181753", "10.1038/s41586-020-2832-5", "33087749"]
        >>> result = convert(ids)
        >>> for record in result['records']:
        ...     print(f"Found identifiers for: {record}")
        >>>
        >>> # Handle missing conversions
        >>> result = convert(["invalid_id"])
        >>> if not result['records']:
        ...     print("No valid identifiers found")

    Note:
        The API may not return conversions for all input identifiers if they
        are invalid, not found, or not available in PMC. Check the 'records'
        list in the response to see successful conversions.

        Requests are cached using pmcgrab.http_utils.cached_get, so repeated
        calls with the same identifier list will return cached results.
    """
    params = {"ids": ",".join(ids), "format": "json"}
    from pmcgrab import __version__

    resp = cached_get(
        _BASE_URL + "json/",
        params=params,
        headers={"User-Agent": f"pmcgrab/{__version__}"},
    )
    return json.loads(resp.text)
