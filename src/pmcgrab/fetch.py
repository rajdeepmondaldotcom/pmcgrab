"""XML fetching, local file reading, and validation utilities for PMC articles.

This module provides the core functionality for downloading PMC article XML
from NCBI Entrez **or reading it from local files**, parsing it into
ElementTree objects, and validating it against PMC DTD schemas. It handles
network retries, caching, XML cleaning, and validation error recovery.

The module supports both raw XML fetching and complete parsing pipelines
with configurable validation, text styling removal, and error handling.
It's designed to be robust against network failures and malformed XML
while providing detailed feedback about validation issues.

Key Functions:
    fetch_pmc_xml_string: Download raw XML from NCBI with retry logic
    xml_tree_from_string: Parse XML string into ElementTree
    validate_xml: Validate XML against PMC DTD schemas
    get_xml: Complete pipeline from PMCID to validated ElementTree
    parse_local_xml: Read and parse a local JATS XML file from disk
"""

import os
import threading
import time
import warnings
from io import StringIO
from pathlib import Path
from urllib.error import HTTPError

import lxml.etree as ET
from Bio import Entrez

_entrez_lock = threading.Lock()

from pmcgrab.common.html_cleaning import strip_html_text_styling
from pmcgrab.common.serialization import clean_doc
from pmcgrab.constants import (
    DTD_URL_PATTERN,
    END_OF_URL_PATTERN,
    SUPPORTED_DTD_URLS,
    NoDTDFoundError,
    ValidationWarning,
    logger,
)


def fetch_pmc_xml_string(
    pmcid: int, email: str, download: bool = False, verbose: bool = False
) -> str:
    """Download raw XML for a PMC article from NCBI Entrez with retry logic.

    Fetches the complete XML document for a PubMed Central article using
    the NCBI Entrez efetch API. Implements automatic retry with exponential
    backoff on failures and optional local caching for repeated access.

    Args:
        pmcid: Numeric PubMed Central ID (e.g., 7181753)
        email: Contact email address required by NCBI Entrez API for identification
        download: If True, cache the XML to local data/ directory for reuse
        verbose: If True, log progress messages and preview of fetched content

    Returns:
        str: Complete raw XML document as UTF-8 string

    Raises:
        HTTPError: If download fails after 3 retry attempts with exponential backoff

    Examples:
        >>> # Basic download
        >>> xml_content = fetch_pmc_xml_string(7181753, "user@example.com")
        >>> print(xml_content[:100])
        >>>
        >>> # With caching and verbose output
        >>> xml_content = fetch_pmc_xml_string(
        ...     7181753, "user@example.com",
        ...     download=True, verbose=True
        ... )

    Note:
        Respects NCBI rate limits with 5-second delays between retry attempts.
        Creates data/ directory automatically if it doesn't exist.
    """
    os.makedirs("data", exist_ok=True)
    cache_path = os.path.join("data", f"entrez_download_PMCID={pmcid}.xml")
    if download and os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            cached_xml = f.read()
        if verbose:
            logger.info("Using cached XML for PMCID %s", pmcid)
        return cached_xml
    from pmcgrab.infrastructure.settings import (
        NCBI_API_KEY,
        NCBI_RETRIES,
        rate_limit_wait,
    )

    db, rettype, retmode = "pmc", "full", "xml"
    delay = 5
    for _attempt in range(NCBI_RETRIES):
        try:
            rate_limit_wait()
            with _entrez_lock:
                Entrez.email = email
                if NCBI_API_KEY:
                    Entrez.api_key = NCBI_API_KEY
                handle = Entrez.efetch(
                    db=db, id=pmcid, rettype=rettype, retmode=retmode
                )
            xml_record = handle.read()
            handle.close()
            xml_text = xml_record.decode("utf-8")
            if verbose:
                logger.info("Fetched XML (first 100 chars): %s", xml_text[:100])
            if download:
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(xml_text)
            return xml_text
        except Exception:
            time.sleep(delay)
            delay *= 2
    raise HTTPError(
        f"Failed to fetch PMCID {pmcid} after retries", None, None, None, None
    )


