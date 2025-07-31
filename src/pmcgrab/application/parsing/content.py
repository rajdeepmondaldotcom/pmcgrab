"""Specialized content extraction for PMC article metadata and supplementary information.

This module provides focused extraction functions for various types of content
commonly found in scientific articles: permissions, funding information, ethics
disclosures, supplementary materials, mathematical equations, and other
specialized metadata not covered by the core metadata parsers.

All functions in this module are pure functions that operate on lxml Element
trees and return structured data suitable for JSON serialization. They handle
edge cases gracefully and include appropriate warnings for unexpected or
missing content.

Key Areas Covered:
    * **Legal Information**: Copyright, licensing, and permissions
    * **Research Funding**: Grant information and funding sources
    * **Ethics & Compliance**: Disclosure statements, conflicts of interest
    * **Supplementary Content**: Additional files, equations, notes
    * **Version Control**: Article version history and updates

Design Principles:
    * Pure functions with no side effects for easy testing
    * Graceful handling of missing or malformed content
    * Comprehensive warning system for data quality issues
    * Structured output optimized for downstream processing
    * Full compliance with PMC XML schema variations

Functions:
    gather_permissions: Extract copyright and licensing information
    gather_funding: Extract funding source information
    gather_version_history: Extract article version history
    gather_equations: Extract mathematical equations in MathML format
    gather_supplementary_material: Extract supplementary file metadata
    gather_ethics_disclosures: Extract ethics statements and disclosures
    gather_footnote: Extract and format footnotes
    gather_acknowledgements: Extract acknowledgement statements
    gather_notes: Extract additional notes and annotations
    gather_custom_metadata: Extract custom metadata fields
    stringify_note: Helper function for note formatting
"""

from __future__ import annotations

import textwrap
import uuid
import warnings

import lxml.etree as ET

from pmcgrab.constants import (
    UnexpectedMultipleMatchWarning,
    UnexpectedZeroMatchWarning,
    UnhandledTextTagWarning,
)
from pmcgrab.model import TextParagraph

__all__: list[str] = [
    "gather_acknowledgements",
    "gather_custom_metadata",
    "gather_equations",
    "gather_ethics_disclosures",
    "gather_footnote",
    "gather_funding",
    "gather_notes",
    "gather_permissions",
    "gather_supplementary_material",
    "gather_version_history",
    # helper
    "stringify_note",
]

# ----------------------------------------------------------------------------
# Permissions / funding / versions
# ----------------------------------------------------------------------------


def gather_permissions(root: ET.Element) -> dict[str, str] | None:
    """Extract copyright and licensing information from PMC article.

    Parses the permissions section of PMC XML to extract copyright statements
    and license information. This is crucial for understanding the legal
    terms under which the article content can be used, particularly important
    for AI/ML applications and content redistribution.

    Args:
        root: Root element of the PMC XML document

    Returns:
        dict[str, str] | None: Dictionary containing permission information with keys:
            - "Copyright Statement": Copyright notice text
            - "License Type": License type identifier (e.g., "open-access")
            - "License Text": Full license text and terms
        Returns None if no license information is found.

    Warnings:
        * UnexpectedZeroMatchWarning: When no license is found
        * UnexpectedMultipleMatchWarning: When multiple licenses exist (uses first)

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> permissions = gather_permissions(root)
        >>> if permissions:
        ...     print(f"License: {permissions['License Type']}")
        ...     print(f"Copyright: {permissions['Copyright Statement']}")
        >>>
        >>> # Check if content is openly licensed
        >>> if permissions and "open" in permissions['License Type'].lower():
        ...     print("Article is openly licensed")

    Common License Types:
        * "open-access": Open access articles
        * "cc-by": Creative Commons Attribution
        * "cc-by-nc": Creative Commons Non-Commercial
        * Various publisher-specific license types

    Note:
        License information is essential for determining how article content
        can be legally used in downstream applications. Always check
        permissions before redistributing or processing copyrighted content.
    """
    cp = root.xpath("//article-meta/permissions/copyright-statement/text()")
    cp_stmt = cp[0] if cp else "No copyright statement found."
    lic_elems = root.xpath("//article-meta/permissions/license")
    if not lic_elems:
        warnings.warn("No license found.", UnexpectedZeroMatchWarning, stacklevel=2)
        return None
    if len(lic_elems) > 1:
        warnings.warn(
            "Multiple licenses found; using the first.",
            UnexpectedMultipleMatchWarning,
            stacklevel=2,
        )
    lic_elem = lic_elems[0]
    lic_type = lic_elem.get("license-type", "Not Specified")
    lic_text = "\n".join(
        str(TextParagraph(child)) for child in lic_elem if child.tag == "license-p"
    )
    return {
        "Copyright Statement": cp_stmt,
        "License Type": lic_type,
        "License Text": lic_text,
    }


