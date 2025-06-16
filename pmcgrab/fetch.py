import os
import time
import warnings
from io import StringIO
from urllib.error import HTTPError

import lxml.etree as ET
from Bio import Entrez

from .constants import DTD_URL_PATTERN, END_OF_URL_PATTERN, SUPPORTED_DTD_URLS, NoDTDFoundError, ValidationWarning, logger
from .utils import strip_html_text_styling, clean_doc

def fetch_pmc_xml_string(pmcid: int, email: str, download: bool = False, verbose: bool = False) -> str:
    """Fetch the raw XML for a PMCID from Entrez, optionally caching it."""
    os.makedirs("data", exist_ok=True)
    cache_path = os.path.join("data", f"entrez_download_PMCID={pmcid}.xml")
    if download and os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            cached_xml = f.read()
        if verbose:
            logger.info("Using cached XML for PMCID %s", pmcid)
        return cached_xml
    db, rettype, retmode = "pmc", "full", "xml"
    Entrez.email = email
    delay = 5
    for attempt in range(3):
        try:
            with Entrez.efetch(db=db, id=pmcid, rettype=rettype, retmode=retmode) as handle:
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
    raise HTTPError(f"Failed to fetch PMCID {pmcid} after retries", None, None, None, None)

def clean_xml_string(xml_string: str, strip_text_styling: bool = True, verbose: bool = False) -> str:
    """Optionally remove HTML-style tags from text to simplify parsing."""
    return strip_html_text_styling(xml_string, verbose) if strip_text_styling else xml_string

def xml_tree_from_string(xml_string: str, strip_text_styling: bool = True, verbose: bool = False) -> ET.ElementTree:
    """Convert an XML string into an ``ElementTree``."""
    cleaned = clean_xml_string(xml_string, strip_text_styling, verbose)
    try:
        tree = ET.ElementTree(ET.fromstring(cleaned))
    except ET.XMLSyntaxError:
        raise
    return tree

def validate_xml(tree: ET.ElementTree) -> bool:
    """Validate an XML ``ElementTree`` against supported PMC DTDs."""
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
    dtd_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "DTDs", filename)
    with open(dtd_path, "r", encoding="utf-8") as f:
        dtd_doc = f.read()
    if not dtd_doc:
        raise NoDTDFoundError(clean_doc("DTD not found."))
    dtd = ET.DTD(StringIO(dtd_doc))
    return dtd.validate(tree)

def get_xml(pmcid: int, email: str, download: bool = False, validate: bool = True, strip_text_styling: bool = True, verbose: bool = False) -> ET.ElementTree:
    """Retrieve and optionally validate the XML tree for a given PMCID."""
    xml_text = fetch_pmc_xml_string(pmcid, email, download, verbose)
    tree = xml_tree_from_string(xml_text, strip_text_styling, verbose)
    if validate:
        validate_xml(tree)
    else:
        warnings.warn(
            f"Scraping XML for PMCID {pmcid} without validation.",
            ValidationWarning,
        )
    return tree

