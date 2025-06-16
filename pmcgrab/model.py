import datetime
import textwrap
import time
import warnings
from typing import Dict, List, Optional, Union

import lxml.etree as ET
import pandas as pd
from urllib.error import HTTPError

from .utils import (
    define_data_dict,
    normalize_value,
    stringify_children,
    split_text_and_refs,
    remove_mhtml_tags,
    BasicBiMap,
)
from .constants import (
    MultipleTitleWarning,
    UnhandledTextTagWarning,
    ReadHTMLFailure,
    PubmedHTTPError,
)


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
        from .parser import paper_dict_from_pmc
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

