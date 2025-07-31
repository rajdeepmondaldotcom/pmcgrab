"""Author and contributor information extraction for PMC articles.

This module provides specialized functions for extracting and structuring
author and contributor information from PMC XML documents. It handles the
complex relationships between contributors, their affiliations, identifiers,
and roles in the research process.

The module produces structured pandas DataFrames that contain comprehensive
bibliographic information suitable for citation generation, author analysis,
and research collaboration studies.

Key Features:
    * **Comprehensive Author Data**: Names, emails, affiliations, identifiers
    * **Contributor Classifications**: Authors, editors, reviewers, and other roles
    * **Institutional Affiliations**: Detailed affiliation parsing and linking
    * **Persistent Identifiers**: ORCID, ISNI, and other researcher identifiers
    * **Contribution Metadata**: Equal contribution flags and role specifications
    * **Structured Output**: Clean pandas DataFrames for downstream analysis

Data Extraction Scope:
    * **Author Information**: Primary research contributors
    * **Non-Author Contributors**: Editors, reviewers, acknowledgees
    * **Contact Details**: Email addresses and correspondence information
    * **Institutional Data**: Affiliations with detailed organization information
    * **Identifier Systems**: ORCID IDs for persistent author identification

Output Format:
    All functions return pandas DataFrames with standardized column structures
    that enable consistent analysis across different articles and publishers.
    The structured format supports both human readability and machine processing.

Functions:
    extract_contributor_info: Core contributor data extraction engine
    gather_authors: Extract primary author information as DataFrame
    gather_non_author_contributors: Extract non-author contributor information
"""

from __future__ import annotations

import warnings

import lxml.etree as ET
import pandas as pd

from pmcgrab.constants import UnexpectedMultipleMatchWarning, UnexpectedZeroMatchWarning

__all__: list[str] = [
    "extract_contributor_info",
    "gather_authors",
    "gather_non_author_contributors",
]


def extract_contributor_info(
    root: ET.Element, contributors: list[ET.Element]
) -> list[tuple]:
    """Extract comprehensive contributor information from PMC XML elements.

    Core function that processes contributor XML elements to extract all
    available metadata including names, affiliations, identifiers, and
    role information. This function handles the complex XML structure
    and cross-references used in PMC author metadata.

    Args:
        root: Root element of the PMC XML document for affiliation lookups
        contributors: List of contributor XML elements to process

    Returns:
        list[tuple]: List of contributor tuples, each containing:
            (contributor_type, first_name, last_name, email, affiliations,
             orcid, isni, equal_contrib_flag)

    Processing Features:
        * Name parsing with given names and surnames
        * Email address extraction and normalization
        * Affiliation resolution through ID cross-references
        * ORCID and ISNI identifier extraction
        * Equal contribution flag detection
        * Contributor type classification

    Warnings:
        * UnexpectedMultipleMatchWarning: When multiple affiliations exist for one ID

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> authors = root.xpath(".//contrib[@contrib-type='author']")
        >>> author_data = extract_contributor_info(root, authors)
        >>> for contributor in author_data:
        ...     ctype, first, last, email, affils, orcid, isni, equal = contributor
        ...     print(f"{first} {last} ({ctype})")
        ...     if orcid:
        ...         print(f"  ORCID: {orcid}")

    Data Structure:
        Each tuple contains the following elements:
        0. contributor_type (str): Role type (e.g., "Author", "Editor")
        1. first_name (str|None): Given names
        2. last_name (str|None): Surname
        3. email (str|None): Email address
        4. affiliations (list[str]): List of affiliation strings
        5. orcid (str|None): ORCID identifier
        6. isni (str|None): ISNI identifier
        7. equal_contrib (bool): Equal contribution flag

    Affiliation Processing:
        * Resolves affiliation IDs to full institutional information
        * Combines institution names with location details
        * Handles missing or incomplete affiliation data gracefully
        * Formats affiliations as "ID: Institution Location"

    Note:
        This function is the core processor for all contributor types and
        provides the foundation for both author and non-author contributor
        DataFrames. It handles the complexity of PMC XML contributor structures.
    """
    result = []
    for contrib in contributors:
        ctype = (contrib.get("contrib-type") or "").capitalize().strip()
        first = contrib.findtext(".//given-names")
        first = first.strip() if first else None
        last = contrib.findtext(".//surname")
        last = last.strip() if last else None
        addr = contrib.findtext(".//address/email")
        addr = addr.strip() if addr else None

        # affiliations ------------------------------------------------------
        affils: list[str] = []
        for aff in contrib.xpath(".//xref[@ref-type='aff']"):
            aid = aff.get("rid")
            texts = root.xpath(
                f"//contrib-group/aff[@id='{aid}']/text()[not(parent::label)]"
            )
            if len(texts) > 1:
                warnings.warn(
                    "Multiple affiliations found for one ID.",
                    UnexpectedMultipleMatchWarning,
                    stacklevel=2,
                )
            if not texts:
                texts = ["Affiliation data not found."]
            inst = root.xpath(
                f"//contrib-group/aff[@id='{aid}']/institution-wrap/institution/text()"
            )
            inst_str = " ".join(str(i) for i in inst)
            affils.append(
                f"{aid.strip()}: {inst_str}{texts[0].strip()}"
                if inst_str
                else f"{aid.strip()}: {texts[0].strip()}"
            )

        orcid = contrib.findtext(".//contrib-id[@contrib-id-type='orcid']")
        isni = contrib.findtext(".//contrib-id[@contrib-id-type='isni']")
        equal_flag = contrib.get("equal-contrib") == "yes"

        result.append((ctype, first, last, addr, affils, orcid, isni, equal_flag))
    return result


