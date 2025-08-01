"""NCBI Literature Citation Exporter API client for formatted citations.

This module provides a simple interface to NCBI's Literature Citation Exporter
(lit/ctxp) API, which generates properly formatted citations for PMC articles
in various standard academic and reference management formats.

The Citation Exporter is useful for generating properly formatted citations
for inclusion in bibliographies, reference lists, or import into reference
management software like EndNote, Zotero, or Mendeley.

Key Features:
    * Multiple citation format support (MEDLINE, RIS, BibTeX, etc.)
    * Automatic formatting according to citation standards
    * Cached HTTP requests for improved performance
    * Clean text output ready for use or further processing
    * Integration with PMC article database

Supported Citation Formats:
    * medline: MEDLINE format (default)
    * ris: Research Information Systems format
    * bibtex: BibTeX format for LaTeX documents
    * nbib: NCBI Bibliography format
    * pubmed: PubMed format
    * pmid: PubMed ID list format

API Endpoint:
    Base URL: https://api.ncbi.nlm.nih.gov/lit/ctxp/v1/pmc/
    Example: https://api.ncbi.nlm.nih.gov/lit/ctxp/v1/pmc/?format=medline&id=PMC7181753

Functions:
    export: Generate formatted citation for a PMC article
"""

from __future__ import annotations

from pmcgrab.http_utils import cached_get

_BASE_URL = "https://api.ncbi.nlm.nih.gov/lit/ctxp/v1/pmc/"


def export(pmcid: str, fmt: str = "medline") -> str:
    """Export formatted citation for a PMC article in specified format.

    Generates a properly formatted citation for the specified PMC article
    using NCBI's Literature Citation Exporter API. The citation is formatted
    according to the specified standard and ready for use in bibliographies
    or import into reference management software.

    Args:
        pmcid: PMC identifier (with or without "PMC" prefix, e.g., "7181753" or "PMC7181753")
        fmt: Citation format to generate. Supported formats:
            - "medline": MEDLINE format (default) - structured text format
            - "ris": Research Information Systems format - for EndNote, Zotero
            - "bibtex": BibTeX format - for LaTeX documents
            - "nbib": NCBI Bibliography format
            - "pubmed": PubMed format
            - "pmid": PubMed ID list format

    Returns:
        str: Formatted citation text in the specified format, ready for use
             or import into reference management software

    Raises:
        requests.HTTPError: If the API request fails (invalid PMCID, network issues)
        requests.RequestException: If request fails after retries

    Examples:
        >>> # Generate MEDLINE format citation (default)
        >>> citation = export("PMC7181753")
        >>> print(citation)
        # Output: Structured MEDLINE format citation

        >>> # Generate BibTeX format for LaTeX documents
        >>> bibtex = export("7181753", fmt="bibtex")
        >>> print(bibtex)
        # Output: @article{...} BibTeX entry

        >>> # Generate RIS format for reference managers
        >>> ris_citation = export("PMC7181753", fmt="ris")
        >>> with open("citation.ris", "w") as f:
        ...     f.write(ris_citation)

        >>> # Batch export multiple citations
        >>> pmcids = ["PMC7181753", "PMC3539614", "PMC5454911"]
        >>> citations = [export(pmcid, "bibtex") for pmcid in pmcids]

    Format Examples:
        MEDLINE format includes structured fields like:
        - PMID, PMC, DOI
        - Author names and affiliations
        - Article title and journal information
        - Publication dates and volume/issue details

        BibTeX format produces LaTeX-compatible entries:
        @article{key,
          title={Article Title},
          author={Author, First and Second, Author},
          journal={Journal Name},
          year={2023},
          ...
        }

    Note:
        Citations are generated based on PMC database information and
        formatted according to standard citation guidelines. The API
        automatically handles proper formatting, punctuation, and field
        ordering for each format.

        Requests are cached, so repeated calls with the same PMCID and
        format will return cached results for improved performance.
    """
    params: dict[str, str] = {"format": fmt, "id": pmcid}
    resp = cached_get(_BASE_URL, params=params, headers={"User-Agent": "pmcgrab/0.5.5"})
    return resp.text