def gather_funding(root: ET.Element) -> list[str] | None:
    """Extract funding source information from PMC article.

    Parses funding information to identify the institutions and organizations
    that supported the research. This information is valuable for understanding
    research funding patterns and institutional affiliations.

    Args:
        root: Root element of the PMC XML document

    Returns:
        list[str] | None: List of funding institution names.
                         Returns None if no funding information is found.

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> funding = gather_funding(root)
        >>> if funding:
        ...     print("Funded by:")
        ...     for funder in funding:
        ...         print(f"  - {funder}")
        >>>
        >>> # Check for specific funding sources
        >>> if funding and any("NIH" in f for f in funding):
        ...     print("NIH-funded research")

    Common Funding Sources:
        * National Institutes of Health (NIH)
        * National Science Foundation (NSF)
        * European Research Council (ERC)
        * Various university and private foundation grants

    Note:
        Funding information helps identify potential conflicts of interest
        and provides context for research independence. Some articles may
        have multiple funding sources or complex funding arrangements.
    """
    fund: list[str] = []
    for group in root.xpath("//article-meta/funding-group"):
        fund.extend(group.xpath("award-group/funding-source/institution/text()"))
    return fund or None


def gather_version_history(root: ET.Element) -> list[dict[str, str]] | None:
    """Extract article version history from PMC XML.

    Parses version information to track article updates and revisions.
    This is particularly useful for understanding the evolution of
    research findings and ensuring you're working with the latest version.

    Args:
        root: Root element of the PMC XML document

    Returns:
        list[dict[str, str]] | None: List of version dictionaries with keys:
            - "Version": Version identifier or number
            - "Date": Version date in YYYY-MM-DD format (may be None)
        Returns None if no version history is found.

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> versions = gather_version_history(root)
        >>> if versions:
        ...     for version in versions:
        ...         ver_num = version["Version"]
        ...         ver_date = version["Date"]
        ...         print(f"Version {ver_num}: {ver_date}")
        >>>
        >>> # Get latest version
        >>> if versions:
        ...     latest = max(versions, key=lambda v: v["Date"] or "")
        ...     print(f"Latest version: {latest['Version']}")

    Version Information:
        * Articles may have multiple versions with corrections or updates
        * Version dates help determine chronological order
        * Some versions may lack specific date information
        * Version numbers may be numeric or descriptive

    Note:
        Version history is important for citation accuracy and ensuring
        you're referencing the correct version of an article. Always
        check for the most recent version when available.
    """
    versions: list[dict[str, str]] = []
    for ver in root.xpath("//article-meta/article-version"):
        ver_num = ver.get("version") or ver.findtext("version")
        date_elem = ver.find("date")
        date_str = None
        if date_elem is not None:
            year = date_elem.findtext("year")
            month = date_elem.findtext("month") or "1"
            day = date_elem.findtext("day") or "1"
            if year:
                date_str = f"{year}-{int(month):02d}-{int(day):02d}"
        versions.append({"Version": ver_num, "Date": date_str})
    return versions or None


# ----------------------------------------------------------------------------
# Equations & supplementary material
# ----------------------------------------------------------------------------


def gather_equations(root: ET.Element) -> list[str] | None:
    """Extract mathematical equations in MathML format from PMC article.

    Parses mathematical content encoded in MathML format, preserving the
    complete mathematical expressions for further processing or display.
    This is essential for articles containing complex mathematical formulas.

    Args:
        root: Root element of the PMC XML document

    Returns:
        list[str] | None: List of MathML equation strings in Unicode format.
                         Returns None if no equations are found.

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> equations = gather_equations(root)
        >>> if equations:
        ...     print(f"Found {len(equations)} equations")
        ...     for i, eq in enumerate(equations):
        ...         print(f"Equation {i+1}: {eq[:50]}...")
        >>>
        >>> # Check for specific mathematical content
        >>> if equations and any("integral" in eq.lower() for eq in equations):
        ...     print("Article contains integral equations")

    MathML Format:
        * Complete MathML markup with proper namespacing
        * Preserves mathematical structure and semantics
        * Unicode encoding for broad compatibility
        * Suitable for conversion to other formats (LaTeX, etc.)

    Use Cases:
        * Mathematical content analysis and indexing
        * Conversion to other mathematical formats
        * Mathematical formula extraction for AI/ML
        * Quality assessment of mathematical notation

    Note:
        MathML content can be complex and may require specialized libraries
        for rendering or conversion. The extracted equations maintain full
        structural information for downstream processing.
    """
    eqs = []
    for math in root.xpath(
        "//mml:math", namespaces={"mml": "http://www.w3.org/1998/Math/MathML"}
    ):
        eqs.append(ET.tostring(math, encoding="unicode"))
    return eqs or None


