"""Core bibliographic and journal metadata extraction for PMC articles.

This module provides pure functions for extracting standard bibliographic
metadata from PMC XML documents. All functions are side-effect-free and
designed for easy unit testing and reliable metadata extraction.

The module focuses on core scholarly metadata that is standardized across
most scientific articles: journal information, article identifiers,
publication dates, author information, and classification schemes.

Key Features:
    * **Pure Functions**: No side effects, easy to test and reason about
    * **Comprehensive Coverage**: All major bibliographic metadata fields
    * **Error Handling**: Graceful handling of missing or malformed metadata
    * **Warning System**: Alerts for data quality issues and unexpected structures
    * **Type Safety**: Full type annotations for reliable integration

Metadata Categories:
    * **Journal Information**: Titles, IDs, ISSN, publisher details
    * **Article Classification**: Types, categories, keywords, subjects
    * **Publication Data**: Dates, volume, issue, page numbers
    * **Identifiers**: DOI, PMID, PMC ID, and other persistent identifiers
    * **Temporal Information**: Publication history and revision dates

Design Principles:
    * Functions return None for missing data rather than raising exceptions
    * Warnings are issued for data quality concerns but processing continues
    * Multiple values are handled gracefully (first item or complete list)
    * Date parsing handles various formats and missing components
    * All output is JSON-serializable for downstream processing

Functions:
    gather_title: Extract article title
    gather_journal_id: Extract journal identifier mappings
    gather_journal_title: Extract journal title(s)
    gather_issn: Extract ISSN mappings by publication type
    gather_publisher_name: Extract publisher name(s)
    gather_publisher_location: Extract publisher location(s)
    gather_article_id: Extract article identifier mappings
    gather_article_types: Extract article type classifications
    gather_article_categories: Extract article category classifications
    gather_published_date: Extract publication date(s)
    gather_history_dates: Extract manuscript history dates
    gather_volume: Extract journal volume number
    gather_issue: Extract journal issue number
    gather_keywords: Extract keywords and subject terms
"""

from __future__ import annotations

import datetime
import warnings

import lxml.etree as ET

from pmcgrab.constants import UnexpectedMultipleMatchWarning, UnexpectedZeroMatchWarning

__all__: list[str] = [
    "gather_article_categories",
    # article identifiers / classification
    "gather_article_id",
    "gather_article_types",
    "gather_history_dates",
    "gather_issn",
    "gather_issue",
    # journal section
    "gather_journal_id",
    "gather_journal_title",
    # keywords
    "gather_keywords",
    # dates / versions
    "gather_published_date",
    "gather_publisher_location",
    "gather_publisher_name",
    # article title
    "gather_title",
    # "gather_version_history",  # moved to content.py
    # misc numeric
    "gather_volume",
]


# ---------------------------------------------------------------------------
# Simple single-value helpers
# ---------------------------------------------------------------------------


def gather_title(root: ET.Element) -> str | None:
    """Extract the main article title from PMC XML.

    Retrieves the primary article title, which is essential for article
    identification and citation. Handles cases where multiple titles
    exist by using the first one and issuing appropriate warnings.

    Args:
        root: Root element of the PMC XML document

    Returns:
        str | None: Article title text, or None if no title is found

    Warnings:
        * UnexpectedMultipleMatchWarning: When multiple titles exist (uses first)
        * UnexpectedZeroMatchWarning: When no title is found

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> title = gather_title(root)
        >>> if title:
        ...     print(f"Title: {title}")
        >>>
        >>> # Check title length for validation
        >>> if title and len(title) < 10:
        ...     print("Warning: Title seems unusually short")

    Title Characteristics:
        * Usually contains the main research question or findings
        * May include subtitles separated by colons
        * Can contain special characters and formatting
        * Length varies significantly across disciplines

    Note:
        The title is one of the most important metadata fields for
        article identification and search. Missing titles indicate
        significant structural issues with the XML document.
    """
    matches: list[str] = root.xpath("//article-title/text()")
    if len(matches) > 1:
        warnings.warn(
            "Multiple titles found; using the first.",
            UnexpectedMultipleMatchWarning,
            stacklevel=2,
        )
    if not matches:
        warnings.warn(
            "No article title found.", UnexpectedZeroMatchWarning, stacklevel=2
        )
        return None
    return matches[0]


# ---------------------------------------------------------------------------
# Journal-level metadata
# ---------------------------------------------------------------------------


