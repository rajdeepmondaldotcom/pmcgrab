"""NCBI PMC OAI-PMH (Open Archives Initiative Protocol for Metadata Harvesting) client.

This module provides a comprehensive interface to NCBI's PMC OAI-PMH service,
enabling systematic harvesting of metadata from the PubMed Central repository.
OAI-PMH is a protocol for metadata harvesting that allows efficient bulk
access to repository metadata.

The PMC OAI-PMH service enables researchers and developers to:
* Harvest metadata for large collections of articles
* Perform incremental harvesting based on date ranges
* Access different metadata formats (PMC, Dublin Core, etc.)
* Navigate collections using set specifications

Key Features:
    * Complete OAI-PMH verb implementation (ListRecords, GetRecord, etc.)
    * Automatic resumption token handling for large result sets
    * Multiple metadata format support
    * Date-based selective harvesting
    * Set-based collection filtering
    * Lazy iteration for memory-efficient processing

Supported OAI-PMH Verbs:
    * ListRecords: Harvest multiple metadata records
    * GetRecord: Retrieve single record by identifier
    * ListIdentifiers: Harvest just the identifiers
    * ListSets: Discover available collections/sets

Supported Metadata Formats:
    * pmc: PMC-specific metadata format (default)
    * oai_dc: Dublin Core metadata format
    * pmc_fm: PMC front matter format

API Endpoint:
    https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi

OAI-PMH Documentation:
    https://www.openarchives.org/OAI/openarchivesprotocol.html

Functions:
    list_records: Harvest multiple records with automatic pagination
    get_record: Retrieve single record by OAI identifier
    list_identifiers: Harvest identifiers only (lightweight)
    list_sets: Discover available collections/sets
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Generator, Iterator

from pmcgrab.http_utils import cached_get

_BASE_URL = "https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi"


class OAIPMHError(RuntimeError):
    """Exception raised when OAI-PMH protocol errors occur.

    This exception is raised when the OAI-PMH service returns an error
    response, such as invalid parameters, unsupported verbs, or repository
    errors. The exception message contains the error details from the service.

    Common error scenarios:
        * badArgument: Invalid or missing required arguments
        * badVerb: Unsupported or misspelled OAI-PMH verb
        * cannotDisseminateFormat: Requested metadata format not supported
        * idDoesNotExist: Requested identifier not found
        * noRecordsMatch: No records match the specified criteria
    """


# ---------------------- Low-level helpers -----------------------------


def _request(verb: str, **params) -> ET.Element:
    """Execute OAI-PMH request with error handling.

    Internal helper function that constructs and executes OAI-PMH requests
    to the PMC service. Handles parameter formatting, HTTP communication,
    and OAI-PMH error response parsing.

    Args:
        verb: OAI-PMH verb (ListRecords, GetRecord, etc.)
        **params: Additional OAI-PMH parameters for the request

    Returns:
        ET.Element: Parsed XML response root element

    Raises:
        OAIPMHError: If the OAI-PMH service returns an error response
        requests.RequestException: If HTTP request fails
        xml.etree.ElementTree.ParseError: If response XML is malformed
    """
    q = {"verb": verb, **params}
    resp = cached_get(_BASE_URL, params=q, headers={"User-Agent": "pmcgrab/0.5.5"})
    root = ET.fromstring(resp.content)
    error = root.find("{*}error")
    if error is not None:
        raise OAIPMHError(error.text or "Unknown OAI-PMH error")
    return root


def _extract_records(root: ET.Element) -> list[ET.Element]:
    """Extract record elements from ListRecords response.

    Internal helper that parses ListRecords XML responses to extract
    individual record elements for processing.

    Args:
        root: Root element of OAI-PMH ListRecords response

    Returns:
        list[ET.Element]: List of record elements found in the response
    """
    return root.findall("{*}ListRecords/{*}record")


def _get_resumption_token(root: ET.Element) -> str | None:
    """Extract resumption token from OAI-PMH response if present.

    OAI-PMH uses resumption tokens to handle large result sets by
    breaking them into manageable chunks. This function extracts
    the token needed to request the next batch of results.

    Args:
        root: Root element of OAI-PMH response

    Returns:
        str | None: Resumption token for next batch, or None if no more results
    """
    token = root.find(".//{*}resumptionToken")
    return token.text if token is not None and token.text else None


# ---------------------- Public API ------------------------------------


def list_records(
    metadata_prefix: str = "pmc",
    from_: str | None = None,
    until: str | None = None,
    set_: str | None = None,
) -> Iterator[ET.Element]:
    """Harvest metadata records from PMC repository with automatic pagination.

    Implements the OAI-PMH ListRecords verb to harvest multiple metadata records
    from the PMC repository. Automatically handles large result sets by following
    resumption tokens, providing a seamless iterator interface for processing
    potentially millions of records.

    Args:
        metadata_prefix: Metadata format to harvest. Supported formats:
                        - "pmc": PMC-specific metadata format (default)
                        - "oai_dc": Dublin Core metadata format
                        - "pmc_fm": PMC front matter format
        from_: Start date for selective harvesting (ISO 8601 format: YYYY-MM-DD)
               Only records modified on or after this date are included
        until: End date for selective harvesting (ISO 8601 format: YYYY-MM-DD)
               Only records modified on or before this date are included
        set_: Set specification for collection-based harvesting
              Use list_sets() to discover available collections

    Yields:
        ET.Element: Individual record elements containing metadata and header information.
                   Each record includes header (identifier, datestamp, setSpec) and
                   metadata sections in the requested format.

    Raises:
        OAIPMHError: If OAI-PMH service returns protocol errors
        requests.RequestException: If HTTP requests fail
        xml.etree.ElementTree.ParseError: If response XML is malformed

    Examples:
        >>> # Harvest all PMC records (warning: very large!)
        >>> for record in list_records():
        ...     identifier = record.find(".//{*}identifier").text
        ...     print(f"Processing {identifier}")
        ...     # Process first 10 records only for demo
        ...     if identifier.endswith("10"):
        ...         break
        >>>
        >>> # Harvest records from specific date range
        >>> for record in list_records(from_="2023-01-01", until="2023-01-31"):
        ...     datestamp = record.find(".//{*}datestamp").text
        ...     print(f"Record from {datestamp}")
        >>>
        >>> # Harvest specific collection in Dublin Core format
        >>> for record in list_records(metadata_prefix="oai_dc", set_="pmc-open"):
        ...     title = record.find(".//{*}title")
        ...     if title is not None:
        ...         print(f"Title: {title.text}")

    Performance Notes:
        * Uses lazy iteration - records are fetched in batches as needed
        * Automatic resumption token handling for seamless large-scale harvesting
        * Memory efficient - only current batch is kept in memory
        * Respects repository rate limits through cached HTTP requests
        * Can process millions of records without memory issues

    Date Format:
        Dates should be in ISO 8601 format (YYYY-MM-DD). Examples:
        * "2023-01-01": January 1, 2023
        * "2023-12-31": December 31, 2023
        * Combined: from_="2023-01-01", until="2023-12-31"

    Note:
        This function can return very large numbers of records (millions).
        Always use appropriate filtering (date ranges, sets) and implement
        proper processing logic to handle the data volume efficiently.
    """
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
    """Retrieve single metadata record by OAI identifier.

    Implements the OAI-PMH GetRecord verb to fetch a specific metadata record
    using its OAI identifier. This is useful for retrieving individual records
    when you know the exact identifier.

    Args:
        identifier: OAI identifier for the record (e.g., "oai:pubmedcentral.nih.gov:PMC7181753")
                   OAI identifiers follow the format: oai:repository:localid
        metadata_prefix: Metadata format to retrieve:
                        - "pmc": PMC-specific metadata format (default)
                        - "oai_dc": Dublin Core metadata format
                        - "pmc_fm": PMC front matter format

    Returns:
        ET.Element: Complete record element containing header and metadata sections
                   in the requested format

    Raises:
        OAIPMHError: If identifier doesn't exist or other protocol errors occur
        requests.RequestException: If HTTP request fails
        xml.etree.ElementTree.ParseError: If response XML is malformed

    Examples:
        >>> # Get specific record in PMC format
        >>> record = get_record("oai:pubmedcentral.nih.gov:PMC7181753")
        >>> identifier = record.find(".//{*}identifier").text
        >>> print(f"Retrieved: {identifier}")
        >>>
        >>> # Get record in Dublin Core format
        >>> record = get_record(
        ...     "oai:pubmedcentral.nih.gov:PMC7181753",
        ...     metadata_prefix="oai_dc"
        ... )
        >>> title = record.find(".//{*}title").text
        >>> print(f"Title: {title}")

    OAI Identifier Format:
        PMC OAI identifiers have the format:
        oai:pubmedcentral.nih.gov:PMC{PMCID}

        Example: oai:pubmedcentral.nih.gov:PMC7181753

        Use list_identifiers() to discover available identifiers.

    Note:
        This function retrieves exactly one record. For bulk harvesting,
        use list_records() which is more efficient for large-scale operations.
    """
    root = _request("GetRecord", identifier=identifier, metadataPrefix=metadata_prefix)
    return root.find("{*}GetRecord/{*}record")  # type: ignore


def list_identifiers(
    metadata_prefix: str = "pmc",
    from_: str | None = None,
    until: str | None = None,
    set_: str | None = None,
) -> Generator[str, None, None]:
    """Harvest only identifiers from PMC repository (lightweight alternative).

    Implements the OAI-PMH ListIdentifiers verb to harvest just the OAI identifiers
    without the full metadata records. This is much more bandwidth and memory
    efficient when you only need to discover what records are available.

    Args:
        metadata_prefix: Metadata format scope (determines which records are included):
                        - "pmc": PMC-specific format records (default)
                        - "oai_dc": Dublin Core format records
                        - "pmc_fm": PMC front matter format records
        from_: Start date for selective harvesting (ISO 8601: YYYY-MM-DD)
        until: End date for selective harvesting (ISO 8601: YYYY-MM-DD)
        set_: Set specification for collection-based harvesting

    Yields:
        str: OAI identifiers in format "oai:pubmedcentral.nih.gov:PMC{ID}"

    Raises:
        OAIPMHError: If OAI-PMH service returns protocol errors
        requests.RequestException: If HTTP requests fail
        xml.etree.ElementTree.ParseError: If response XML is malformed

    Examples:
        >>> # Discover all available PMC identifiers (warning: very large!)
        >>> count = 0
        >>> for identifier in list_identifiers():
        ...     print(identifier)
        ...     count += 1
        ...     if count >= 10:  # Show first 10 only
        ...         break
        >>>
        >>> # Find identifiers for recent additions
        >>> recent_ids = list(list_identifiers(from_="2023-12-01"))
        >>> print(f"Found {len(recent_ids)} recent additions")
        >>>
        >>> # Get identifiers for specific collection
        >>> collection_ids = list(list_identifiers(set_="pmc-open"))
        >>> print(f"Collection contains {len(collection_ids)} articles")

    Use Cases:
        * Discovering available records before bulk harvesting
        * Monitoring repository for new additions
        * Building local identifier indexes
        * Validating identifier availability before GetRecord calls
        * Bandwidth-efficient repository surveys

    Performance Benefits:
        * Much faster than list_records() - no metadata transfer
        * Lower bandwidth usage - only identifiers transferred
        * Efficient for large-scale repository surveys
        * Automatic pagination handling via resumption tokens

    Note:
        Identifiers returned can be used directly with get_record() to fetch
        the full metadata when needed. This two-stage approach is often more
        efficient than harvesting all records immediately.
    """
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
    """Discover available collections/sets in the PMC repository.

    Implements the OAI-PMH ListSets verb to retrieve information about
    collections or sets available in the PMC repository. Sets allow
    for selective harvesting of specific collections or categories of records.

    Returns:
        list[dict[str, str]]: List of set dictionaries, each containing:
            - "setSpec": Set specification identifier for use in harvesting
            - "setName": Human-readable set name/description

    Raises:
        OAIPMHError: If OAI-PMH service returns protocol errors
        requests.RequestException: If HTTP request fails
        xml.etree.ElementTree.ParseError: If response XML is malformed

    Examples:
        >>> # Discover all available sets
        >>> sets = list_sets()
        >>> for set_info in sets:
        ...     print(f"Set: {set_info['setName']} (spec: {set_info['setSpec']})")
        >>>
        >>> # Find specific set for harvesting
        >>> sets = list_sets()
        >>> open_access_sets = [s for s in sets if 'open' in s['setName'].lower()]
        >>> for set_info in open_access_sets:
        ...     print(f"Open Access set: {set_info['setSpec']}")
        >>>
        >>> # Use set specification for targeted harvesting
        >>> sets = list_sets()
        >>> target_set = sets[0]['setSpec']  # Use first available set
        >>> for record in list_records(set_=target_set):
        ...     # Process records from specific collection
        ...     break

    Set Usage:
        Set specifications returned by this function can be used with:
        * list_records(set_="setspec") - Harvest records from specific collection
        * list_identifiers(set_="setspec") - Get identifiers from specific collection

    Common PMC Sets:
        PMC typically provides sets organized by:
        * Subject areas or disciplines
        * Open Access status
        * Journal collections
        * Special collections or projects

    Note:
        Not all OAI-PMH repositories support sets. PMC provides set support
        for organized access to different collections within the repository.
        Sets enable more targeted harvesting than date-based filtering alone.
    """
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