def clean_xml_string(
    xml_string: str, strip_text_styling: bool = True, verbose: bool = False
) -> str:
    """Normalize and clean XML string for reliable parsing.

    Preprocesses raw XML from NCBI Entrez to remove problematic HTML-style
    formatting tags that can interfere with parsing. The cleaning process
    focuses on text styling elements while preserving structural markup
    and content.

    Args:
        xml_string: Raw XML text as returned from NCBI Entrez API
        strip_text_styling: If True, remove HTML emphasis tags (<b>, <i>, etc.)
                           and other styling markup that's not needed for content extraction
        verbose: If True, log details about which tags are being removed

    Returns:
        str: Cleaned XML string optimized for lxml parsing with problematic
             formatting removed but content and structure preserved

    Examples:
        >>> raw_xml = fetch_pmc_xml_string(7181753, "user@example.com")
        >>> clean_xml = clean_xml_string(raw_xml, strip_text_styling=True, verbose=True)
        >>> # Clean XML is now ready for reliable parsing

    Note:
        This function delegates to strip_html_text_styling() which handles
        the actual tag removal logic. Setting strip_text_styling=False
        returns the XML unchanged.
    """
    return (
        strip_html_text_styling(xml_string, verbose=verbose)
        if strip_text_styling
        else xml_string
    )


def xml_tree_from_string(
    xml_string: str, strip_text_styling: bool = True, verbose: bool = False
) -> ET.ElementTree:
    """Parse XML string into lxml ElementTree with preprocessing.

    Converts raw XML text into a structured ElementTree object suitable
    for XPath queries and content extraction. Includes optional text
    styling cleanup to ensure reliable parsing of PMC articles.

    Args:
        xml_string: Raw XML text to parse
        strip_text_styling: If True, remove HTML-style formatting tags
                           before parsing to avoid parser issues
        verbose: If True, log parsing steps and any issues encountered

    Returns:
        ET.ElementTree: Parsed XML document tree ready for content extraction
                       and XPath queries

    Raises:
        ET.XMLSyntaxError: If the XML is malformed and cannot be parsed
                          even after cleaning attempts

    Examples:
        >>> xml_content = fetch_pmc_xml_string(7181753, "user@example.com")
        >>> tree = xml_tree_from_string(xml_content, strip_text_styling=True)
        >>> root = tree.getroot()
        >>> title = root.xpath("//article-title/text()")[0]
        >>> print(f"Article title: {title}")

    Note:
        This function automatically applies clean_xml_string() preprocessing
        before parsing to handle common XML formatting issues found in
        PMC articles from NCBI.
    """
    cleaned = clean_xml_string(xml_string, strip_text_styling, verbose)
    tree = ET.ElementTree(ET.fromstring(cleaned))
    return tree