def gather_journal_id(root: ET.Element) -> dict[str, str]:
    """Extract journal identifier mappings from PMC XML.

    Retrieves various journal identifiers used by different indexing systems
    and databases. These IDs are crucial for journal identification and
    cross-referencing across different scholarly databases.

    Args:
        root: Root element of the PMC XML document

    Returns:
        dict[str, str]: Dictionary mapping identifier types to values.
                       Common keys include "nlm-ta", "iso-abbrev", "publisher-id"

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> journal_ids = gather_journal_id(root)
        >>> if journal_ids:
        ...     for id_type, id_value in journal_ids.items():
        ...         print(f"{id_type}: {id_value}")
        >>>
        >>> # Check for specific identifier types
        >>> if "nlm-ta" in journal_ids:
        ...     print(f"NLM Title Abbreviation: {journal_ids['nlm-ta']}")

    Common Identifier Types:
        * "nlm-ta": NLM Title Abbreviation (standardized short form)
        * "iso-abbrev": ISO journal title abbreviation
        * "publisher-id": Publisher's internal journal identifier
        * "hwp": HighWire Press identifier

    Note:
        Journal IDs enable precise journal identification across different
        systems and are essential for bibliometric analysis and citation
        tracking. Different publishers may use different identifier schemes.
    """
    ids = root.xpath("//journal-meta/journal-id")
    return {jid.get("journal-id-type"): jid.text for jid in ids}


def gather_journal_title(root: ET.Element) -> list[str] | str | None:
    """Extract journal title(s) from PMC XML.

    Retrieves the journal title, which may include both full titles and
    abbreviated forms. Handles cases with multiple titles appropriately.

    Args:
        root: Root element of the PMC XML document

    Returns:
        list[str] | str | None: Single title string if one title exists,
                               list of titles if multiple exist,
                               or None if no titles are found

    Warnings:
        * UnexpectedZeroMatchWarning: When no journal title is found

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> journal_title = gather_journal_title(root)
        >>> if isinstance(journal_title, str):
        ...     print(f"Journal: {journal_title}")
        >>> elif isinstance(journal_title, list):
        ...     print(f"Journal titles: {', '.join(journal_title)}")

    Title Types:
        * Full journal titles (e.g., "Nature Biotechnology")
        * Abbreviated titles (e.g., "Nat Biotechnol")
        * Alternative language titles
        * Historical titles for journals that have changed names

    Note:
        Journal titles are essential for proper citation formatting and
        journal identification. Multiple titles may represent different
        formats or languages of the same journal name.
    """
    titles = [t.text for t in root.xpath("//journal-title")]
    if not titles:
        warnings.warn(
            "No journal title found.", UnexpectedZeroMatchWarning, stacklevel=2
        )
        return None
    return titles if len(titles) > 1 else titles[0]


def gather_issn(root: ET.Element) -> dict[str, str]:
    """Extract ISSN (International Standard Serial Number) mappings from PMC XML.

    Retrieves ISSN identifiers for different publication formats of the journal.
    ISSNs are standardized identifiers that uniquely identify serial publications.

    Args:
        root: Root element of the PMC XML document

    Returns:
        dict[str, str]: Dictionary mapping publication types to ISSN values.
                       Common keys include "print", "electronic", "linking"

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> issns = gather_issn(root)
        >>> if issns:
        ...     for pub_type, issn in issns.items():
        ...         print(f"{pub_type.title()} ISSN: {issn}")
        >>>
        >>> # Check for electronic ISSN
        >>> if "electronic" in issns:
        ...     print(f"e-ISSN: {issns['electronic']}")

    ISSN Types:
        * "print": Print publication ISSN (p-ISSN)
        * "electronic": Electronic publication ISSN (e-ISSN)
        * "linking": Linking ISSN for journal series
        * Other publisher-specific types

    ISSN Format:
        * 8-digit identifier in format XXXX-XXXX
        * Includes check digit for validation
        * Uniquely identifies the journal across all platforms

    Note:
        ISSNs are crucial for library cataloging, citation management,
        and journal identification across different platforms and formats.
        Most journals have separate ISSNs for print and electronic versions.
    """
    issns = root.xpath("//journal-meta/issn")
    return {issn.get("pub-type"): issn.text for issn in issns}


