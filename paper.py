#!/usr/bin/env python3
import argparse
import copy
import datetime
import gc
import html
import json
import logging
import os
import random
import re
import signal
import textwrap
import time
import uuid
import warnings
from collections.abc import Hashable
from inspect import cleandoc
from io import StringIO
import importlib.resources
from itertools import chain
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from urllib.error import HTTPError

import lxml.etree as ET
import pandas as pd
import requests
from Bio import Entrez
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)
warnings.formatwarning = lambda msg, cat, *args, **kwargs: f"{cat.__name__}: {msg}\n\n"
warnings.filterwarnings("ignore")

SUPPORTED_DTD_URLS = [
    "https://dtd.nlm.nih.gov/ncbi/pmc/articleset/nlm-articleset-2.0.dtd"
]
DTD_URL_PATTERN = re.compile(r'"(https?://\S+)"')
END_OF_URL_PATTERN = re.compile(r"[^/]+$")

class NoDTDFoundError(Exception):
    pass

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("Operation timed out")
signal.signal(signal.SIGALRM, timeout_handler)

EMAILS = sorted(set([
    "bk68g1gx@test.com", "wkv1h06c@sample.com", "m42touro@sample.com", "vy8u7tsx@test.com",
    "8xsqaxke@sample.com", "cilml02q@sample.com", "1s1ywssv@demo.com", "pfd4bf0y@demo.com",
    "hvjhnv7o@test.com", "vtirmn0j@sample.com", "4bk68g1gx0y4@sample.com", "a8riw1tsm42t@sample.com",
    "uro2fp0bt1w@demo.com", "8xsqaxkenhc@test.com", "js2rq1s1yw@demo.com", "7t2pfd4bf0yf@test.com",
    "5h1cwqg2p0hx@sample.com", "n0jc5ob2lrb@demo.com", "hng0gryqf@test.com", "iftxphoxuk5@demo.com",
    "bwd4n34n0e@sample.com", "bpx4le9l@demo.com", "sjqexrltn@test.com", "r6xjuxkjahc@demo.com",
    "0ppd1x4w@test.com", "ur58ralllmn@sample.com", "ifm9ikmz5@test.com", "72z4j1pvi@demo.com",
    "zsgq0a1y1s@sample.com", "b25m7bv9lrdr@demo.com", "g28fn53pg@demo.com", "yimjg6il5@sample.com",
    "srsu7jehnqar@demo.com", "c4ktfvaho@demo.com", "do19vw6hbad@demo.com", "1fk0t7j1@test.com",
    "ym4w8xkimeu@test.com", "5icttn2von8@sample.com", "twy6ejv0@test.com", "nmjvr8pzr9@demo.com"
]))
email_counter = 0

class ReversedBiMapComparisonWarning(Warning): pass
class ValidationWarning(Warning): pass
class MultipleTitleWarning(Warning): pass
class UnhandledTextTagWarning(Warning): pass
class ReadHTMLFailure(Warning): pass
class UnexpectedMultipleMatchWarning(Warning): pass
class UnexpectedZeroMatchWarning(Warning): pass
class UnmatchedCitationWarning(Warning): pass
class UnmatchedTableWarning(Warning): pass
class UnexpectedTagWarning(Warning): pass
class EmptyTextWarning(Warning): pass
class PubmedHTTPError(Warning): pass

def clean_doc(s: str) -> str:
    return cleandoc(s).replace("\n", "")

def make_hashable(value):
    if isinstance(value, dict):
        return tuple(sorted((k, make_hashable(v)) for k, v in value.items()))
    if isinstance(value, list):
        return tuple(make_hashable(item) for item in value)
    return value

def normalize_value(val):
    if isinstance(val, (datetime.date, datetime.datetime)):
        return val.isoformat()
    if isinstance(val, pd.DataFrame):
        return val.to_dict(orient="records")
    if isinstance(val, dict):
        return {k: normalize_value(v) for k, v in val.items()}
    if isinstance(val, list):
        return [normalize_value(item) for item in val]
    return val

