"""Core data model classes for PMC article representation.

This module defines the primary data structures used to represent parsed
PubMed Central articles. The main classes provide hierarchical text
representation with support for cross-references, tables, figures, and
metadata preservation.

Classes:
    Paper: Main container for all parsed PMC article information
    TextElement: Base class for text elements with reference mapping
    TextParagraph: Individual paragraph with reference handling
    TextSection: Hierarchical section containing nested content
    TextTable: Table wrapper with pandas DataFrame representation

The design emphasizes preservation of document structure while providing
convenient access methods for AI/ML applications that need clean text
extraction alongside metadata.
"""

import datetime
import textwrap
import warnings

import lxml.etree as ET
import pandas as pd

from pmcgrab.common.serialization import normalize_value
from pmcgrab.common.xml_processing import (
    remove_mhtml_tags,
    split_text_and_refs,
    stringify_children,
)
from pmcgrab.constants import (
    MultipleTitleWarning,
    ReadHTMLFailure,
    UnhandledTextTagWarning,
)
from pmcgrab.domain.value_objects import BasicBiMap
from pmcgrab.figure import TextFigure
from pmcgrab.utils import define_data_dict


class Paper:
    """Comprehensive container for all parsed information about a PMC article.

    This class serves as the primary data model for representing a complete
    PubMed Central article with all its metadata, content sections, references,
    tables, figures, and other scholarly article components. It provides
    convenient access to both structured data and human-readable text.

    The Paper class is designed to be AI/ML-friendly, offering clean text
    extraction methods alongside preservation of document structure and
    cross-references. All data is normalized for JSON serialization and
    downstream processing.

    Attributes:
        has_data (bool): Whether the paper contains valid parsed data
        last_updated (str): Timestamp of when the paper was parsed
        pmcid (str): PubMed Central ID
        title (str): Article title
        authors (pd.DataFrame): Author information including names, emails, affiliations
        non_author_contributors (pd.DataFrame): Non-author contributors
        abstract (list[TextSection]): Structured abstract sections
        body (list[TextSection]): Main article body sections
        journal_id (dict): Journal identifier mappings
        journal_title (str): Full journal title
        issn (dict): ISSN mappings by type
        publisher_name (str): Publisher name
        publisher_location (str): Publisher location
        article_id (dict): Article ID mappings by type
        article_types (list): Article type classifications
        article_categories (list): Article category classifications
        keywords (list): Article keywords/subject terms
        published_date (dict): Publication dates by type
        history_dates (dict): Manuscript history dates
        volume (str): Journal volume number
        issue (str): Journal issue number
        fpage (str): First page number
        lpage (str): Last page number
        first_page (str): Alias for fpage
        last_page (str): Alias for lpage
        citations (list): Parsed citation entries
        tables (list[pd.DataFrame]): Parsed table data
        figures (list[dict]): Figure metadata and captions
        permissions (dict): Copyright and licensing information
        copyright (str): Copyright statement
        license (str): License type
        funding (list): Funding source information
        ethics (dict): Ethics and disclosure statements
        supplementary (list): Supplementary material metadata
        equations (list): Mathematical equations in MathML
        footnote (str): Article footnotes
        acknowledgements (list): Acknowledgement statements
        notes (list): Additional notes
        custom_meta (dict): Custom metadata key-value pairs
        ref_map (BasicBiMap): Reference mapping for cross-references
        _ref_map_with_tags (BasicBiMap): Internal reference map with XML tags
        data_dict (dict): Field documentation dictionary
        vector_collection: Optional vector collection for embeddings

    Examples:
        Create a Paper from a PMCID:

            >>> paper = Paper.from_pmc("7181753", email="your-email@example.com")
            >>> print(paper.title)
            >>> print(paper.abstract_as_str()[:200])

        Access specific sections:

            >>> for section in paper.body:
            ...     if section.title == "Methods":
            ...         print(section.get_section_text())

        Get author information:

            >>> print(paper.authors.head())
            >>> print(f"Number of authors: {len(paper.authors)}")
    """

    __tablename__ = "Papers"

    def __init__(self, d: dict) -> None:
        """Initialize a Paper from a dictionary of parsed article data.

        Args:
            d: Dictionary containing parsed article data from PMC XML.
               Should contain keys like 'PMCID', 'Title', 'Authors', 'Body', etc.
               If empty dict is provided, creates a Paper with has_data=False.

        Note:
            The dictionary structure should match the output of
            parser.build_complete_paper_dict() for proper initialization.
        """
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
        # Backwards compatibility aliases expected by legacy tests
        self.first_page = self.fpage
        self.last_page = self.lpage
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
        """Return the abstract as plain text string.

        Converts the structured abstract sections into a single readable
        text string by concatenating all section content with newlines.
        This is useful for applications that need simple text representation
        rather than the structured section hierarchy.

        Returns:
            str: Complete abstract text with sections separated by newlines.
                 Returns empty string if no abstract is available.

        Examples:
            >>> paper = Paper.from_pmc("7181753", email="your-email@example.com")
            >>> abstract_text = paper.abstract_as_str()
            >>> print(f"Abstract length: {len(abstract_text)} characters")
            >>> print(abstract_text[:200] + "...")
        """
        return "\n".join(str(sec) for sec in self.abstract) if self.abstract else ""