def gather_publisher_name(root: ET.Element) -> str | list[str]:
    """Extract publisher name(s) from PMC XML.

    Retrieves the name of the organization responsible for publishing
    the journal. Handles cases with multiple publishers appropriately.

    Args:
        root: Root element of the PMC XML document

    Returns:
        str | list[str]: Single publisher name if one exists,
                        list of names if multiple publishers exist

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> publisher = gather_publisher_name(root)
        >>> if isinstance(publisher, str):
        ...     print(f"Publisher: {publisher}")
        >>> elif isinstance(publisher, list):
        ...     print(f"Publishers: {', '.join(publisher)}")

    Publisher Information:
        * Commercial publishers (e.g., Elsevier, Springer Nature)
        * Academic society publishers (e.g., American Chemical Society)
        * University presses (e.g., Oxford University Press)
        * Open access publishers (e.g., PLOS, BioMed Central)

    Multiple Publishers:
        * Joint publishing agreements
        * Historical changes in ownership
        * Regional publishing arrangements
        * Co-publishing partnerships

    Note:
        Publisher information is important for understanding publication
        context, access policies, and copyright arrangements. It may
        affect data usage rights and availability.
    """
    pubs = root.xpath("//journal-meta/publisher/publisher-name")
    return pubs[0].text if len(pubs) == 1 else [p.text for p in pubs]


def gather_publisher_location(root: ET.Element) -> str | list[str]:
    """Extract publisher location(s) from PMC XML.

    Retrieves the geographic location of the publisher, which provides
    context about the journal's regional focus and publication origin.

    Args:
        root: Root element of the PMC XML document

    Returns:
        str | list[str] | None: Single location if one exists,
                               list of locations if multiple exist,
                               or None if no location information is found

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> location = gather_publisher_location(root)
        >>> if isinstance(location, str):
        ...     print(f"Published in: {location}")
        >>> elif isinstance(location, list):
        ...     print(f"Publisher locations: {', '.join(location)}")

    Location Formats:
        * City and country (e.g., "London, UK")
        * City and state/province (e.g., "New York, NY, USA")
        * Multiple locations for international publishers
        * Regional offices or distribution centers

    Use Cases:
        * Geographic analysis of publication patterns
        * Understanding regional research focus
        * Publisher identification and verification
        * Copyright and legal jurisdiction information

    Note:
        Publisher location may indicate the primary editorial office
        rather than corporate headquarters. Some publishers have
        multiple locations for different operations.
    """
    locs = root.xpath("//journal-meta/publisher/publisher-loc")
    if not locs:
        return None
    return locs[0].text if len(locs) == 1 else [loc.text for loc in locs]


# ---------------------------------------------------------------------------
# Article identifiers & categories
# ---------------------------------------------------------------------------


def gather_article_id(root: ET.Element) -> dict[str, str]:
    """Extract article identifier mappings from PMC XML.

    Retrieves various persistent identifiers associated with the article,
    including DOI, PMID, PMC ID, and publisher-specific identifiers.
    These IDs are essential for article identification and cross-referencing.

    Args:
        root: Root element of the PMC XML document

    Returns:
        dict[str, str]: Dictionary mapping identifier types to values.
                       Common keys include "doi", "pmid", "pmc", "publisher-id"

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> article_ids = gather_article_id(root)
        >>> if article_ids:
        ...     for id_type, id_value in article_ids.items():
        ...         print(f"{id_type.upper()}: {id_value}")
        >>>
        >>> # Check for DOI
        >>> if "doi" in article_ids:
        ...     doi_url = f"https://doi.org/{article_ids['doi']}"
        ...     print(f"DOI URL: {doi_url}")

    Common Identifier Types:
        * "doi": Digital Object Identifier (most important for citations)
        * "pmid": PubMed ID for MEDLINE database
        * "pmc": PubMed Central ID
        * "publisher-id": Publisher's internal article identifier
        * "manuscript": Manuscript tracking number

    Use Cases:
        * Cross-referencing between databases
        * Citation management and formatting
        * Article versioning and tracking
        * Persistent linking and access

    Note:
        DOI is the most reliable identifier for permanent access.
        PMC and PMID are specific to NCBI databases. Publisher IDs
        may be useful for editorial workflow tracking.
    """
    ids = root.xpath("//article-meta/article-id")
    return {aid.get("pub-id-type"): aid.text for aid in ids}