def gather_authors(root: ET.Element) -> pd.DataFrame | None:
    """Extract primary author information as structured DataFrame.

    Retrieves all authors (primary research contributors) from the PMC article
    and returns their information in a structured pandas DataFrame suitable
    for bibliographic analysis, citation generation, and author studies.

    Args:
        root: Root element of the PMC XML document

    Returns:
        pd.DataFrame | None: DataFrame containing author information with columns:
            - Contributor_Type: Role type (typically "Author")
            - First_Name: Given names
            - Last_Name: Surname
            - Email_Address: Contact email
            - Affiliations: List of institutional affiliations
            - ORCID: ORCID identifier for persistent author identification
            - ISNI: ISNI identifier (International Standard Name Identifier)
            - Equal_Contrib: Boolean flag for equal contribution status
        Returns None if no authors are found.

    Warnings:
        * UnexpectedZeroMatchWarning: When no authors are found in the document
        * UnexpectedMultipleMatchWarning: When affiliation resolution issues occur

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> authors_df = gather_authors(root)
        >>> if authors_df is not None:
        ...     print(f"Found {len(authors_df)} authors")
        ...     print(authors_df[['First_Name', 'Last_Name', 'ORCID']].head())
        >>>
        >>> # Access individual author information
        >>> if authors_df is not None:
        ...     for idx, author in authors_df.iterrows():
        ...         name = f"{author['First_Name']} {author['Last_Name']}"
        ...         print(f"Author: {name}")
        ...         if author['ORCID']:
        ...             print(f"  ORCID: {author['ORCID']}")
        ...         if author['Affiliations']:
        ...             print(f"  Affiliations: {len(author['Affiliations'])}")

    DataFrame Structure:
        The returned DataFrame provides comprehensive author metadata with:
        * Standardized column names for consistent access
        * Proper data types for each field
        * List structures for multi-value fields (affiliations)
        * Boolean flags for binary attributes (equal contribution)

    Use Cases:
        * **Citation Generation**: Extract names and affiliations for proper citations
        * **Author Analysis**: Study collaboration patterns and institutional networks
        * **Bibliometrics**: Analyze author productivity and collaboration
        * **Contact Information**: Identify corresponding authors and email contacts
        * **Identifier Resolution**: Link authors across publications via ORCID

    Data Quality:
        * Handles missing names, emails, and identifiers gracefully
        * Normalizes text fields by stripping whitespace
        * Resolves institutional affiliations through cross-references
        * Preserves equal contribution metadata for author ordering

    Note:
        This function focuses specifically on primary authors (contrib-type='author').
        For other contributor types (editors, reviewers, etc.), use
        gather_non_author_contributors(). The DataFrame format enables easy
        integration with bibliometric analysis tools and citation managers.
    """
    authors = root.xpath(".//contrib[@contrib-type='author']")
    if not authors:
        warnings.warn("No authors found.", UnexpectedZeroMatchWarning, stacklevel=2)
        return None
    data = extract_contributor_info(root, authors)
    return pd.DataFrame(
        data,
        columns=[
            "Contributor_Type",
            "First_Name",
            "Last_Name",
            "Email_Address",
            "Affiliations",
            "ORCID",
            "ISNI",
            "Equal_Contrib",
        ],
    )