class BasicBiMap(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reverse = {make_hashable(v): k for k, v in self.items()}
    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.reverse[make_hashable(value)] = key
    def __eq__(self, other) -> bool:
        if not isinstance(other, dict):
            return False
        if not super().__eq__(other):
            if isinstance(other, BasicBiMap) and other.reverse == dict(self):
                warnings.warn("BasicBiMap reversed key/value equivalence.", ReversedBiMapComparisonWarning)
            return False
        return True

def fetch_pmc_xml_string(pmcid: int, email: str, download: bool = False, verbose: bool = False) -> str:
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
    return strip_html_text_styling(xml_string, verbose) if strip_text_styling else xml_string

def xml_tree_from_string(xml_string: str, strip_text_styling: bool = True, verbose: bool = False) -> ET.ElementTree:
    cleaned = clean_xml_string(xml_string, strip_text_styling, verbose)
    try:
        tree = ET.ElementTree(ET.fromstring(cleaned))
    except ET.XMLSyntaxError:
        raise
    return tree

def validate_xml(tree: ET.ElementTree) -> bool:
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
    dtd_path = importlib.resources.files("pmcgrab.data.DTDs").joinpath(filename)
    with open(dtd_path, "r", encoding="utf-8") as f:
        dtd_doc = f.read()
    if not dtd_doc:
        raise NoDTDFoundError(clean_doc("DTD not found."))
    dtd = ET.DTD(StringIO(dtd_doc))
    return dtd.validate(tree)

def get_xml(pmcid: int, email: str, download: bool = False, validate: bool = True, strip_text_styling: bool = True, verbose: bool = False) -> ET.ElementTree:
    xml_text = fetch_pmc_xml_string(pmcid, email, download, verbose)
    tree = xml_tree_from_string(xml_text, strip_text_styling, verbose)
    if validate:
        validate_xml(tree)
    else:
        warnings.warn(f"Scraping XML for PMCID {pmcid} without validation.", ValidationWarning)
    return tree

def stringify_children(node: ET.Element, encoding: str = "utf-8") -> str:
    chunks = [c for c in chain((node.text,), chain(*((ET.tostring(child, with_tail=False), child.tail) for child in node)), (node.tail,)) if c]
    decoded = [c.decode(encoding) if isinstance(c, bytes) else c for c in chunks]
    return "".join(decoded).strip()

def remove_html_tags(text: str, removals: List[str], replaces: Dict[str, str], verbose: bool = False) -> str:
    to_remove = removals + [f"</{tag[1:]}" for tag in removals] + [f"</{tag[1:]}" for tag in replaces.keys()]
    to_remove = [tag[:-1] + r"\b[^>]*" + tag[-1] for tag in to_remove]
    to_replace = {tag[:-1] + r"\b[^>]*" + tag[-1]: rep for tag, rep in replaces.items()}
    if verbose:
        logger.info("Removing tags: %s", to_remove)
        logger.info("Replacing tags: %s", to_replace)
    pat = "|".join(to_remove)
    text = re.sub(pat, "", text, flags=re.IGNORECASE)
    for p, r in to_replace.items():
        text = re.sub(p, r, text)
    return text

def strip_html_text_styling(text: str, verbose: bool = False) -> str:
    removes = ["<italic>", "<i>", "<bold>", "<b>", "<underline>", "<u>"]
    reps = {"<sub>": "_", "<sup>": "^", "<ext-link>": "[External URI:]"}
    return remove_html_tags(text, removes, reps, verbose)

def split_text_and_refs(tree_text: str, ref_map: BasicBiMap, id: Optional[str] = None, on_unknown: str = "keep") -> str:
    allowed_tags = ["xref", "fig", "table-wrap"]
    pattern = r"<([a-zA-Z][\w-]*)\b[^>]*>(.*?)</\1>|<([a-zA-Z][\w-]*)\b[^/>]*/?>"
    tag_r = re.compile(pattern, re.DOTALL)
    text = tree_text.strip()
    text = strip_html_text_styling(text)
    cleaned_text = ""
    while text:
        match = tag_r.search(text)
        if match:
            tag_name = match.group(1) or match.group(3)
            tag_contents = match.group(2) if match.group(2) else ""
            full_tag = match.group()
            cleaned_text += text[:match.start()]
            if tag_name not in allowed_tags:
                warnings.warn(f"Tag {tag_name} not allowed. Behavior: {on_unknown}.", UnexpectedTagWarning)
                if on_unknown == "keep":
                    cleaned_text += tag_contents
                text = text[match.end():]
            else:
                if tag_name == "xref":
                    cleaned_text += tag_contents
                if full_tag in ref_map.reverse:
                    ref_num = ref_map.reverse[full_tag]
                else:
                    ref_num = len(ref_map)
                    ref_map[ref_num] = full_tag
                data_ref_tag = generate_typed_mhtml_tag("dataref", str(ref_num))
                cleaned_text += data_ref_tag
                text = text[match.end():]
        else:
            cleaned_text += text
            break
    return cleaned_text

def generate_typed_mhtml_tag(tag_type: str, s: str) -> str:
    return f"[MHTML::{tag_type}::{s}]"

def remove_mhtml_tags(text: str) -> str:
    pat = r"\[MHTML::([^:\[\]]+)::([^:\[\]]+)\]|\[MHTML::([^:\[\]]+)\]"
    return re.sub(pat, "", text)

def define_data_dict() -> Dict[str, str]:
    return {
        "PMCID": "PMCID of the PMC article. Unique.",
        "Title": "Title of the PMC article.",
        "Authors": clean_doc("DataFrame of PMC Authors including names, emails, and affiliations."),
        "Non-Author Contributors": clean_doc("DataFrame of non-author contributors with names, emails, and affiliations."),
        "Abstract": clean_doc("List of TextSections parsed from the abstract. Use Paper.abstract_as_str() for a simple view."),
        "Body": clean_doc("List of TextSections parsed from the body. Use Paper.body_as_str() for a simple view."),
        "Journal ID": clean_doc("Dict of journal ID types and values (e.g. NLM-TA, ISO-ABBREV)."),
        "Journal Title": "Journal title in text.",
        "ISSN": "Dict of ISSN types and values.",
        "Publisher Name": "Name of the publisher.",
        "Publisher Location": "Location of the publisher.",
        "Article ID": clean_doc("Dict of article ID types and values. e.g., p.article_id['pmc'] returns the PMCID."),
        "Article Types": "List of header article types.",
        "Article Categories": "List of non-header article types.",
        "Published Date": clean_doc("Dict of publication dates (e.g., electronic, print)."),
        "Volume": clean_doc("Volume number."),
        "Issue": clean_doc("Issue number."),
        "FPage": "First page of publication.",
        "LPage": "Last page of publication.",
        "Permissions": clean_doc("Summary of copyright, license type, and full license text."),
        "Copyright Statement": clean_doc("Copyright statement, typically a short phrase."),
        "License": clean_doc("License type (e.g., Open Access)."),
        "Funding": clean_doc("List of funding groups, important for bias detection."),
        "Footnote": "Text of any footnotes provided with the article.",
        "Acknowledgements": clean_doc("List of acknowledgement statements."),
        "Notes": "List of notes included with the article.",
        "Custom Meta": clean_doc("Dict of custom metadata key/value pairs."),
        "Ref Map": clean_doc("Dict mapping reference indices to reference data for linking text with citations, tables, etc."),
    }

class Paper:
    __tablename__ = "Papers"
    def __init__(self, d: Dict) -> None:
        if not d:
            self.has_data = False
            return
        self.has_data = True
        now = datetime.datetime.now()
        self.last_updated = normalize_value((now.month, now.day, now.year))
        self.pmcid = d.get("PMCID")
        self.title = d.get("Title")
        self.authors = d.get("Authors")
        self.non_author_contributors = d.get("Non-Author Contributors")
        self.abstract = d.get("Abstract")
        self.body = d.get("Body")
        self.journal_id = d.get("Journal ID")
        self.journal_title = d.get("Journal Title")
        self.issn = d.get("ISSN")
        self.publisher_name = d.get("Publisher Name")
        self.publisher_location = d.get("Publisher Location")
        self.article_id = d.get("Article ID")
        self.article_types = d.get("Article Types")
        self.article_categories = d.get("Article Categories")
        self.published_date = d.get("Published Date")
        self.volume = d.get("Volume")
        self.issue = d.get("Issue")
        self.permissions = d.get("Permissions")
        if self.permissions:
            self.copyright = self.permissions.get("Copyright Statement")
            self.license = self.permissions.get("License Type")
        else:
            self.copyright = None
            self.license = None
        self.funding = d.get("Funding")
        self.footnote = d.get("Footnote")
        self.acknowledgements = d.get("Acknowledgements")
        self.notes = d.get("Notes")
        self.custom_meta = d.get("Custom Meta")
        self.ref_map = d.get("Ref Map")
        self._ref_map_with_tags = d.get("Ref Map With Tags")
        self.data_dict = define_data_dict()
        self.vector_collection = None
    @classmethod
    def from_pmc(cls, pmcid: int, email: str, download: bool = False, validate: bool = True, verbose: bool = False, suppress_warnings: bool = False, suppress_errors: bool = False) -> Optional["Paper"]:
        attempts = 3
        d = None
        for _ in range(attempts):
            try:
                d = paper_dict_from_pmc(pmcid, email, download, validate, verbose, suppress_warnings, suppress_errors)
                break
            except HTTPError:
                time.sleep(5)
        if not d:
            warnings.warn(f"Unable to retrieve PMCID {pmcid} from PMC.", PubmedHTTPError)
            return None
        return cls(d)
    def abstract_as_str(self) -> str:
        return "\n".join(str(sec) for sec in self.abstract) if self.abstract else ""

class TextElement:
    def __init__(self, root: ET.Element, parent: Optional["TextElement"] = None, ref_map: Optional[BasicBiMap] = None) -> None:
        self.root = root
        self.parent = parent
        self.ref_map = ref_map if ref_map is not None else BasicBiMap()
    def get_ref_map(self) -> BasicBiMap:
        return self.parent.get_ref_map() if self.parent else self.ref_map
    def set_ref_map(self, ref_map: BasicBiMap) -> None:
        if self.parent:
            self.parent.set_ref_map(ref_map)
        else:
            self.ref_map = ref_map

class TextParagraph(TextElement):
    def __init__(self, p_root: ET.Element, parent: Optional[TextElement] = None, ref_map: Optional[BasicBiMap] = None) -> None:
        super().__init__(p_root, parent, ref_map)
        self.id = p_root.get("id")
        p_subtree = stringify_children(self.root)
        self.text_with_refs = split_text_and_refs(p_subtree, self.get_ref_map(), id=self.id, on_unknown="keep")
        self.text = remove_mhtml_tags(self.text_with_refs)
    def __str__(self) -> str:
        return self.text
    def __eq__(self, other: object) -> bool:
        return isinstance(other, TextParagraph) and self.text_with_refs == other.text_with_refs

class TextSection(TextElement):
    def __init__(self, sec_root: ET.Element, parent: Optional[TextElement] = None, ref_map: Optional[BasicBiMap] = None) -> None:
        super().__init__(sec_root, parent, ref_map)
        self.title: Optional[str] = None
        self.children: List[Union["TextSection", TextParagraph, "TextTable"]] = []
        for child in sec_root:
            if child.tag == "title":
                if self.title:
                    warnings.warn("Multiple titles found; using the first.", MultipleTitleWarning)
                    continue
                self.title = child.text
            elif child.tag == "sec":
                self.children.append(TextSection(child, parent=self, ref_map=self.get_ref_map()))
            elif child.tag == "p":
                self.children.append(TextParagraph(child, parent=self, ref_map=self.get_ref_map()))
            elif child.tag == "table-wrap":
                self.children.append(TextTable(child, parent=self, ref_map=self.get_ref_map()))
            else:
                warnings.warn(f"Unexpected tag {child.tag} in section.", UnhandledTextTagWarning)
        self.text = self.get_section_text()
        self.text_with_refs = self.get_section_text_with_refs()
    def __str__(self) -> str:
        res = f"SECTION: {self.title}:\n" if self.title else ""
        for child in self.children:
            res += "\n" + textwrap.indent(str(child), " " * 4) + "\n"
        return res
    def get_section_text(self) -> str:
        return str(self)
    def get_section_text_with_refs(self) -> str:
        res = f"SECTION: {self.title}:\n" if self.title else ""
        for child in self.children:
            if isinstance(child, TextSection):
                res += "\n" + textwrap.indent(child.get_section_text_with_refs(), " " * 4) + "\n"
            elif isinstance(child, TextParagraph):
                res += "\n" + child.text_with_refs + "\n"
        return res
    def __eq__(self, other: object) -> bool:
        return isinstance(other, TextSection) and self.title == other.title and self.children == other.children

class TextTable(TextElement):
    def __init__(self, table_root: ET.Element, parent: Optional[TextElement] = None, ref_map: Optional[BasicBiMap] = None) -> None:
        super().__init__(table_root, parent, ref_map)
        label = table_root.xpath("label/text()")
        caption = table_root.xpath("caption/p/text()")
        label = label[0] if label else None
        caption = caption[0] if caption else None
        self.df: Optional[pd.io.formats.style.Styler] = None
        table_xml_str = ET.tostring(table_root)
        try:
            tables = pd.read_html(table_xml_str)
            if tables:
                table_df = tables[0]
                title = f"{label}: {caption}" if label and caption else (label or caption)
                if title:
                    table_df = table_df.style.set_caption(title)
                self.df = table_df
        except (ValueError, AttributeError) as e:
            warnings.warn(f"Table parsing failed (label: {label}, caption: {caption}): {e}", ReadHTMLFailure)
    def __str__(self) -> str:
        return str(self.df) if self.df is not None else "Table could not be parsed"
    def __repr__(self) -> str:
        return repr(self.df) if self.df is not None else "Table could not be parsed"

def gather_title(root: ET.Element) -> Optional[str]:
    matches = root.xpath("//article-title/text()")
    if len(matches) > 1:
        warnings.warn("Multiple titles found; using the first.", UnexpectedMultipleMatchWarning)
    if not matches:
        warnings.warn("No article title found.", UnexpectedZeroMatchWarning)
        return None
    return matches[0]

def extract_contributor_info(root: ET.Element, contributors: List[ET.Element]) -> List[Tuple]:
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
    authors = root.xpath(".//contrib[@contrib-type='author']")
    if not authors:
        warnings.warn("No authors found.", UnexpectedZeroMatchWarning)
        return None
    data = extract_contributor_info(root, authors)
    return pd.DataFrame(data, columns=["Contributor_Type", "First_Name", "Last_Name", "Email_Address", "Affiliations"])

def gather_non_author_contributors(root: ET.Element) -> Union[str, pd.DataFrame]:
    non_auth = root.xpath(".//contrib[not(@contrib-type='author')]")
    if non_auth:
        data = extract_contributor_info(root, non_auth)
        return pd.DataFrame(data, columns=["Contributor_Type", "First_Name", "Last_Name", "Email_Address", "Affiliations"])
    return "No non-author contributors found."

def gather_abstract(root: ET.Element, ref_map: BasicBiMap) -> Optional[List[Union[TextSection, TextParagraph]]]:
    abstracts = root.xpath("//abstract")
    if not abstracts:
        warnings.warn("No abstract found.", UnexpectedZeroMatchWarning)
        return None
    if len(abstracts) > 1:
        warnings.warn("Multiple abstracts found; using the first.", UnexpectedMultipleMatchWarning)
    abs_root = abstracts[0]
    result = []
    for child in abs_root:
        if child.tag == "sec":
            result.append(TextSection(child, ref_map=ref_map))
        elif child.tag == "p":
            result.append(TextParagraph(child, ref_map=ref_map))
        else:
            warnings.warn(f"Unexpected tag {child.tag} in abstract.", UnhandledTextTagWarning)
    return result

def gather_body(root: ET.Element, ref_map: BasicBiMap) -> Optional[List[Union[TextSection, TextParagraph]]]:
    bodies = root.xpath("//body")
    if not bodies:
        warnings.warn("No <body> tag found.", UnexpectedZeroMatchWarning)
        return None
    if len(bodies) > 1:
        warnings.warn("Multiple <body> tags found; using the first.", UnexpectedMultipleMatchWarning)
    body_root = bodies[0]
    result = []
    for child in body_root:
        if child.tag == "sec":
            result.append(TextSection(child, ref_map=ref_map))
        elif child.tag == "p":
            result.append(TextParagraph(child, ref_map=ref_map))
        else:
            warnings.warn(f"Unexpected tag {child.tag} in body.", UnhandledTextTagWarning)
    return result

def gather_journal_id(root: ET.Element) -> Dict[str, str]:
    ids = root.xpath("//journal-meta/journal-id")
    return {jid.get("journal-id-type"): jid.text for jid in ids}

def gather_journal_title(root: ET.Element) -> Optional[Union[List[str], str]]:
    titles = [t.text for t in root.xpath("//journal-title")]
    if not titles:
        warnings.warn("No journal title found.", UnexpectedZeroMatchWarning)
        return None
    return titles if len(titles) > 1 else titles[0]

def gather_issn(root: ET.Element) -> Dict[str, str]:
    issns = root.xpath("//journal-meta/issn")
    return {issn.get("pub-type"): issn.text for issn in issns}

def gather_publisher_name(root: ET.Element) -> Union[str, List[str]]:
    pubs = root.xpath("//journal-meta/publisher/publisher-name")
    return pubs[0].text if len(pubs) == 1 else [p.text for p in pubs]

def gather_article_id(root: ET.Element) -> Dict[str, str]:
    ids = root.xpath("//article-meta/article-id")
    return {aid.get("pub-id-type"): aid.text for aid in ids}

def gather_article_types(root: ET.Element) -> Optional[List[str]]:
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
    dates = {}
    for pd_elem in root.xpath("//article-meta/pub-date"):
        ptype = pd_elem.get("pub-type")
        year = int(pd_elem.xpath("year/text()")[0]) if pd_elem.xpath("year/text()") else 1
        month = int(pd_elem.xpath("month/text()")[0]) if pd_elem.xpath("month/text()") else 1
        day = int(pd_elem.xpath("day/text()")[0]) if pd_elem.xpath("day/text()") else 1
        dates[ptype] = datetime.date(year, month, day)
    return dates

def gather_volume(root: ET.Element) -> Optional[str]:
    vol = root.xpath("//article-meta/volume/text()")
    if not vol:
        warnings.warn("No volume found.", UnexpectedZeroMatchWarning)
        return None
    return vol[0]

def gather_issue(root: ET.Element) -> Optional[str]:
    iss = root.xpath("//article-meta/issue/text()")
    if not iss:
        warnings.warn("No issue found.", UnexpectedZeroMatchWarning)
        return None
    return iss[0]

def gather_permissions(root: ET.Element) -> Optional[Dict[str, str]]:
    cp = root.xpath("//article-meta/permissions/copyright-statement/text()")
    cp_stmt = cp[0] if cp else "No copyright statement found."
    lic = root.xpath("//article-meta/permissions/license")
    if not lic:
        warnings.warn("No license found.", UnexpectedZeroMatchWarning)
        return None
    if len(lic) > 1:
        warnings.warn("Multiple licenses found; using the first.", UnexpectedMultipleMatchWarning)
    lic_elem = lic[0]
    lic_type = lic_elem.get("license-type", "Not Specified")
    lic_text = "\n".join(str(TextParagraph(child)) for child in lic_elem if child.tag == "license-p")
    return {"Copyright Statement": cp_stmt, "License Type": lic_type, "License Text": lic_text}

def gather_funding(root: ET.Element) -> Optional[List[str]]:
    fund = []
    for group in root.xpath("//article-meta/funding-group"):
        fund.extend(group.xpath("award-group/funding-source/institution/text()"))
    return fund if fund else None

def gather_footnote(root: ET.Element) -> Optional[str]:
    foot = []
    for fn in root.xpath("//back/fn-group/fn"):
        for child in fn:
            if child.tag == "p":
                foot.append(str(TextParagraph(child)))
            else:
                warnings.warn(f"Unexpected tag {child.tag} in footnote.", UnhandledTextTagWarning)
    return " - ".join(foot) if foot else None

def gather_acknowledgements(root: ET.Element) -> Union[List[str], str]:
    return [" ".join(match.itertext()).strip() for match in root.xpath("//ack")]

def gather_notes(root: ET.Element) -> List[str]:
    return [stringify_note(note) for note in root.xpath("//notes") if note.getparent().tag != "notes"]

def stringify_note(root: ET.Element) -> str:
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
    custom = {}
    for meta in root.xpath("//custom-meta"):
        name = meta.findtext("meta-name")
        value = " ".join(meta.find("meta-value").itertext()) if meta.find("meta-value") is not None else None
        if value:
            if name is None:
                name = str(uuid.uuid4())
            custom[name] = value
    return custom if custom else None

def _parse_citation(citation_root: ET.Element) -> Union[Dict[str, Union[List[str], str]], str]:
    authors = citation_root.xpath('.//person-group[@person-group-type="author"]/name')
    if not authors:
        mixed = citation_root.xpath("//mixed-citation/text()")
        if mixed:
            return str(mixed[0])
        warnings.warn(f"No authors found in citation {citation_root.get('id')}", UnexpectedZeroMatchWarning)
    return {"Authors": [f"{extract_xpath_text_safely(a, 'given-names')} {extract_xpath_text_safely(a, 'surname')}" for a in authors],
            "Title": extract_xpath_text_safely(citation_root, ".//article-title"),
            "Source": extract_xpath_text_safely(citation_root, ".//source"),
            "Year": extract_xpath_text_safely(citation_root, ".//year"),
            "Volume": extract_xpath_text_safely(citation_root, ".//volume"),
            "FirstPage": extract_xpath_text_safely(citation_root, ".//fpage"),
            "LastPage": extract_xpath_text_safely(citation_root, ".//lpage"),
            "DOI": extract_xpath_text_safely(citation_root, './/pub-id[@pub-id-type="doi"]'),
            "PMID": extract_xpath_text_safely(citation_root, './/pub-id[@pub-id-type="pmid"]')}

def extract_xpath_text_safely(root: ET.Element, xpath: str, verbose: bool = False) -> Optional[str]:
    try:
        el = root.find(xpath)
        return el.text if el is not None else None
    except AttributeError:
        if verbose:
            warnings.warn(f"Failed to extract text for XPath {xpath} in element with ID {root.get('id')}", RuntimeWarning)
    return None

def process_reference_map(paper_root: ET.Element, ref_map: BasicBiMap) -> BasicBiMap:
    cleaned = {}
    for key, item in ref_map.items():
        root = ET.fromstring(item)
        if root.tag == "xref":
            rtype = root.get("ref-type")
            if rtype == "bibr":
                rid = root.get("rid")
                if not rid:
                    warnings.warn(f"Citation without a reference id: {root.text}", UnmatchedCitationWarning)
                    continue
                matches = paper_root.xpath(f"//ref[@id='{rid}']")
                if not matches:
                    warnings.warn(f"No matching reference for citation {root.text}", UnmatchedCitationWarning)
                    continue
                if len(matches) > 1:
                    warnings.warn("Multiple references found; using the first.")
                cleaned[key] = _parse_citation(matches[0])
            elif rtype == "table":
                tid = root.get("rid")
                if not tid:
                    warnings.warn("Table ref without a reference ID.", UnmatchedTableWarning)
                    continue
                matches = paper_root.xpath(f"//table-wrap[@id='{tid}']")
                if not matches:
                    warnings.warn(f"Table xref with rid={tid} not matched.", UnmatchedTableWarning)
                    continue
                if len(matches) > 1:
                    warnings.warn("Multiple table references found; using the first.")
                cleaned[key] = TextTable(matches[0])
            else:
                warnings.warn(f"Unknown reference type: {root.get('ref-type')}", RuntimeWarning)
        elif root.tag == "table-wrap":
            cleaned[key] = TextTable(root)
        else:
            warnings.warn(f"Unexpected tag {root.tag} in reference map.", RuntimeWarning)
            cleaned[key] = ET.tostring(root)
    for key, item in cleaned.items():
        if isinstance(item, int):
            cleaned[key] = cleaned[item]
    return BasicBiMap(cleaned)

def paper_dict_from_pmc(pmcid: int, email: str, download: bool = False, validate: bool = True, verbose: bool = False, suppress_warnings: bool = False, suppress_errors: bool = False) -> Dict:
    if verbose:
        logger.info("Generating Paper object for PMCID = %s...", pmcid)
    tree = get_xml(pmcid, email, download, validate, verbose=verbose)
    root = tree.getroot()
    return generate_paper_dict(pmcid, root, verbose, suppress_warnings, suppress_errors)

def generate_paper_dict(pmcid: int, root: ET.Element, verbose: bool = False, suppress_warnings: bool = False, suppress_errors: bool = False) -> Dict:
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

def process_single_pmc(pmc_id: str) -> Optional[Dict[str, Union[str, dict, list]]]:
    global email_counter
    gc.collect()
    paper_info: Dict[str, Union[str, dict, list]] = {}
    body_info: Dict[str, str] = {}
    p_obj = None
    try:
        pmc_id_num = int(pmc_id)
        current_email = EMAILS[(email_counter // 3) % len(EMAILS)]
        email_counter += 1
        signal.alarm(60)
        try:
            p_obj = Paper.from_pmc(pmc_id_num, current_email, download=True, validate=False)
        except TimeoutException:
            return None
        finally:
            signal.alarm(0)
        if p_obj is None:
            return None
        if p_obj.body is not None:
            sec_counter = 1
            for section in p_obj.body:
                try:
                    text = getattr(section, "get_section_text", lambda: str(section))()
                    title = section.title if (hasattr(section, "title") and section.title is not None) else f"Section {sec_counter}"
                    sec_counter += 1
                    body_info[title] = text
                except Exception:
                    pass
        paper_info["pmc_id"] = str(pmc_id_num)
        paper_info["abstract"] = p_obj.abstract_as_str() if p_obj.abstract is not None else ""
        paper_info["has_data"] = str(p_obj.has_data) if p_obj.has_data is not None else ""
        paper_info["body"] = body_info if body_info else {}
        paper_info["title"] = p_obj.title if p_obj.title is not None else ""
        paper_info["authors"] = normalize_value(p_obj.authors) if p_obj.authors is not None else ""
        paper_info["non_author_contributors"] = normalize_value(p_obj.non_author_contributors) if p_obj.non_author_contributors is not None else ""
        paper_info["publisher_name"] = normalize_value(p_obj.publisher_name) if p_obj.publisher_name is not None else ""
        paper_info["publisher_location"] = normalize_value(p_obj.publisher_location) if p_obj.publisher_location is not None else ""
        paper_info["article_id"] = normalize_value(p_obj.article_id) if p_obj.article_id is not None else ""
        paper_info["journal_title"] = normalize_value(p_obj.journal_title) if p_obj.journal_title is not None else ""
        paper_info["journal_id"] = normalize_value(p_obj.journal_id) if p_obj.journal_id is not None else ""
        paper_info["issn"] = normalize_value(p_obj.issn) if p_obj.issn is not None else ""
        paper_info["article_types"] = normalize_value(p_obj.article_types) if p_obj.article_types is not None else ""
        paper_info["article_categories"] = normalize_value(p_obj.article_categories) if p_obj.article_categories is not None else ""
        paper_info["published_date"] = normalize_value(p_obj.published_date) if p_obj.published_date is not None else ""
        paper_info["volume"] = normalize_value(p_obj.volume) if p_obj.volume is not None else ""
        paper_info["issue"] = normalize_value(p_obj.issue) if p_obj.issue is not None else ""
        paper_info["permissions"] = normalize_value(p_obj.permissions) if p_obj.permissions is not None else ""
        paper_info["copyright"] = normalize_value(p_obj.copyright) if p_obj.copyright is not None else ""
        paper_info["license"] = normalize_value(p_obj.license) if p_obj.license is not None else ""
        paper_info["funding"] = normalize_value(p_obj.funding) if p_obj.funding is not None else ""
        paper_info["footnote"] = normalize_value(p_obj.footnote) if p_obj.footnote is not None else ""
        paper_info["acknowledgements"] = normalize_value(p_obj.acknowledgements) if p_obj.acknowledgements is not None else ""
        paper_info["notes"] = normalize_value(p_obj.notes) if p_obj.notes is not None else ""
        paper_info["custom_meta"] = normalize_value(p_obj.custom_meta) if p_obj.custom_meta is not None else ""
        paper_info["last_updated"] = normalize_value(p_obj.last_updated) if hasattr(p_obj, "last_updated") else ""
        paper_info = {k: normalize_value(v) for k, v in paper_info.items()}
        if not paper_info or not paper_info.get("body") or paper_info.get("body") == {}:
            return None
        return paper_info
    except Exception:
        return None
    finally:
        try:
            del paper_info, body_info, p_obj
        except Exception:
            pass
        gc.collect()
    return None

def process_pmc_ids_in_batches(pmc_ids: List[str], base_directory: str, batch_size: int = 16):
    def process_single_pmc_wrapper(pmc_id: str):
        info = process_single_pmc(pmc_id)
        if info:
            file_path = os.path.join(base_directory, f"PMC{pmc_id}.json")
            with open(file_path, "w", encoding="utf-8") as jf:
                json.dump(info, jf, ensure_ascii=False, indent=4, default=str)
        return pmc_id, info is not None
    total_processed = 0
    successful = 0
    failed = 0
    start_time = time.time()
    custom_bar_format = "{l_bar}{bar} | {n_fmt}/{total_fmt} [elapsed: {elapsed} | remaining: {remaining}] {postfix}"
    with tqdm(total=len(pmc_ids), desc="Processing PMC IDs", unit="paper", bar_format=custom_bar_format, dynamic_ncols=True) as pbar:
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            futures = {executor.submit(process_single_pmc_wrapper, pmc_id): pmc_id for pmc_id in pmc_ids}
            for future in as_completed(futures):
                pmc_id = futures[future]
                try:
                    _, success = future.result()
                    if success:
                        successful += 1
                    else:
                        failed += 1
                except Exception:
                    failed += 1
                total_processed += 1
                elapsed = time.time() - start_time
                avg_time = elapsed / total_processed if total_processed else 0
                pbar.set_postfix({
                    'Success': f"{successful}",
                    'Failed': f"{failed}",
                    'Success Rate': f"{(successful/total_processed)*100:.1f}%",
                    'Avg Time': f"{avg_time:.2f}s"
                })
                pbar.update(1)

def process_in_batches(pmc_ids, base_directory, chunk_size=100, parallel_workers=16):
    total_chunks = (len(pmc_ids) + chunk_size - 1) // chunk_size
    for chunk_index in range(total_chunks):
        chunk = pmc_ids[chunk_index * chunk_size : (chunk_index + 1) * chunk_size]
        print(f"\n=== Processing Batch {chunk_index+1} of {total_chunks} ===")
        print(f"Working on {len(chunk)} papers. Please wait...")
        process_pmc_ids_in_batches(chunk, base_directory, batch_size=parallel_workers)
        print(f"Batch {chunk_index+1} complete!")

def process_in_batches_with_retry(pmc_ids, base_directory, chunk_size=100, parallel_workers=16, max_retries=3):
    print("\n=== Initial Processing ===")
    print(f"Total papers to process: {len(pmc_ids)}")
    process_in_batches(pmc_ids, base_directory, chunk_size, parallel_workers)
    
    remaining_ids = set()
    for pmc_id in pmc_ids:
        file_path = os.path.join(base_directory, f"PMC{pmc_id}.json")
        if not os.path.exists(file_path):
            remaining_ids.add(pmc_id)
        else:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not data.get("body") or data.get("body") == {}:
                    remaining_ids.add(pmc_id)
            except Exception:
                remaining_ids.add(pmc_id)
    
    if not remaining_ids:
        print("\nCongratulations! All papers were processed successfully on the initial attempt!")
        return

    for attempt in range(1, max_retries + 1):
        print(f"\n*** Retry Attempt {attempt} of {max_retries} ***")
        print(f"Retrying processing for {len(remaining_ids)} paper(s) that failed or have missing content...")
        process_in_batches(list(remaining_ids), base_directory, chunk_size, parallel_workers)
        
        new_remaining = set()
        for pmc_id in remaining_ids:
            file_path = os.path.join(base_directory, f"{pmc_id}.json")
            if not os.path.exists(file_path):
                new_remaining.add(pmc_id)
            else:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if not data.get("body") or data.get("body") == {}:
                        new_remaining.add(pmc_id)
                except Exception:
                    new_remaining.add(pmc_id)
        print(f"After retry attempt {attempt}, {len(new_remaining)} paper(s) still failed or have empty content.")
        remaining_ids = new_remaining
        if not remaining_ids:
            print("\nCongratulations! All previously failed papers have now been successfully processed!")
            return

    if remaining_ids:
        print("\nUnfortunately, the following PMCID(s) could not be processed after all attempts:")
        for pmc in remaining_ids:
            print(f"  - {pmc}")
    else:
        print("\nCongratulations! All papers have been successfully processed!")
