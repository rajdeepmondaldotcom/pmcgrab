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
"""

from __future__ import annotations

import json
from typing import Any

from pmcgrab.http_utils import cached_get

_BASE_URL = "https://pmc.ncbi.nlm.nih.gov/tools/idconv/v1.0/"  # new API path


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
    resp = cached_get(
        _BASE_URL + "json/", params=params, headers={"User-Agent": "pmcgrab/0.5.7"}
    )
    return json.loads(resp.text)