def gather_non_author_contributors(root: ET.Element) -> str | pd.DataFrame:
    """Extract non-author contributor information as structured DataFrame.

    Retrieves information about contributors who are not primary authors,
    such as editors, reviewers, translators, and other roles in the
    publication process. This provides comprehensive metadata about
    all individuals involved in the article's creation and review.

    Args:
        root: Root element of the PMC XML document

    Returns:
        str | pd.DataFrame: DataFrame containing non-author contributor information
                           with the same column structure as gather_authors(),
                           or string message if no non-author contributors exist.

        DataFrame columns (when contributors exist):
            - Contributor_Type: Role type (e.g., "Editor", "Reviewer", "Translator")
            - First_Name: Given names
            - Last_Name: Surname
            - Email_Address: Contact email
            - Affiliations: List of institutional affiliations
            - ORCID: ORCID identifier
            - ISNI: ISNI identifier
            - Equal_Contrib: Boolean flag (typically False for non-authors)

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> non_authors = gather_non_author_contributors(root)
        >>> if isinstance(non_authors, pd.DataFrame):
        ...     print(f"Found {len(non_authors)} non-author contributors")
        ...     role_counts = non_authors['Contributor_Type'].value_counts()
        ...     print("Contributor roles:")
        ...     print(role_counts)
        >>> else:
        ...     print(non_authors)  # String message for no contributors

    Common Non-Author Roles:
        * **Editor**: Journal or section editors
        * **Reviewer**: Peer reviewers (when disclosed)
        * **Translator**: Language translators
        * **Illustrator**: Figure and graphic creators
        * **Data Curator**: Data management contributors
        * **Software Developer**: Tool and software contributors

    Processing Features:
        * Same comprehensive extraction as authors
        * Role-based categorization and analysis
        * Complete institutional affiliation resolution
        * Identifier extraction for persistent identification
        * Consistent DataFrame structure for combined analysis

    Use Cases:
        * **Editorial Analysis**: Study editorial board composition and roles
        * **Peer Review Studies**: Analyze reviewer disclosure patterns
        * **Collaboration Networks**: Map extended collaboration beyond authorship
        * **Role Attribution**: Credit non-traditional research contributions
        * **Quality Assessment**: Evaluate editorial and review processes

    Data Integration:
        * Compatible DataFrame structure with gather_authors()
        * Enables combined analysis of all contributors
        * Supports role-based filtering and analysis
        * Consistent identifier systems across contributor types

    Return Type Handling:
        The function returns either a DataFrame (when contributors exist) or
        a string message (when none exist). This dual return type should be
        checked before processing:

        >>> result = gather_non_author_contributors(root)
        >>> if isinstance(result, pd.DataFrame):
        ...     # Process DataFrame
        ...     contributor_analysis(result)
        >>> else:
        ...     # Handle no contributors case
        ...     print("No non-author contributors to analyze")

    Note:
        Non-author contributors provide valuable context about the broader
        scholarly community involved in article creation and review. This
        information is increasingly important for understanding research
        collaboration networks and giving proper credit to all contributors.
    """
    non_auth = root.xpath(".//contrib[not(@contrib-type='author')]")
    if non_auth:
        data = extract_contributor_info(root, non_auth)
        return pd.DataFrame(
            data,
            columns=[
                "Contributor_Type",
                "First_Name",
                "Last_Name",
                "Email_Address",
                "Affiliations",
                "ORCID",
                "ISNI",
                "Equal_Contrib",
            ],
        )
    return "No non-author contributors found."
