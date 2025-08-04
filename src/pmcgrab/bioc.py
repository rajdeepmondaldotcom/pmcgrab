"""BioC RESTful API client for PMC Open Access articles.

This module provides a simple interface to NCBI's BioC RESTful API, which
offers access to PubMed Central Open Access articles in BioC JSON format.
The BioC format is specifically designed for biomedical text mining and
natural language processing applications.

The BioC API provides structured document representations including:
* Document metadata and passages
* Annotations and relations
* Sentence and token boundaries
* Named entity recognition results

Key Features:
    * Cached HTTP requests for improved performance
    * Simple one-function interface
    * Raw JSON dictionary return for maximum flexibility
    * Automatic User-Agent header for API compliance

API Endpoint:
    Base URL: https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/
    Example: https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/PMC7181753

Note:
    This API only works with Open Access PMC articles. Non-OA articles
    will return error responses or empty content.
"""

from __future__ import annotations

import json
from typing import Any

from pmcgrab.http_utils import cached_get

_BASE_URL = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/"


def fetch_json(pmcid: str) -> dict[str, Any]:
    """Fetch BioC JSON data for a PMC Open Access article.

    Retrieves structured document data from NCBI's BioC RESTful API for
    the specified PMC article. The BioC format includes document passages,
    annotations, and metadata optimized for text mining applications.

    Args:
        pmcid: PMC identifier (with or without "PMC" prefix, e.g., "7181753" or "PMC7181753")

    Returns:
        dict[str, Any]: Complete BioC JSON document structure containing:
            - source: Data source information
            - date: Processing date
            - key: Document identifier
            - infons: Document metadata
            - passages: List of document passages with text and annotations
            - relations: Inter-annotation relationships
            - annotations: Document-level annotations

    Raises:
        HTTPError: If the API request fails (network issues, invalid PMCID, non-OA article)
        JSONDecodeError: If the API returns malformed JSON

    Examples:
        >>> # Fetch BioC data for an Open Access article
        >>> bioc_data = fetch_json("7181753")
        >>> print(f"Document key: {bioc_data['key']}")
        >>> print(f"Number of passages: {len(bioc_data['passages'])}")
        >>>
        >>> # Access passage text
        >>> for passage in bioc_data['passages']:
        ...     print(f"Passage type: {passage['infons']['type']}")
        ...     print(f"Text: {passage['text'][:100]}...")

    Note:
        This function only works with Open Access PMC articles. Attempting
        to fetch non-OA articles will result in API errors. The response
        is cached using pmcgrab.http_utils.cached_get for performance.
    """
    url = _BASE_URL + pmcid
    resp = cached_get(url, headers={"User-Agent": "pmcgrab/0.5.7"})
    return json.loads(resp.text)