def gather_supplementary_material(root: ET.Element) -> list[dict[str, str]] | None:
    """Extract metadata for supplementary materials and media files.

    Parses supplementary material references to identify additional files,
    datasets, videos, and other materials associated with the article.
    This information is valuable for comprehensive content analysis.

    Args:
        root: Root element of the PMC XML document

    Returns:
        list[dict[str, str]] | None: List of supplementary material dictionaries with keys:
            - "Label": Material identifier or label
            - "Caption": Descriptive caption text
            - "Href": Link to the material (may be None)
            - "Tag": XML tag type ("supplementary-material" or "media")
        Returns None if no supplementary materials are found.

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> supp_materials = gather_supplementary_material(root)
        >>> if supp_materials:
        ...     for material in supp_materials:
        ...         label = material["Label"]
        ...         caption = material["Caption"]
        ...         print(f"{label}: {caption}")
        >>>
        >>> # Find specific types of supplementary content
        >>> videos = [m for m in supp_materials if "video" in m["Caption"].lower()]
        >>> datasets = [m for m in supp_materials if "data" in m["Label"].lower()]

    Common Supplementary Materials:
        * Datasets and raw data files
        * Video and audio recordings
        * Additional figures and images
        * Software code and algorithms
        * Detailed experimental protocols

    Link Handling:
        * Handles both explicit xlink namespace and plain href attributes
        * Falls back to ext-link elements when direct href is unavailable
        * Links may be relative paths or absolute URLs
        * Some materials may not have accessible links

    Note:
        Supplementary materials often contain critical research data and
        methodological details. Links may require institutional access
        or may point to external repositories.
    """
    items: list[dict[str, str]] = []
    for supp in root.xpath("//supplementary-material|//media"):
        label = supp.findtext("label") or supp.get("id")
        caption_elem = supp.find("caption")
        caption = None
        if caption_elem is not None:
            caption = " ".join(caption_elem.itertext()).strip()
        # Handle both explicit xlink namespace and plain attribute usage
        href = (
            supp.get("xlink:href")
            or supp.get("{http://www.w3.org/1999/xlink}href")
            or None
        )
        if not href:
            ext = supp.find("ext-link")
            if ext is not None:
                href = ext.get("xlink:href") or ext.get(
                    "{http://www.w3.org/1999/xlink}href"
                )
        items.append(
            {
                "Label": label,
                "Caption": caption,
                "Href": href,
                "Tag": supp.tag,
            }
        )
    return items or None


# ----------------------------------------------------------------------------
# Ethics / footnotes / acknowledgements / notes
# ----------------------------------------------------------------------------


