"""High-level helper that constructs a :class:`pmcgrab.model.Paper` from PMC.

This lives in the *application* layer to keep the domain entity (`Paper`)
free of infrastructure details such as network calls, retries, or XML
parsing.
"""

from __future__ import annotations

import time
from urllib.error import HTTPError

from pmcgrab.model import Paper
from pmcgrab.parser import paper_dict_from_pmc

__all__: list[str] = ["build_paper_from_pmc"]


# NOTE: retry / back-off logic kept identical to the original implementation to
# preserve existing behaviour.


def build_paper_from_pmc(
    pmcid: int,
    *,
    email: str,
    download: bool = False,
    validate: bool = True,
    verbose: bool = False,
    suppress_warnings: bool = False,
    suppress_errors: bool = False,
    attempts: int = 3,
) -> Paper | None:
    """Build a complete Paper instance from PMC ID with retry logic.

    High-level application service that orchestrates the complete paper
    construction process: XML fetching, parsing, validation, and Paper
    object creation. Includes automatic retry logic with exponential
    backoff for handling transient network failures.

    This function serves as the main entry point for creating Paper objects
    and provides a clean separation between the domain model (Paper) and
    infrastructure concerns (XML fetching, parsing).

    Args:
        pmcid: PubMed Central ID of the target article
        email: Contact email required by NCBI Entrez API
        download: If True, cache raw XML locally for reuse
        validate: If True, perform DTD validation of XML structure
        verbose: If True, emit detailed progress messages
        suppress_warnings: If True, suppress parsing warnings
        suppress_errors: If True, continue processing despite errors
        attempts: Maximum number of retry attempts for network failures (default: 3)

    Returns:
        Paper | None: Complete Paper instance with all parsed content,
                     or None if article could not be retrieved/parsed

    Examples:
        >>> # Basic usage
        >>> paper = build_paper_from_pmc(7181753, email="user@example.com")
        >>> if paper:
        ...     print(f"Title: {paper.title}")
        ...     print(f"Authors: {len(paper.authors)}")
        >>>
        >>> # With error handling and retries
        >>> paper = build_paper_from_pmc(
        ...     7181753,
        ...     email="user@example.com",
        ...     attempts=5,
        ...     suppress_errors=True,
        ...     verbose=True
        ... )

    Note:
        This function mirrors the legacy Paper.from_pmc() API to enable
        easy migration while providing cleaner separation of concerns.
        Network failures trigger automatic retries with 5-second delays.
    """
    d: dict | None = None
    for _ in range(attempts):
        try:
            d = paper_dict_from_pmc(
                pmcid,
                email=email,
                download=download,
                validate=validate,
                verbose=verbose,
                suppress_warnings=suppress_warnings,
                suppress_errors=suppress_errors,
            )
            break
        except HTTPError:
            time.sleep(5)

    if not d:
        return None
    return Paper(d)
