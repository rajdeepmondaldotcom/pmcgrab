import datetime
import textwrap
import warnings
from typing import Optional, Union

import lxml.etree as ET
import pandas as pd

from pmcgrab.constants import (
    MultipleTitleWarning,
    ReadHTMLFailure,
    UnhandledTextTagWarning,
)
from pmcgrab.figure import TextFigure
from pmcgrab.common.serialization import normalize_value
from pmcgrab.common.xml_processing import (
    remove_mhtml_tags,
    split_text_and_refs,
    stringify_children,
)
from pmcgrab.domain.value_objects import BasicBiMap
from pmcgrab.utils import define_data_dict


class Paper:
    """Container for all parsed information about a PMC article."""

    __tablename__ = "Papers"

    def __init__(self, d: dict) -> None:
        """Initialize a ``Paper`` from a dictionary of parsed values."""
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
        self.keywords = d.get("Keywords")
        self.published_date = d.get("Published Date")
        self.history_dates = d.get("History Dates")
        self.volume = d.get("Volume")
        self.issue = d.get("Issue")
        # Accept both shorthand and full keys for page numbers
        self.fpage = d.get("FPage", d.get("First Page"))
        self.lpage = d.get("LPage", d.get("Last Page"))
        self.citations = d.get("Citations")
        self.tables = d.get("Tables")
        self.figures = d.get("Figures")
        self.permissions = d.get("Permissions")
        if self.permissions:
            self.copyright = self.permissions.get("Copyright Statement")
            self.license = self.permissions.get("License Type")
        else:
            self.copyright = None
            self.license = None
        self.funding = d.get("Funding")
        self.ethics = d.get("Ethics")
        self.supplementary = d.get("Supplementary Material")
        self.equations = d.get("Equations")
        self.footnote = d.get("Footnote")
        self.acknowledgements = d.get("Acknowledgements")
        self.notes = d.get("Notes")
        self.custom_meta = d.get("Custom Meta")
        self.ref_map = d.get("Ref Map")
        self._ref_map_with_tags = d.get("Ref Map With Tags")
        self.data_dict = define_data_dict()
        self.vector_collection = None

    def abstract_as_str(self) -> str:
        """Return the abstract as plain text."""
        return "\n".join(str(sec) for sec in self.abstract) if self.abstract else ""


class TextElement:
    """Base class for text elements that reference a shared ``BasicBiMap``."""

    def __init__(
        self,
        root: ET.Element,
        parent: Optional["TextElement"] = None,
        ref_map: Optional[BasicBiMap] = None,
    ) -> None:
        self.root = root
        self.parent = parent
        self.ref_map = ref_map if ref_map is not None else BasicBiMap()

    def get_ref_map(self) -> BasicBiMap:
        """Return the ``BasicBiMap`` associated with this element."""
        return self.parent.get_ref_map() if self.parent else self.ref_map

    def set_ref_map(self, ref_map: BasicBiMap) -> None:
        """Propagate ``ref_map`` to this element or its root parent."""
        if self.parent:
            self.parent.set_ref_map(ref_map)
        else:
            self.ref_map = ref_map


class TextParagraph(TextElement):
    """Paragraph of text possibly containing references."""

    def __init__(
        self,
        p_root: ET.Element,
        parent: Optional[TextElement] = None,
        ref_map: Optional[BasicBiMap] = None,
    ) -> None:
        super().__init__(p_root, parent, ref_map)
        self.id = p_root.get("id")
        p_subtree = stringify_children(self.root)
        self.text_with_refs = split_text_and_refs(
            p_subtree, self.get_ref_map(), element_id=self.id, on_unknown="keep"
        )
        self.text = remove_mhtml_tags(self.text_with_refs)

    def __str__(self) -> str:
        """Return paragraph text without reference tags."""
        return self.text

    def __eq__(self, other: object) -> bool:
        """Equality based on underlying text with references."""
        return (
            isinstance(other, TextParagraph)
            and self.text_with_refs == other.text_with_refs
        )


class TextSection(TextElement):
    """Hierarchical section of text that can contain nested sections."""

    def __init__(
        self,
        sec_root: ET.Element,
        parent: Optional[TextElement] = None,
        ref_map: Optional[BasicBiMap] = None,
    ) -> None:
        super().__init__(sec_root, parent, ref_map)
        self.title: Optional[str] = None
        self.children: list[Union[TextSection, TextParagraph, TextTable]] = []
        for child in sec_root:
            if child.tag == "title":
                if self.title:
                    warnings.warn(
                        "Multiple titles found; using the first.",
                        MultipleTitleWarning,
                        stacklevel=2,
                    )
                    continue
                self.title = child.text
            elif child.tag == "sec":
                self.children.append(
                    TextSection(child, parent=self, ref_map=self.get_ref_map())
                )
            elif child.tag == "p":
                self.children.append(
                    TextParagraph(child, parent=self, ref_map=self.get_ref_map())
                )
            elif child.tag == "table-wrap":
                self.children.append(
                    TextTable(child, parent=self, ref_map=self.get_ref_map())
                )
            elif child.tag == "fig":
                self.children.append(
                    TextFigure(child, parent=self, ref_map=self.get_ref_map())
                )
            else:
                warnings.warn(
                    f"Unexpected tag {child.tag} in section.",
                    UnhandledTextTagWarning,
                    stacklevel=2,
                )
        self.text = self.get_section_text()
        self.text_with_refs = self.get_section_text_with_refs()

    def __str__(self) -> str:
        """Return a human-readable representation of the section."""
        res = f"SECTION: {self.title}:\n" if self.title else ""
        for child in self.children:
            res += "\n" + textwrap.indent(str(child), " " * 4) + "\n"
        return res

    def get_section_text(self) -> str:
        """Return text for this section without reference markers."""
        return str(self)

    def get_section_text_with_refs(self) -> str:
        """Return text for this section including reference markers."""
        res = f"SECTION: {self.title}:\n" if self.title else ""
        for child in self.children:
            if isinstance(child, TextSection):
                res += (
                    "\n"
                    + textwrap.indent(child.get_section_text_with_refs(), " " * 4)
                    + "\n"
                )
            elif isinstance(child, TextParagraph):
                res += "\n" + child.text_with_refs + "\n"
            elif isinstance(child, TextFigure):
                res += "\n" + str(child) + "\n"
        return res

    def __eq__(self, other: object) -> bool:
        """Sections are equal if titles and children match."""
        return (
            isinstance(other, TextSection)
            and self.title == other.title
            and self.children == other.children
        )


class TextTable(TextElement):
    """Wrapper for a table element and any parsed ``pandas`` representation."""

    def __init__(
        self,
        table_root: ET.Element,
        parent: Optional[TextElement] = None,
        ref_map: Optional[BasicBiMap] = None,
    ) -> None:
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
                title = (
                    f"{label}: {caption}" if label and caption else (label or caption)
                )
                if title:
                    table_df = table_df.style.set_caption(title)
                self.df = table_df
        except (ValueError, AttributeError) as e:
            warnings.warn(
                f"Table parsing failed (label: {label}, caption: {caption}): {e}",
                ReadHTMLFailure,
                stacklevel=2,
            )

    def __str__(self) -> str:
        """Return a string representation of the parsed table."""
        return str(self.df) if self.df is not None else "Table could not be parsed"

    def __repr__(self) -> str:
        """Return the ``repr`` of the parsed table."""
        return repr(self.df) if self.df is not None else "Table could not be parsed"