def gather_ethics_disclosures(root: ET.Element) -> dict[str, str] | None:
    """Extract ethics statements and disclosure information from PMC article.

    Parses various ethics-related disclosures including conflicts of interest,
    clinical trial information, data availability statements, and consent
    information. This is crucial for research transparency and compliance.

    Args:
        root: Root element of the PMC XML document

    Returns:
        dict[str, str] | None: Dictionary containing disclosure information with keys:
            - "Conflicts of Interest": Conflict of interest statements
            - "Ethics Statement": Ethics approval and compliance information
            - "Clinical Trial Registration": Trial registration numbers and info
            - "Data Availability": Data sharing and availability statements
            - "Author Contributions": Author contribution statements
            - "Patient Consent": Patient consent and privacy information
        Returns None if no ethics disclosures are found.

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> ethics = gather_ethics_disclosures(root)
        >>> if ethics:
        ...     for category, statement in ethics.items():
        ...         print(f"{category}:")
        ...         print(f"  {statement[:100]}...")
        >>>
        >>> # Check for specific disclosures
        >>> if ethics and "Conflicts of Interest" in ethics:
        ...     coi = ethics["Conflicts of Interest"]
        ...     if "none" in coi.lower():
        ...         print("No conflicts of interest declared")

    Disclosure Categories:
        * **Conflicts of Interest**: Financial and professional conflicts
        * **Ethics Statement**: IRB approval and ethical compliance
        * **Clinical Trial Registration**: ClinicalTrials.gov numbers, etc.
        * **Data Availability**: Data sharing policies and access information
        * **Author Contributions**: Individual author contribution details
        * **Patient Consent**: Consent procedures and privacy protections

    Fallback Handling:
        * Searches multiple XPath patterns for comprehensive coverage
        * Includes fallback patterns for conflicts of interest in footnotes
        * Handles various XML schema variations used by different publishers

    Use Cases:
        * Research integrity assessment
        * Compliance checking for institutional policies
        * Transparency evaluation for systematic reviews
        * Data availability assessment for meta-analyses

    Note:
        Ethics disclosures are increasingly important for research transparency
        and may be required by funding agencies and journals. Missing
        disclosures may indicate older articles or different reporting standards.
    """
    fields: dict[str, tuple[str, list[str]]] = {
        "Conflicts of Interest": ("//conflict-of-interest", []),
        "Ethics Statement": ("//ethics-statement", []),
        "Clinical Trial Registration": (
            "//clinical-trial-number|//other-id[@other-id-type='clinical-trial-number']",
            [],
        ),
        "Data Availability": ("//data-availability", []),
        "Author Contributions": ("//author-notes", []),
        "Patient Consent": ("//patient-consent", []),
    }
    result: dict[str, str] = {}
    for key, (xpath, _) in fields.items():
        texts = [" ".join(el.itertext()).strip() for el in root.xpath(xpath)]
        if texts:
            result[key] = "\n".join(texts)
    if "Conflicts of Interest" not in result:
        texts = [
            " ".join(fn.itertext()).strip()
            for fn in root.xpath("//fn[@fn-type='conflict']")
        ]
        if texts:
            result["Conflicts of Interest"] = "\n".join(texts)
    return result or None


def gather_footnote(root: ET.Element) -> str | None:
    """Extract and format footnotes from PMC article.

    Parses footnote content from the back matter of the article,
    combining multiple footnotes into a single formatted string.
    Footnotes often contain important clarifications and additional information.

    Args:
        root: Root element of the PMC XML document

    Returns:
        str | None: Concatenated footnote text separated by " - ".
                   Returns None if no footnotes are found.

    Warnings:
        * UnhandledTextTagWarning: When unexpected tags are found in footnotes

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> footnotes = gather_footnote(root)
        >>> if footnotes:
        ...     print("Footnotes:")
        ...     print(footnotes)
        >>>
        >>> # Split individual footnotes
        >>> if footnotes:
        ...     individual_notes = footnotes.split(" - ")
        ...     for i, note in enumerate(individual_notes, 1):
        ...         print(f"Footnote {i}: {note}")

    Footnote Content:
        * Additional explanations and clarifications
        * Methodological details not included in main text
        * Author corrections and updates
        * Editorial notes and comments

    Note:
        Footnotes are processed using TextParagraph for consistent formatting
        and cross-reference handling. Multiple footnotes are joined with
        " - " separators for easy parsing.
    """
    foot: list[str] = []
    for fn in root.xpath("//back/fn-group/fn"):
        for child in fn:
            if child.tag == "p":
                foot.append(str(TextParagraph(child)))
            else:
                warnings.warn(
                    f"Unexpected tag {child.tag} in footnote.",
                    UnhandledTextTagWarning,
                    stacklevel=2,
                )
    return " - ".join(foot) if foot else None


def gather_acknowledgements(root: ET.Element) -> list[str] | str:
    """Extract acknowledgement statements from PMC article.

    Parses acknowledgement sections where authors thank contributors,
    institutions, and funding sources. This provides valuable context
    about research collaboration and support.

    Args:
        root: Root element of the PMC XML document

    Returns:
        list[str]: List of acknowledgement text strings.
                  Empty list if no acknowledgements are found.

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> acknowledgements = gather_acknowledgements(root)
        >>> if acknowledgements:
        ...     print("Acknowledgements:")
        ...     for ack in acknowledgements:
        ...         print(f"  {ack}")
        >>>
        >>> # Search for specific acknowledgements
        >>> funding_acks = [ack for ack in acknowledgements
        ...                 if "fund" in ack.lower()]

    Acknowledgement Content:
        * Technical assistance and collaboration
        * Institutional support and resources
        * Funding acknowledgements
        * Editorial and peer review thanks
        * Data and material contributions

    Note:
        Acknowledgements provide insight into research networks and
        collaborative relationships. They may complement funding
        information and author contribution statements.
    """
    return [" ".join(match.itertext()).strip() for match in root.xpath("//ack")]


