import copy
import datetime
import uuid
import warnings
from typing import Dict, List, Optional, Tuple, Union

import lxml.etree as ET
import pandas as pd

from .constants import (
    UnexpectedMultipleMatchWarning,
    UnexpectedZeroMatchWarning,
    MultipleTitleWarning,
    UnhandledTextTagWarning,
    ReadHTMLFailure,
    UnmatchedCitationWarning,
    UnmatchedTableWarning,
    ValidationWarning,
    logger,
)
from .utils import BasicBiMap
from .model import TextSection, TextParagraph, TextTable
from .fetch import get_xml

def gather_title(root: ET.Element) -> Optional[str]:
    """Extract the article title from the XML.

    Args:
        root: ``<article>`` root element of the paper.

    Returns:
        The title text if found, otherwise ``None``.
    """
    matches = root.xpath("//article-title/text()")
    if len(matches) > 1:
        warnings.warn(
            "Multiple titles found; using the first.",
            UnexpectedMultipleMatchWarning,
        )
    if not matches:
        warnings.warn("No article title found.", UnexpectedZeroMatchWarning)
        return None
    return matches[0]

def extract_contributor_info(root: ET.Element, contributors: List[ET.Element]) -> List[Tuple]:
    """Gather contributor metadata such as names, emails and affiliations."""
    result = []
    for contrib in contributors:
        ctype = (contrib.get("contrib-type") or "").capitalize().strip()
        first = contrib.findtext(".//given-names")
        if first:
            first = first.strip()
        last = contrib.findtext(".//surname")
        if last:
            last = last.strip()
        addr = contrib.findtext(".//address/email")
        if addr:
            addr = addr.strip()
        affils = []
        for aff in contrib.xpath(".//xref[@ref-type='aff']"):
            aid = aff.get("rid")
            texts = root.xpath(f"//contrib-group/aff[@id='{aid}']/text()[not(parent::label)]")
            if len(texts) > 1:
                warnings.warn("Multiple affiliations found for one ID.", UnexpectedMultipleMatchWarning)
            if not texts:
                texts = ["Affiliation data not found."]
            inst = root.xpath(f"//contrib-group/aff[@id='{aid}']/institution-wrap/institution/text()")
            inst_str = " ".join(str(i) for i in inst)
            affils.append(f"{aid.strip()}: {inst_str}{texts[0].strip()}" if inst_str else f"{aid.strip()}: {texts[0].strip()}")
        result.append((ctype, first, last, addr, affils))
    return result

def gather_authors(root: ET.Element) -> Optional[pd.DataFrame]:
    """Collect information on article authors.

    Args:
        root: ``<article>`` root element.

    Returns:
        ``pandas.DataFrame`` with columns ``Contributor_Type``, ``First_Name``,
        ``Last_Name``, ``Email_Address`` and ``Affiliations``. ``None`` is
        returned when no authors are present.
    """
    authors = root.xpath(".//contrib[@contrib-type='author']")
    if not authors:
        warnings.warn("No authors found.", UnexpectedZeroMatchWarning)
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
        ],
    )