def gather_article_types(root: ET.Element) -> list[str] | None:
    """Extract article type classifications from PMC XML.

    Retrieves the primary article type classifications that indicate
    the nature and format of the scholarly work. These types are
    essential for content categorization and filtering.

    Args:
        root: Root element of the PMC XML document

    Returns:
        list[str] | None: List of article type strings, or None if no
                         categories are found. Returns default message
                         if categories exist but no types are specified.

    Warnings:
        * UnexpectedZeroMatchWarning: When no article-categories section exists

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> article_types = gather_article_types(root)
        >>> if article_types:
        ...     print("Article types:")
        ...     for atype in article_types:
        ...         print(f"  - {atype}")

    Common Article Types:
        * "research-article": Original research papers
        * "review-article": Review and survey articles
        * "case-report": Clinical case reports
        * "editorial": Editorial content
        * "letter": Letters to the editor
        * "correction": Corrections and errata

    Classification Context:
        * Types help determine appropriate processing workflows
        * Important for content filtering and search
        * May affect citation patterns and impact metrics
        * Used by indexing services for categorization

    Note:
        Article types are typically assigned by publishers and may
        vary in granularity and terminology across different journals.
        The classification helps users and systems understand content format.
    """
    cats = root.xpath("//article-meta/article-categories")
    if not cats:
        warnings.warn(
            "No article-categories found.", UnexpectedZeroMatchWarning, stacklevel=2
        )
        return None
    heading = cats[0].xpath("subj-group[@subj-group-type='heading']/subject")
    texts = [h.text for h in heading]
    if not texts:
        return ["No article type found."]
    return texts


def gather_article_categories(root: ET.Element) -> list[dict[str, str]] | None:
    """Extract additional article category classifications from PMC XML.

    Retrieves supplementary article categorizations beyond the primary
    article types. These may include subject areas, methodological
    approaches, or other classification schemes used by the publisher.

    Args:
        root: Root element of the PMC XML document

    Returns:
        list[dict[str, str]] | None: List of category dictionaries mapping
                                    category types to values, or None if no
                                    categories are found. Returns default message
                                    if no additional categories exist.

    Warnings:
        * UnexpectedZeroMatchWarning: When no article-categories section exists

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> categories = gather_article_categories(root)
        >>> if categories:
        ...     for category in categories:
        ...         for cat_type, cat_value in category.items():
        ...             print(f"{cat_type}: {cat_value}")

    Category Types:
        * Subject area classifications (e.g., "biology", "medicine")
        * Methodology categories (e.g., "computational", "experimental")
        * Special collections or thematic issues
        * Publisher-specific classification schemes

    Multiple Categories:
        * Articles may belong to multiple subject areas
        * Different classification schemes may be used simultaneously
        * Categories may be hierarchical or overlapping

    Use Cases:
        * Content recommendation and discovery
        * Subject-based filtering and search
        * Bibliometric analysis by research area
        * Editorial workflow and peer review assignment

    Note:
        Additional categories provide finer-grained classification
        beyond basic article types and are valuable for detailed
        content analysis and organization.
    """
    cats = root.xpath("//article-meta/article-categories")
    if not cats:
        warnings.warn(
            "No article-categories found.", UnexpectedZeroMatchWarning, stacklevel=2
        )
        return None
    others = cats[0].xpath("subj-group[not(@subj-group-type='heading')]/subject")
    result = [{other.get("subj-group-type"): other.text} for other in others]
    if not result:
        return [{"info": "No extra article categories found."}]
    return result


# ---------------------------------------------------------------------------
# Dates / history
# ---------------------------------------------------------------------------


def gather_published_date(root: ET.Element) -> dict[str, datetime.date]:
    """Extract publication dates from PMC XML.

    Retrieves various publication dates associated with the article,
    including online publication, print publication, and other
    date types. These dates are crucial for citation and chronological analysis.

    Args:
        root: Root element of the PMC XML document

    Returns:
        dict[str, datetime.date]: Dictionary mapping publication types to date objects.
                                 Common keys include "epub", "ppub", "collection"

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> pub_dates = gather_published_date(root)
        >>> if pub_dates:
        ...     for date_type, date_obj in pub_dates.items():
        ...         print(f"{date_type}: {date_obj.strftime('%Y-%m-%d')}")
        >>>
        >>> # Get electronic publication date
        >>> if "epub" in pub_dates:
        ...     epub_date = pub_dates["epub"]
        ...     print(f"Published online: {epub_date}")

    Publication Date Types:
        * "epub": Electronic publication date (online first)
        * "ppub": Print publication date
        * "collection": Collection or issue publication date
        * "accepted": Acceptance date (less common in this field)

    Date Handling:
        * Missing date components default to 1 (e.g., January 1st)
        * All dates are returned as Python datetime.date objects
        * Enables easy date arithmetic and comparison
        * Suitable for chronological sorting and analysis

    Use Cases:
        * Citation formatting with proper dates
        * Chronological analysis of research trends
        * Determining article recency and relevance
        * Publication timeline reconstruction

    Note:
        Electronic publication typically occurs before print publication.
        The "epub" date is often the most relevant for online articles
        and should be used for citation purposes when available.
    """
    dates: dict[str, datetime.date] = {}
    for pd_elem in root.xpath("//article-meta/pub-date"):
        ptype = pd_elem.get("pub-type")
        year = (
            int(pd_elem.xpath("year/text()")[0]) if pd_elem.xpath("year/text()") else 1
        )
        month = (
            int(pd_elem.xpath("month/text()")[0])
            if pd_elem.xpath("month/text()")
            else 1
        )
        day = int(pd_elem.xpath("day/text()")[0]) if pd_elem.xpath("day/text()") else 1
        dates[ptype] = datetime.date(year, month, day)
    return dates