class TextElement:
    """Base class for hierarchical text elements with cross-reference support.

    This abstract base class provides common functionality for text elements
    that need to maintain and access cross-reference mappings. It implements
    a parent-child hierarchy where reference maps can be inherited from
    parent elements, ensuring consistent cross-reference resolution throughout
    the document structure.

    Attributes:
        root (ET.Element): The XML element this text element wraps
        parent (Optional[TextElement]): Parent element in the hierarchy
        ref_map (BasicBiMap): Bidirectional reference mapping for cross-references

    The reference map enables linking between text references (like citations,
    tables, figures) and their actual definitions elsewhere in the document.
    """

    def __init__(
        self,
        root: ET.Element,
        parent: "TextElement | None" = None,
        ref_map: BasicBiMap | None = None,
    ) -> None:
        """Initialize a text element with XML root and optional parent/reference map.

        Args:
            root: The XML element that this text element represents
            parent: Parent element in the document hierarchy (for reference inheritance)
            ref_map: Bidirectional reference map for cross-reference resolution.
                    If None, creates a new empty BasicBiMap.
        """
        self.root = root
        self.parent = parent
        self.ref_map = ref_map if ref_map is not None else BasicBiMap()

    def get_ref_map(self) -> BasicBiMap:
        """Get the reference map, inheriting from parent if available.

        Returns:
            BasicBiMap: The reference map associated with this element or its
                       root parent. Enables consistent cross-reference resolution
                       throughout the document hierarchy.
        """
        return self.parent.get_ref_map() if self.parent else self.ref_map

    def set_ref_map(self, ref_map: BasicBiMap) -> None:
        """Set the reference map, propagating to root parent if present.

        Args:
            ref_map: New reference map to associate with this element tree.
                    Will be set on the root parent if hierarchy exists, otherwise
                    set directly on this element.
        """
        if self.parent:
            self.parent.set_ref_map(ref_map)
        else:
            self.ref_map = ref_map


class TextParagraph(TextElement):
    """Individual paragraph of text with cross-reference and citation support.

    Represents a single paragraph from a PMC article, handling both plain text
    content and embedded cross-references to citations, tables, figures, etc.
    The paragraph maintains both clean text (with references removed) and
    text with reference markers for different use cases.

    Attributes:
        id (str): XML ID attribute of the paragraph element
        text_with_refs (str): Paragraph text with reference markers preserved
        text (str): Clean paragraph text with HTML/reference tags removed

    Examples:
        >>> # Paragraph text without reference markers (clean for AI/ML)
        >>> clean_text = paragraph.text
        >>>
        >>> # Paragraph text with reference markers (for citation tracking)
        >>> text_with_refs = paragraph.text_with_refs
        >>>
        >>> # String representation returns clean text
        >>> print(str(paragraph))
    """

    def __init__(
        self,
        p_root: ET.Element,
        parent: TextElement | None = None,
        ref_map: BasicBiMap | None = None,
    ) -> None:
        """Initialize paragraph from XML element.

        Args:
            p_root: XML paragraph element (<p>)
            parent: Parent text element for reference map inheritance
            ref_map: Reference map for cross-reference resolution
        """
        super().__init__(p_root, parent, ref_map)
        self.id = p_root.get("id")
        p_subtree = stringify_children(self.root)
        self.text_with_refs = split_text_and_refs(
            p_subtree, self.get_ref_map(), element_id=self.id, on_unknown="keep"
        )
        self.text = remove_mhtml_tags(self.text_with_refs)

    def __str__(self) -> str:
        """Return clean paragraph text without reference tags.

        Returns:
            str: Paragraph text with HTML tags and reference markers removed,
                 suitable for display or AI/ML processing.
        """
        return self.text

    def __eq__(self, other: object) -> bool:
        """Check equality based on text content with references.

        Args:
            other: Object to compare against

        Returns:
            bool: True if other is a TextParagraph with identical text_with_refs
        """
        return (
            isinstance(other, TextParagraph)
            and self.text_with_refs == other.text_with_refs
        )