def gather_non_author_contributors(root: ET.Element) -> Union[str, pd.DataFrame]:
    """Get contributor metadata for non-author roles.

    Args:
        root: ``<article>`` root element.

    Returns:
        ``pandas.DataFrame`` containing non-author contributor information,
        or a message string when no such contributors exist.
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
            ],
        )
    return "No non-author contributors found."

def _collect_sections(
    parent: ET.Element, context: str, ref_map: BasicBiMap
) -> List[Union[TextSection, TextParagraph]]:
    """Return ``TextSection`` or ``TextParagraph`` objects from a given element."""
    sections: List[Union[TextSection, TextParagraph]] = []
    for child in parent:
        if child.tag == "sec":
            sections.append(TextSection(child, ref_map=ref_map))
        elif child.tag == "p":
            sections.append(TextParagraph(child, ref_map=ref_map))
        else:
            warnings.warn(
                f"Unexpected tag {child.tag} in {context}.",
                UnhandledTextTagWarning,
            )
    return sections


def _gather_sections(
    root: ET.Element,
    xpath: str,
    missing_warning: str,
    context: str,
    ref_map: BasicBiMap,
) -> Optional[List[Union[TextSection, TextParagraph]]]:
    """Locate and parse text sections specified by ``xpath``."""
    nodes = root.xpath(xpath)
    if not nodes:
        warnings.warn(missing_warning, UnexpectedZeroMatchWarning)
        return None
    if len(nodes) > 1:
        warnings.warn(
            f"Multiple {context} tags found; using the first.",
            UnexpectedMultipleMatchWarning,
        )
    return _collect_sections(nodes[0], context, ref_map)


def gather_abstract(
    root: ET.Element, ref_map: BasicBiMap
) -> Optional[List[Union[TextSection, TextParagraph]]]:
    """Parse the abstract into structured sections.

    Args:
        root: ``<article>`` root element.
        ref_map: Shared reference map for resolving citations and tables.

    Returns:
        List of :class:`TextSection` and :class:`TextParagraph` objects or
        ``None`` if no abstract is present.
    """
    return _gather_sections(
        root,
        "//abstract",
        "No abstract found.",
        "abstract",
        ref_map,
    )

def gather_body(
    root: ET.Element, ref_map: BasicBiMap
) -> Optional[List[Union[TextSection, TextParagraph]]]:
    """Parse the article body into structured sections.

    Args:
        root: ``<article>`` root element.
        ref_map: Shared reference map for citations and tables.

    Returns:
        List of text elements representing the body, or ``None`` if absent.
    """
    return _gather_sections(
        root,
        "//body",
        "No <body> tag found.",
        "body",
        ref_map,
    )

def gather_journal_id(root: ET.Element) -> Dict[str, str]:
    """Return a mapping of journal-id types to values."""
    ids = root.xpath("//journal-meta/journal-id")
    return {jid.get("journal-id-type"): jid.text for jid in ids}

def gather_journal_title(root: ET.Element) -> Optional[Union[List[str], str]]:
    """Retrieve the journal title text."""
    titles = [t.text for t in root.xpath("//journal-title")]
    if not titles:
        warnings.warn("No journal title found.", UnexpectedZeroMatchWarning)
        return None
    return titles if len(titles) > 1 else titles[0]

def gather_issn(root: ET.Element) -> Dict[str, str]:
    """Return a mapping of ISSN publication types to values."""
    issns = root.xpath("//journal-meta/issn")
    return {issn.get("pub-type"): issn.text for issn in issns}

def gather_publisher_name(root: ET.Element) -> Union[str, List[str]]:
    """Return the publisher name or list of names."""
    pubs = root.xpath("//journal-meta/publisher/publisher-name")
    return pubs[0].text if len(pubs) == 1 else [p.text for p in pubs]

def gather_article_id(root: ET.Element) -> Dict[str, str]:
    """Return a mapping of article-id types to values."""
    ids = root.xpath("//article-meta/article-id")
    return {aid.get("pub-id-type"): aid.text for aid in ids}

def gather_article_types(root: ET.Element) -> Optional[List[str]]:
    """Return the list of article type headings."""
    cats = root.xpath("//article-meta/article-categories")
    if not cats:
        warnings.warn("No article-categories found.", UnexpectedZeroMatchWarning)
        return None
    heading = cats[0].xpath("subj-group[@subj-group-type='heading']/subject")
    texts = [h.text for h in heading]
    if not texts:
        return ["No article type found."]
    return texts

def gather_article_categories(root: ET.Element) -> Optional[List[Dict[str, str]]]:
    """Return article categories other than the primary headings."""
    cats = root.xpath("//article-meta/article-categories")
    if not cats:
        warnings.warn("No article-categories found.", UnexpectedZeroMatchWarning)
        return None
    others = cats[0].xpath("subj-group[not(@subj-group-type='heading')]/subject")
    result = [{other.get("subj-group-type"): other.text} for other in others]
    if not result:
        return [{"info": "No extra article categories found."}]
    return result

def gather_published_date(root: ET.Element) -> Dict[str, datetime.date]:
    """Return publication dates keyed by publication type."""
    dates = {}
    for pd_elem in root.xpath("//article-meta/pub-date"):
        ptype = pd_elem.get("pub-type")
        year = int(pd_elem.xpath("year/text()")[0]) if pd_elem.xpath("year/text()") else 1
        month = int(pd_elem.xpath("month/text()")[0]) if pd_elem.xpath("month/text()") else 1
        day = int(pd_elem.xpath("day/text()")[0]) if pd_elem.xpath("day/text()") else 1
        dates[ptype] = datetime.date(year, month, day)
    return dates

def gather_volume(root: ET.Element) -> Optional[str]:
    """Return the volume number if available."""
    vol = root.xpath("//article-meta/volume/text()")
    if not vol:
        warnings.warn("No volume found.", UnexpectedZeroMatchWarning)
        return None
    return vol[0]

def gather_issue(root: ET.Element) -> Optional[str]:
    """Return the issue number if available."""
    iss = root.xpath("//article-meta/issue/text()")
    if not iss:
        warnings.warn("No issue found.", UnexpectedZeroMatchWarning)
        return None
    return iss[0]

def gather_permissions(root: ET.Element) -> Optional[Dict[str, str]]:
    """Return copyright, license type and license text."""
    cp = root.xpath("//article-meta/permissions/copyright-statement/text()")
    cp_stmt = cp[0] if cp else "No copyright statement found."
    lic = root.xpath("//article-meta/permissions/license")
    if not lic:
        warnings.warn("No license found.", UnexpectedZeroMatchWarning)
        return None
    if len(lic) > 1:
        warnings.warn(
            "Multiple licenses found; using the first.",
            UnexpectedMultipleMatchWarning,
        )
    lic_elem = lic[0]
    lic_type = lic_elem.get("license-type", "Not Specified")
    lic_text = "\n".join(
        str(TextParagraph(child))
        for child in lic_elem
        if child.tag == "license-p"
    )
    return {
        "Copyright Statement": cp_stmt,
        "License Type": lic_type,
        "License Text": lic_text,
    }

def gather_funding(root: ET.Element) -> Optional[List[str]]:
    """Return a list of funding institutions if provided."""
    fund = []
    for group in root.xpath("//article-meta/funding-group"):
        fund.extend(
            group.xpath("award-group/funding-source/institution/text()")
        )
    return fund if fund else None

def gather_footnote(root: ET.Element) -> Optional[str]:
    """Return concatenated footnote text."""
    foot = []
    for fn in root.xpath("//back/fn-group/fn"):
        for child in fn:
            if child.tag == "p":
                foot.append(str(TextParagraph(child)))
            else:
                warnings.warn(
                    f"Unexpected tag {child.tag} in footnote.",
                    UnhandledTextTagWarning,
                )
    return " - ".join(foot) if foot else None

def gather_acknowledgements(root: ET.Element) -> Union[List[str], str]:
    """Return a list of acknowledgement paragraphs."""
    return [" ".join(match.itertext()).strip() for match in root.xpath("//ack")]

def gather_notes(root: ET.Element) -> List[str]:
    """Return the list of notes not embedded within other notes."""
    return [
        stringify_note(note)
        for note in root.xpath("//notes")
        if note.getparent().tag != "notes"
    ]

def stringify_note(root: ET.Element) -> str:
    """Recursively convert a ``notes`` element into formatted text."""
    note = ""
    for child in root:
        if child.tag == "title":
            note += f"Title: {child.text}\n"
        elif child.tag == "p":
            note += child.text or ""
        elif child.tag == "notes":
            note += "\n" + textwrap.indent(stringify_note(child), " " * 4)
    return note.strip()

def gather_custom_metadata(root: ET.Element) -> Optional[Dict[str, str]]:
    """Return custom metadata present in the article."""
    custom = {}
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
    return custom if custom else None

def _parse_citation(citation_root: ET.Element) -> Union[Dict[str, Union[List[str], str]], str]:
    """Parse a citation entry into a dictionary of reference details."""
    authors = citation_root.xpath('.//person-group[@person-group-type="author"]/name')
    if not authors:
        mixed = citation_root.xpath("//mixed-citation/text()")
        if mixed:
            return str(mixed[0])
        warnings.warn(
            f"No authors found in citation {citation_root.get('id')}",
            UnexpectedZeroMatchWarning,
        )
    return {
        "Authors": [
            f"{extract_xpath_text_safely(a, 'given-names')} {extract_xpath_text_safely(a, 'surname')}"
            for a in authors
        ],
        "Title": extract_xpath_text_safely(citation_root, ".//article-title"),
        "Source": extract_xpath_text_safely(citation_root, ".//source"),
        "Year": extract_xpath_text_safely(citation_root, ".//year"),
        "Volume": extract_xpath_text_safely(citation_root, ".//volume"),
        "FirstPage": extract_xpath_text_safely(citation_root, ".//fpage"),
        "LastPage": extract_xpath_text_safely(citation_root, ".//lpage"),
        "DOI": extract_xpath_text_safely(citation_root, './/pub-id[@pub-id-type="doi"]'),
        "PMID": extract_xpath_text_safely(citation_root, './/pub-id[@pub-id-type="pmid"]'),
    }

def extract_xpath_text_safely(root: ET.Element, xpath: str, verbose: bool = False) -> Optional[str]:
    """Return the text at ``xpath`` or ``None`` if not found."""
    try:
        el = root.find(xpath)
        return el.text if el is not None else None
    except AttributeError:
        if verbose:
            warnings.warn(
                f"Failed to extract text for XPath {xpath} in element with ID {root.get('id')}",
                RuntimeWarning,
            )
    return None

def process_reference_map(paper_root: ET.Element, ref_map: BasicBiMap) -> BasicBiMap:
    """Resolve reference map items to structured citation or table objects."""
    cleaned = {}
    for key, item in ref_map.items():
        root = ET.fromstring(item)
        if root.tag == "xref":
            rtype = root.get("ref-type")
            if rtype == "bibr":
                rid = root.get("rid")
                if not rid:
                    warnings.warn(
                        f"Citation without a reference id: {root.text}",
                        UnmatchedCitationWarning,
                    )
                    continue
                matches = paper_root.xpath(f"//ref[@id='{rid}']")
                if not matches:
                    warnings.warn(
                        f"No matching reference for citation {root.text}",
                        UnmatchedCitationWarning,
                    )
                    continue
                if len(matches) > 1:
                    warnings.warn(
                        "Multiple references found; using the first.",
                    )
                cleaned[key] = _parse_citation(matches[0])
            elif rtype == "table":
                tid = root.get("rid")
                if not tid:
                    warnings.warn(
                        "Table ref without a reference ID.",
                        UnmatchedTableWarning,
                    )
                    continue
                matches = paper_root.xpath(f"//table-wrap[@id='{tid}']")
                if not matches:
                    warnings.warn(
                        f"Table xref with rid={tid} not matched.",
                        UnmatchedTableWarning,
                    )
                    continue
                if len(matches) > 1:
                    warnings.warn(
                        "Multiple table references found; using the first.",
                    )
                cleaned[key] = TextTable(matches[0])
            else:
                warnings.warn(
                    f"Unknown reference type: {root.get('ref-type')}",
                    RuntimeWarning,
                )
        elif root.tag == "table-wrap":
            cleaned[key] = TextTable(root)
        else:
            warnings.warn(
                f"Unexpected tag {root.tag} in reference map.",
                RuntimeWarning,
            )
            cleaned[key] = ET.tostring(root)
    for key, item in cleaned.items():
        if isinstance(item, int):
            cleaned[key] = cleaned[item]
    return BasicBiMap(cleaned)

def paper_dict_from_pmc(pmcid: int, email: str, download: bool = False, validate: bool = True, verbose: bool = False, suppress_warnings: bool = False, suppress_errors: bool = False) -> Dict:
    """Convenience wrapper to fetch and parse an article by PMCID."""
    if verbose:
        logger.info("Generating Paper object for PMCID = %s...", pmcid)
    tree = get_xml(pmcid, email, download, validate, verbose=verbose)
    root = tree.getroot()
    return generate_paper_dict(
        pmcid, root, verbose, suppress_warnings, suppress_errors
    )

def generate_paper_dict(pmcid: int, root: ET.Element, verbose: bool = False, suppress_warnings: bool = False, suppress_errors: bool = False) -> Dict:
    """Generate a dictionary representation of a paper from its XML root."""
    if suppress_warnings:
        warnings.simplefilter("ignore")
    try:
        d = build_complete_paper_dict(pmcid, root, verbose)
    except Exception as e:
        if suppress_errors:
            d = {}
        else:
            raise e
    if suppress_warnings:
        warnings.simplefilter("default")
    return d

def build_complete_paper_dict(pmcid: int, root: ET.Element, verbose: bool = False) -> Dict:
    """Create a comprehensive dictionary of paper metadata and content."""
    ref_map = BasicBiMap()
    d = {
        "PMCID": pmcid,
        "Title": gather_title(root),
        "Authors": gather_authors(root),
        "Non-Author Contributors": gather_non_author_contributors(root),
        "Abstract": gather_abstract(root, ref_map),
        "Body": gather_body(root, ref_map),
        "Journal ID": gather_journal_id(root),
        "Journal Title": gather_journal_title(root),
        "ISSN": gather_issn(root),
        "Publisher Name": gather_publisher_name(root),
        "Article ID": gather_article_id(root),
        "Article Types": gather_article_types(root),
        "Article Categories": gather_article_categories(root),
        "Published Date": gather_published_date(root),
        "Volume": gather_volume(root),
        "Issue": gather_issue(root),
        "Permissions": gather_permissions(root),
        "Funding": gather_funding(root),
        "Footnote": gather_footnote(root),
        "Acknowledgements": gather_acknowledgements(root),
        "Notes": gather_notes(root),
        "Custom Meta": gather_custom_metadata(root),
        "Ref Map With Tags": copy.deepcopy(ref_map),
        "Ref Map": process_reference_map(root, ref_map),
    }
    if verbose:
        logger.info("Finished generating Paper object for PMCID = %s", pmcid)
    return d