def gather_history_dates(root: ET.Element) -> dict[str, datetime.date] | None:
    """Extract manuscript history dates from PMC XML.

    Retrieves key dates in the manuscript's editorial process,
    including submission, revision, acceptance, and other
    milestone dates. This information provides insight into
    the peer review timeline and editorial process.

    Args:
        root: Root element of the PMC XML document

    Returns:
        dict[str, datetime.date] | None: Dictionary mapping date types to date objects,
                                        or None if no history dates are found.
                                        Common keys include "received", "accepted", "revised"

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> history = gather_history_dates(root)
        >>> if history:
        ...     for date_type, date_obj in history.items():
        ...         print(f"{date_type.title()}: {date_obj.strftime('%Y-%m-%d')}")
        >>>
        >>> # Calculate review time
        >>> if history and "received" in history and "accepted" in history:
        ...     review_time = history["accepted"] - history["received"]
        ...     print(f"Review time: {review_time.days} days")

    Common History Date Types:
        * "received": Initial manuscript submission date
        * "accepted": Final acceptance date
        * "revised": Revision submission date(s)
        * "rev-recd": Revised manuscript received
        * "rev-request": Revision requested date

    Editorial Process Insights:
        * Submission to acceptance timeline
        * Number and timing of revision rounds
        * Editorial efficiency metrics
        * Seasonal patterns in review times

    Date Handling:
        * Missing components default to 1 for valid date construction
        * All dates returned as Python datetime.date objects
        * Enables timeline analysis and process metrics
        * Useful for editorial workflow research

    Note:
        History dates provide valuable metadata about the editorial
        process and can be used to assess journal efficiency and
        the complexity of the peer review process for specific articles.
    """
    dates: dict[str, datetime.date] = {}
    for h_elem in root.xpath("//article-meta/history/date"):
        dtype = h_elem.get("date-type") or "unknown"
        year = int(h_elem.xpath("year/text()")[0]) if h_elem.xpath("year/text()") else 1
        month = (
            int(h_elem.xpath("month/text()")[0]) if h_elem.xpath("month/text()") else 1
        )
        day = int(h_elem.xpath("day/text()")[0]) if h_elem.xpath("day/text()") else 1
        dates[dtype] = datetime.date(year, month, day)
    return dates or None


# gather_version_history intentionally left in original parser for now

# ---------------------------------------------------------------------------
# Numbers
# ---------------------------------------------------------------------------


def gather_volume(root: ET.Element) -> str | None:
    """Extract journal volume number from PMC XML.

    Retrieves the journal volume number, which is part of the standard
    bibliographic citation format. Volume numbers typically represent
    annual collections of issues for a journal.

    Args:
        root: Root element of the PMC XML document

    Returns:
        str | None: Volume number as string, or None if not found

    Warnings:
        * UnexpectedZeroMatchWarning: When no volume information is found

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> volume = gather_volume(root)
        >>> if volume:
        ...     print(f"Volume: {volume}")
        >>>
        >>> # Use in citation format
        >>> if volume and issue:
        ...     print(f"Vol. {volume}, Issue {issue}")

    Volume Characteristics:
        * Usually numeric (e.g., "42", "118")
        * May include letters for special cases (e.g., "15A")
        * Typically represents one calendar year of publication
        * Sequential numbering starting from journal inception

    Citation Importance:
        * Essential component of complete bibliographic citations
        * Used in conjunction with issue number and page numbers
        * Enables precise article location within journal archives
        * Required by most citation styles (APA, MLA, etc.)

    Note:
        Volume numbers are crucial for proper citation formatting
        and article identification within journal collections.
        Missing volume information may indicate incomplete metadata.
    """
    vol = root.xpath("//article-meta/volume/text()")
    if not vol:
        warnings.warn("No volume found.", UnexpectedZeroMatchWarning, stacklevel=2)
        return None
    return vol[0]


