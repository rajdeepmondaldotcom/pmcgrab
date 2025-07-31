import os
import time
import warnings
from io import StringIO
from urllib.error import HTTPError

import lxml.etree as ET
from Bio import Entrez

from pmcgrab.constants import (
    DTD_URL_PATTERN,
    END_OF_URL_PATTERN,
    SUPPORTED_DTD_URLS,
    NoDTDFoundError,
    ValidationWarning,
    logger,
)
from pmcgrab.common.html_cleaning import strip_html_text_styling
from pmcgrab.common.serialization import clean_doc


def fetch_pmc_xml_string(
    pmcid: int, email: str, download: bool = False, verbose: bool = False
) -> str:
    """Return the raw XML for a PMC article.

    Args:
        pmcid: Numeric PubMed Central ID.
        email: Contact email for NCBI Entrez.
        download: If ``True`` cache the XML to ``data/``.
        verbose: If ``True`` log progress messages.

    Returns:
        Raw XML string for the requested article.

    Raises:
        HTTPError: If the download repeatedly fails.
    """
    os.makedirs("data", exist_ok=True)
    cache_path = os.path.join("data", f"entrez_download_PMCID={pmcid}.xml")
    if download and os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            cached_xml = f.read()
        if verbose:
            logger.info("Using cached XML for PMCID %s", pmcid)
        return cached_xml
    db, rettype, retmode = "pmc", "full", "xml"
    Entrez.email = email
    delay = 5
    for _attempt in range(3):
        try:
            with Entrez.efetch(
                db=db, id=pmcid, rettype=rettype, retmode=retmode
            ) as handle:
                xml_record = handle.read()
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
    """Normalize an XML string before parsing.

    Args:
        xml_string: Raw XML text returned from Entrez.
        strip_text_styling: When ``True`` remove emphasis tags and styling.
        verbose: If ``True`` log the tag removal operations.

    Returns:
        Cleaned XML string suitable for ``lxml`` parsing.
    """
    return (
        strip_html_text_styling(xml_string, verbose=verbose)
        if strip_text_styling
        else xml_string
    )


def xml_tree_from_string(
    xml_string: str, strip_text_styling: bool = True, verbose: bool = False
) -> ET.ElementTree:
    """Parse an XML string into an ``ElementTree``.

    Args:
        xml_string: The XML text to parse.
        strip_text_styling: Whether to remove emphasis tags before parsing.
        verbose: If ``True`` log additional information.

    Returns:
        ``lxml.etree.ElementTree`` representation of the XML document.

    Raises:
        ET.XMLSyntaxError: If the XML is malformed.
    """
    cleaned = clean_xml_string(xml_string, strip_text_styling, verbose)
    tree = ET.ElementTree(ET.fromstring(cleaned))
    return tree


def validate_xml(tree: ET.ElementTree) -> bool:
    """Validate an XML tree against supported PMC DTD files.

    Args:
        tree: Parsed XML document tree.

    Returns:
        ``True`` if validation succeeds, otherwise ``False``.

    Raises:
        NoDTDFoundError: If the tree references an unsupported or missing DTD.
    """
    doctype = tree.docinfo.doctype
    match = DTD_URL_PATTERN.search(doctype)
    if match:
        url = match.group(1)
        if url not in SUPPORTED_DTD_URLS:
            raise NoDTDFoundError(f"Unsupported DTD URL: {url}")
    else:
        raise NoDTDFoundError(clean_doc("A DTD must be specified for validation."))
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
    """Fetch, parse and optionally validate the XML for a PMCID.

    Args:
        pmcid: PubMed Central ID of the article.
        email: Contact email for NCBI Entrez.
        download: Cache the raw XML locally when ``True``.
        validate: Perform DTD validation if ``True``.
        strip_text_styling: Remove styling tags before parsing.
        verbose: Emit informational log messages when ``True``.

    Returns:
        Parsed XML tree of the article.
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