def validate_xml(tree: ET.ElementTree) -> bool:
    """Validate XML document against PMC DTD schema definitions.

    Performs structural validation of PMC article XML against the appropriate
    Document Type Definition (DTD) schema. Handles DTD resolution, entity
    amplification limits, and provides graceful fallbacks for validation issues.

    Args:
        tree: Parsed XML document tree to validate

    Returns:
        bool: True if validation succeeds or is skipped due to DTD issues,
              False if validation explicitly fails

    Raises:
        NoDTDFoundError: If the DTD URL is unsupported or DTD file is missing

    Warns:
        ValidationWarning: When DTD is not specified or DTD parsing fails
                          but XML structure is accepted

    Examples:
        >>> xml_content = fetch_pmc_xml_string(7181753, "user@example.com")
        >>> tree = xml_tree_from_string(xml_content)
        >>> is_valid = validate_xml(tree)
        >>> print(f"XML is valid: {is_valid}")

    Note:
        The function gracefully handles DTD entity amplification limits
        by falling back to basic XML well-formedness validation when
        full DTD validation is not possible.
    """
    doctype = tree.docinfo.doctype
    match = DTD_URL_PATTERN.search(doctype)
    if match:
        url = match.group(1)
        if url not in SUPPORTED_DTD_URLS:
            raise NoDTDFoundError(f"Unsupported DTD URL: {url}")
    else:
        # If no DTD is referenced **do not** fail hard – fall back to XML well-formedness.
        warnings.warn(
            "DTD not specified – skipping validation.",
            ValidationWarning,
            stacklevel=2,
        )
        return True
    match = END_OF_URL_PATTERN.search(url)
    filename = match.group(0)
    dtd_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "DTDs",
        filename,
    )
    with open(dtd_path, encoding="utf-8") as f:
        dtd_doc = f.read()
    if not dtd_doc:
        raise NoDTDFoundError(clean_doc("DTD not found."))

    try:
        dtd = ET.DTD(StringIO(dtd_doc))
        return dtd.validate(tree)
    except ET.DTDParseError as e:
        # Handle DTD parsing errors (including entity amplification limits)
        error_msg = str(e)
        if (
            "Maximum entity amplification factor exceeded" in error_msg
            or "error parsing DTD" in error_msg
        ):
            warnings.warn(
                f"DTD validation skipped due to DTD parsing error: {error_msg}. "
                f"XML structure will be validated without DTD constraints.",
                ValidationWarning,
                stacklevel=2,
            )
            # Return True to indicate we're accepting the XML structure as valid
            # since it parsed successfully as XML
            return True
        # Re-raise other DTD parsing errors
        raise


def get_xml(
    pmcid: int,
    email: str,
    download: bool = False,
    validate: bool = True,
    strip_text_styling: bool = True,
    verbose: bool = False,
) -> ET.ElementTree:
    """Complete pipeline from PMCID to validated, parsed XML ElementTree.

    High-level function that orchestrates the entire XML acquisition and
    processing pipeline: downloading from NCBI, cleaning, parsing, and
    validating. This is the main entry point for converting a PMCID into
    a ready-to-use XML document tree.

    Args:
        pmcid: PubMed Central ID of the target article
        email: Contact email address required by NCBI Entrez API
        download: If True, cache raw XML locally in data/ directory for reuse
        validate: If True, perform DTD validation against PMC schema
        strip_text_styling: If True, remove HTML-style formatting tags during processing
        verbose: If True, emit detailed progress and diagnostic messages

    Returns:
        ET.ElementTree: Complete parsed and validated XML document tree
                       ready for content extraction and analysis

    Warns:
        ValidationWarning: When validation is skipped (validate=False)

    Examples:
        >>> # Basic usage with validation
        >>> tree = get_xml(7181753, "user@example.com")
        >>> root = tree.getroot()
        >>> title = root.xpath("//article-title/text()")[0]
        >>>
        >>> # With caching and verbose output
        >>> tree = get_xml(
        ...     7181753, "user@example.com",
        ...     download=True,
        ...     validate=True,
        ...     verbose=True
        ... )
        >>>
        >>> # Fast processing without validation
        >>> tree = get_xml(
        ...     7181753, "user@example.com",
        ...     validate=False,
        ...     strip_text_styling=True
        ... )

    Note:
        This function combines all the individual steps (fetch, clean, parse, validate)
        into a single convenient interface. For more control over individual steps,
        use the component functions directly.
    """
    xml_text = fetch_pmc_xml_string(pmcid, email, download, verbose)
    tree = xml_tree_from_string(xml_text, strip_text_styling, verbose)
    if validate:
        validate_xml(tree)
    else:
        warnings.warn(
            f"Scraping XML for PMCID {pmcid} without validation.",
            ValidationWarning,
            stacklevel=2,
        )
    return tree