def gather_issue(root: ET.Element) -> str | None:
    """Extract journal issue number from PMC XML.

    Retrieves the journal issue number, which specifies the particular
    issue within a volume. Issues typically represent periodic publications
    within a journal volume (monthly, quarterly, etc.).

    Args:
        root: Root element of the PMC XML document

    Returns:
        str | None: Issue number as string, or None if not found

    Warnings:
        * UnexpectedZeroMatchWarning: When no issue information is found

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> issue = gather_issue(root)
        >>> if issue:
        ...     print(f"Issue: {issue}")
        >>>
        >>> # Create complete volume/issue citation
        >>> if volume and issue:
        ...     citation_part = f"{volume}({issue})"
        ...     print(f"Citation format: {citation_part}")

    Issue Characteristics:
        * Usually numeric (e.g., "3", "12")
        * May include special designators (e.g., "Suppl 1", "Pt A")
        * Represents subdivision within a journal volume
        * May correspond to publication frequency (monthly = 12 issues/year)

    Special Issue Types:
        * Supplemental issues (e.g., "Suppl 1")
        * Special thematic issues
        * Conference proceedings issues
        * Anniversary or commemorative issues

    Citation Usage:
        * Combined with volume for precise article location
        * Format varies by citation style
        * Essential for library and database indexing
        * Enables chronological ordering within volumes

    Note:
        Issue numbers help pinpoint articles within journal volumes
        and are essential for complete bibliographic citations.
        Some journals may use alternative numbering schemes.
    """
    iss = root.xpath("//article-meta/issue/text()")
    if not iss:
        warnings.warn("No issue found.", UnexpectedZeroMatchWarning, stacklevel=2)
        return None
    return iss[0]


# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------


def gather_keywords(root: ET.Element):
    """Extract keywords and subject terms from PMC XML.

    Retrieves author-provided keywords and subject classifications
    from multiple sources within the article metadata. Keywords are
    essential for content discovery, search optimization, and
    topical analysis.

    Args:
        root: Root element of the PMC XML document

    Returns:
        list[str | dict[str, list[str]]] | None: Mixed list containing:
            - Individual keyword strings (for ungrouped keywords)
            - Dictionaries mapping keyword types to keyword lists
            Returns None if no keywords are found.

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> keywords = gather_keywords(root)
        >>> if keywords:
        ...     for item in keywords:
        ...         if isinstance(item, str):
        ...             print(f"Keyword: {item}")
        ...         elif isinstance(item, dict):
        ...             for ktype, kwords in item.items():
        ...                 print(f"{ktype}: {', '.join(kwords)}")

    Keyword Sources:
        * **kwd-group**: Author-provided keyword groups
        * **article-categories**: Subject classification keywords
        * Multiple keyword types may be present in one article

    Keyword Group Types:
        * "author": Author-provided keywords
        * "subject": Subject area classifications
        * "mesh": Medical Subject Headings (MeSH terms)
        * "other": Publisher or editor-assigned terms

    Data Structure:
        * Ungrouped keywords appear as individual strings
        * Grouped keywords appear as dictionaries with type mappings
        * Mixed structure preserves original organization
        * Empty or whitespace-only keywords are filtered out

    Use Cases:
        * Content-based article recommendation
        * Search engine optimization and indexing
        * Topical clustering and analysis
        * Subject area identification
        * Research trend analysis

    Note:
        Keywords provide valuable semantic information about article
        content and are crucial for discoverability. Different keyword
        types may serve different purposes in information retrieval systems.
    """
    keywords: list[str | dict[str, list[str]]] = []

    # kwd-group parsing
    for group in root.xpath("//kwd-group"):
        group_type = group.get("kwd-group-type")
        words = [
            kwd.text.strip()
            for kwd in group.xpath("kwd")
            if kwd.text and kwd.text.strip()
        ]
        if not words:
            continue
        if group_type:
            keywords.append({group_type: words})
        else:
            keywords.extend(words)

    # article-categories keyword groups
    for subj_grp in root.xpath(
        "//article-meta/article-categories/subj-group[@subj-group-type='keyword']"
    ):
        words = [
            subj.text.strip()
            for subj in subj_grp.xpath("subject")
            if subj.text and subj.text.strip()
        ]
        if words:
            keywords.append({"article-categories-keyword": words})

    return keywords or None