def stringify_note(root: ET.Element) -> str:
    """Convert note XML element to formatted string representation.

    Helper function that recursively processes note elements to create
    a readable text representation with proper formatting and indentation
    for nested structures.

    Args:
        root: XML element containing note content

    Returns:
        str: Formatted note text with titles and nested structure preserved

    Examples:
        >>> note_element = ET.fromstring('<notes><title>Note</title><p>Content</p></notes>')
        >>> formatted = stringify_note(note_element)
        >>> print(formatted)  # "Title: Note\nContent"

    Formatting Rules:
        * Titles are prefixed with "Title: "
        * Paragraph content is included directly
        * Nested notes are indented with 4 spaces
        * Leading/trailing whitespace is stripped

    Note:
        This is a helper function used internally by gather_notes()
        to ensure consistent note formatting across the system.
    """
    note = ""
    for child in root:
        if child.tag == "title":
            note += f"Title: {child.text}\n"
        elif child.tag == "p":
            note += child.text or ""
        elif child.tag == "notes":
            note += "\n" + textwrap.indent(stringify_note(child), " " * 4)
    return note.strip()


def gather_notes(root: ET.Element) -> list[str]:
    """Extract additional notes and annotations from PMC article.

    Parses note elements that contain supplementary information,
    editorial comments, or other annotations not captured in main content.
    Only processes top-level notes to avoid duplication.

    Args:
        root: Root element of the PMC XML document

    Returns:
        list[str]: List of formatted note strings.
                  Empty list if no notes are found.

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> notes = gather_notes(root)
        >>> if notes:
        ...     print(f"Found {len(notes)} additional notes:")
        ...     for i, note in enumerate(notes, 1):
        ...         print(f"Note {i}: {note}")

    Note Processing:
        * Only extracts top-level notes (parent is not another note)
        * Uses stringify_note() for consistent formatting
        * Preserves note structure and hierarchy
        * Handles nested note elements appropriately

    Common Note Types:
        * Editorial comments and corrections
        * Author clarifications and updates
        * Methodological annotations
        * Cross-references to related work

    Note:
        Notes may contain important contextual information not found
        elsewhere in the article. They are processed separately from
        footnotes to maintain distinct semantic meaning.
    """
    return [
        stringify_note(note)
        for note in root.xpath("//notes")
        if note.getparent().tag != "notes"
    ]


# ----------------------------------------------------------------------------
# Custom meta
# ----------------------------------------------------------------------------


def gather_custom_metadata(root: ET.Element) -> dict[str, str] | None:
    """Extract custom metadata fields from PMC article.

    Parses publisher-specific or journal-specific custom metadata fields
    that are not covered by standard bibliographic metadata. These fields
    can contain valuable supplementary information about the article.

    Args:
        root: Root element of the PMC XML document

    Returns:
        dict[str, str] | None: Dictionary mapping custom metadata names to values.
                              Returns None if no custom metadata is found.
                              Names without explicit labels get UUID identifiers.

    Examples:
        >>> root = ET.fromstring(pmc_xml)
        >>> custom_meta = gather_custom_metadata(root)
        >>> if custom_meta:
        ...     print("Custom metadata:")
        ...     for name, value in custom_meta.items():
        ...         print(f"  {name}: {value}")
        >>>
        >>> # Look for specific custom fields
        >>> if custom_meta and "manuscript-type" in custom_meta:
        ...     print(f"Manuscript type: {custom_meta['manuscript-type']}")

    Custom Metadata Examples:
        * Publisher-specific article classifications
        * Journal-specific submission categories
        * Special issue or thematic collection indicators
        * Processing workflow metadata
        * Editorial system identifiers

    Handling Anonymous Fields:
        * Fields without explicit names get UUID identifiers
        * Ensures all custom metadata is preserved and accessible
        * UUIDs prevent key conflicts in the output dictionary

    Use Cases:
        * Publisher-specific content analysis
        * Workflow and processing information extraction
        * Complete metadata preservation for archival purposes
        * Publisher-specific feature extraction

    Note:
        Custom metadata varies significantly between publishers and journals.
        The content and structure of these fields depends on the specific
        editorial and publishing systems used by each publication.
    """
    custom: dict[str, str] = {}
    for meta in root.xpath("//custom-meta"):
        name = meta.findtext("meta-name")
        value = (
            " ".join(meta.find("meta-value").itertext())
            if meta.find("meta-value") is not None
            else None
        )
        if value:
            if name is None:
                name = str(uuid.uuid4())
            custom[name] = value
    return custom or None