# ---------------------------------------------------------------------------
# Local / bulk XML file support
# ---------------------------------------------------------------------------


def parse_local_xml(
    xml_path: str | Path,
    *,
    strip_text_styling: bool = True,
    validate: bool = False,
    verbose: bool = False,
) -> tuple[ET.ElementTree, int | None]:
    """Read and parse a local JATS XML file from disk.

    This function provides an alternative to :func:`get_xml` for working with
    bulk-exported PMC data that has already been downloaded (e.g. from the
    PMC FTP service at https://ftp.ncbi.nlm.nih.gov/pub/pmc/).  By reading
    from disk instead of fetching over the network, processing is orders of
    magnitude faster and does not require timeouts or email authentication.

    Args:
        xml_path: Path to a JATS XML file on disk.
        strip_text_styling: If True, remove HTML-style formatting tags before
            parsing (same behaviour as :func:`get_xml`).
        validate: If True, perform DTD validation against PMC schema.
        verbose: If True, emit progress logging messages.

    Returns:
        tuple[ET.ElementTree, int | None]: A 2-tuple of:
            - The parsed XML document tree.
            - The PMCID extracted from ``<article-id pub-id-type="pmc">``,
              or ``None`` if the element is not present in the XML.

    Raises:
        FileNotFoundError: If *xml_path* does not exist.
        ET.XMLSyntaxError: If the file contains malformed XML.

    Examples:
        >>> tree, pmcid = parse_local_xml("path/to/PMC7181753.xml")
        >>> root = tree.getroot()
        >>> title = root.xpath("//article-title/text()")[0]
        >>> print(f"PMCID {pmcid}: {title}")
        >>>
        >>> # Parse without any cleaning
        >>> tree, pmcid = parse_local_xml(
        ...     "article.xml",
        ...     strip_text_styling=False,
        ...     validate=True,
        ... )
    """
    xml_path = Path(xml_path)
    if not xml_path.exists():
        raise FileNotFoundError(f"XML file not found: {xml_path}")

    # Read as bytes first so lxml can handle the encoding declaration
    # itself (ET.fromstring rejects Unicode strings that contain an
    # <?xml encoding="..."?> declaration).
    raw_bytes = xml_path.read_bytes()

    # Detect encoding from XML declaration or fall back to UTF-8
    try:
        xml_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        # Try common fallback encodings
        for enc in ("latin-1", "iso-8859-1", "windows-1252", "ascii"):
            try:
                xml_text = raw_bytes.decode(enc)
                if verbose:
                    logger.info("Decoded %s with fallback encoding: %s", xml_path, enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            # Last resort: decode with errors replaced
            xml_text = raw_bytes.decode("utf-8", errors="replace")
            if verbose:
                logger.warning(
                    "Could not detect encoding for %s, using UTF-8 with replacement",
                    xml_path,
                )

    if verbose:
        logger.info("Read %d bytes from %s", len(raw_bytes), xml_path)

    # Apply optional text-styling cleanup (operates on str)
    cleaned = clean_xml_string(xml_text, strip_text_styling, verbose)
    # Parse from bytes to honour encoding declarations
    tree = ET.ElementTree(ET.fromstring(cleaned.encode("utf-8")))

    if validate:
        validate_xml(tree)

    # Extract PMCID from the parsed XML
    root = tree.getroot()
    pmc_id_elements = root.xpath(
        './/article-id[@pub-id-type="pmc"]/text()'
    ) or root.xpath('.//article-meta/article-id[@pub-id-type="pmc"]/text()')

    pmcid: int | None = None
    if pmc_id_elements:
        raw = str(pmc_id_elements[0]).strip().upper().replace("PMC", "")
        try:
            pmcid = int(raw)
        except (ValueError, TypeError):
            if verbose:
                logger.warning("Could not parse PMCID from XML: %r", pmc_id_elements[0])

    return tree, pmcid