class TextSection(TextElement):
    """Hierarchical document section that can contain nested sections and content.

    Represents a logical section of a PMC article (like Introduction, Methods,
    Results, Discussion, etc.) that can contain paragraphs, tables, figures,
    and nested subsections. Maintains both the hierarchical structure and
    provides flattened text access for different use cases.

    Attributes:
        title (Optional[str]): Section title/heading
        children (list): Child elements including subsections, paragraphs, tables, figures
        text (str): Complete section text with clean formatting
        text_with_refs (str): Complete section text with reference markers preserved

    The section automatically parses its XML structure to build the hierarchy,
    handling various content types and providing both structured access and
    flattened text representations.

    Examples:
        >>> # Access section title and content
        >>> print(f"Section: {section.title}")
        >>> print(section.text[:200])
        >>>
        >>> # Iterate through child elements
        >>> for child in section.children:
        ...     if isinstance(child, TextParagraph):
        ...         print(f"Paragraph: {child.text[:100]}")
        ...     elif isinstance(child, TextSection):
        ...         print(f"Subsection: {child.title}")
    """

    def __init__(
        self,
        sec_root: ET.Element,
        parent: TextElement | None = None,
        ref_map: BasicBiMap | None = None,
    ) -> None:
        """Initialize section from XML element.

        Parses the XML section element to extract title, child sections,
        paragraphs, tables, and figures. Builds a hierarchical structure
        while maintaining reference map consistency.

        Args:
            sec_root: XML section element (<sec>)
            parent: Parent text element for reference map inheritance
            ref_map: Reference map for cross-reference resolution

        Warns:
            MultipleTitleWarning: If section contains multiple <title> elements
            UnhandledTextTagWarning: If section contains unrecognized child elements
        """
        super().__init__(sec_root, parent, ref_map)
        self.title: str | None = None
        self.children: list[TextSection | TextParagraph | TextTable] = []
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
        """Return human-readable representation of the section.

        Creates a formatted string showing the section title and all child
        content with proper indentation to reflect the hierarchical structure.

        Returns:
            str: Formatted section text with title header and indented children
        """
        res = f"SECTION: {self.title}:\n" if self.title else ""
        for child in self.children:
            res += "\n" + textwrap.indent(str(child), " " * 4) + "\n"
        return res

    def get_section_text(self) -> str:
        """Return clean text for this section without reference markers.

        Returns:
            str: Complete section text with HTML tags and reference markers
                 removed, suitable for display or AI/ML processing.
        """
        return str(self)

    def get_section_text_with_refs(self) -> str:
        """Return section text including cross-reference markers.

        Preserves reference markers for applications that need to track
        citations, table references, figure references, etc.

        Returns:
            str: Complete section text with reference markers preserved
                 for citation and cross-reference tracking.
        """
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
        """Check equality based on title and child content.

        Args:
            other: Object to compare against

        Returns:
            bool: True if other is a TextSection with identical title and children
        """
        return (
            isinstance(other, TextSection)
            and self.title == other.title
            and self.children == other.children
        )


class TextTable(TextElement):
    """Table element with pandas DataFrame representation and metadata.

    Wraps a PMC table element and attempts to parse it into a structured
    pandas DataFrame for data analysis and manipulation. Preserves table
    labels, captions, and provides both structured data access and text
    representations.

    Attributes:
        df (Optional[pd.io.formats.style.Styler]): Parsed table as styled DataFrame,
                                                   None if parsing failed

    The table parser uses pandas' read_html() function to extract tabular data
    from the XML representation, automatically handling common table structures
    and formatting.

    Examples:
        >>> # Access parsed table data
        >>> if table.df is not None:
        ...     data = table.df.data  # Get underlying DataFrame
        ...     print(f"Table shape: {data.shape}")
        ...     print(data.head())
        >>>
        >>> # Get text representation
        >>> print(str(table))
    """

    def __init__(
        self,
        table_root: ET.Element,
        parent: TextElement | None = None,
        ref_map: BasicBiMap | None = None,
    ) -> None:
        """Initialize table from XML element with pandas parsing.

        Attempts to parse the table XML into a pandas DataFrame using
        pd.read_html(). Extracts label and caption information and
        applies them as table styling.

        Args:
            table_root: XML table-wrap element containing the table
            parent: Parent text element for reference map inheritance
            ref_map: Reference map for cross-reference resolution

        Warns:
            ReadHTMLFailure: If table parsing fails due to malformed HTML/XML
                           or unsupported table structure
        """
        super().__init__(table_root, parent, ref_map)
        label = table_root.xpath("label/text()")
        caption = table_root.xpath("caption/p/text()")
        label = label[0] if label else None
        caption = caption[0] if caption else None
        self.df: pd.io.formats.style.Styler | None = None
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
        """Return string representation of the parsed table.

        Returns:
            str: Formatted table string from pandas or error message if parsing failed
        """
        return str(self.df) if self.df is not None else "Table could not be parsed"

    def __repr__(self) -> str:
        """Return detailed representation of the parsed table.

        Returns:
            str: Detailed table representation from pandas or error message if parsing failed
        """
        return repr(self.df) if self.df is not None else "Table could not be parsed"
