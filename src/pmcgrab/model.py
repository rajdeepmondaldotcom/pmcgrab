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
import json
import textwrap
import warnings
from pathlib import Path

import lxml.etree as ET
import pandas as pd

from pmcgrab.common.serialization import normalize_value
from pmcgrab.common.xml_processing import (
    remove_mhtml_tags,
    split_text_and_refs,
    stringify_children,
)
from pmcgrab.constants import MultipleTitleWarning, ReadHTMLFailure
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
        # Python 3.10 compatibility: datetime.UTC was added later than 3.10.
        _utc = getattr(datetime, "UTC", datetime.timezone.utc)
        self.last_updated = datetime.datetime.now(_utc).isoformat()
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
        self.fpage = d.get("FPage")
        self.lpage = d.get("LPage")
        self.elocation_id = d.get("Elocation ID")
        # Backwards compatibility aliases
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
        self.counts = d.get("Counts")
        self.self_uri = d.get("Self URI")
        self.related_articles = d.get("Related Articles")
        self.conference = d.get("Conference")
        # Phase 5 additions
        self.subtitle = d.get("Subtitle")
        self.author_notes = d.get("Author Notes")
        self.appendices = d.get("Appendices")
        self.glossary = d.get("Glossary")
        self.translated_titles = d.get("Translated Titles")
        self.translated_abstracts = d.get("Translated Abstracts")
        self.abstract_type = d.get("Abstract Type")
        self.tex_equations = d.get("TeX Equations")
        self.version_history = d.get("Version History")
        self.ref_map = d.get("Ref Map")
        self._ref_map_with_tags = d.get("Ref Map With Tags")
        self.data_dict = define_data_dict()
        self.vector_collection = None

    # -----------------------------------------------------------------
    # Class methods (factory constructors)
    # -----------------------------------------------------------------

    @classmethod
    def from_pmc(
        cls,
        pmcid: str | int,
        *,
        email: str | None = None,
        download: bool = False,
        validate: bool = True,
        verbose: bool = False,
        suppress_warnings: bool = False,
        suppress_errors: bool = False,
    ) -> "Paper":
        """Create a Paper by downloading and parsing a PMC article.

        Convenience factory method that combines XML fetching and parsing
        into a single call.

        Args:
            pmcid: PubMed Central ID (accepts "PMC7181753", "pmc7181753", "7181753", or int)
            email: Contact email for NCBI API. If None, uses the email pool.
            download: If True, cache raw XML locally
            validate: If True, perform DTD validation
            verbose: If True, emit progress logging
            suppress_warnings: If True, suppress parsing warnings
            suppress_errors: If True, return empty Paper on errors

        Returns:
            Paper: Fully parsed Paper object

        Examples:
            >>> paper = Paper.from_pmc("7181753")
            >>> paper = Paper.from_pmc("PMC7181753", email="user@example.com")
        """
        from pmcgrab.idconvert import normalize_id
        from pmcgrab.infrastructure.settings import next_email
        from pmcgrab.parser import paper_dict_from_pmc

        # Normalize the ID
        numeric_id = pmcid if isinstance(pmcid, int) else int(normalize_id(str(pmcid)))

        if email is None:
            email = next_email()

        d = paper_dict_from_pmc(
            numeric_id,
            email=email,
            download=download,
            validate=validate,
            verbose=verbose,
            suppress_warnings=suppress_warnings,
            suppress_errors=suppress_errors,
        )
        return cls(d)

    @classmethod
    def from_local_xml(
        cls,
        xml_path: str | Path,
        *,
        verbose: bool = False,
        suppress_warnings: bool = False,
        suppress_errors: bool = False,
        strip_text_styling: bool = True,
        validate: bool = False,
    ) -> "Paper":
        """Create a Paper from a local JATS XML file.

        Args:
            xml_path: Path to a JATS XML file on disk
            verbose: If True, emit progress logging
            suppress_warnings: If True, suppress parsing warnings
            suppress_errors: If True, return empty Paper on errors
            strip_text_styling: If True, remove HTML-style formatting tags
            validate: If True, perform DTD validation

        Returns:
            Paper: Fully parsed Paper object

        Examples:
            >>> paper = Paper.from_local_xml("path/to/PMC7181753.xml")
        """
        from pmcgrab.parser import paper_dict_from_local_xml

        d = paper_dict_from_local_xml(
            str(xml_path),
            verbose=verbose,
            suppress_warnings=suppress_warnings,
            suppress_errors=suppress_errors,
            strip_text_styling=strip_text_styling,
            validate=validate,
        )
        return cls(d)

    # -----------------------------------------------------------------
    # Serialization methods
    # -----------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return the Paper as a fully normalized, JSON-serializable dictionary.

        Returns:
            dict: Dictionary with all paper fields normalized for JSON.
                  Returns ``{"has_data": False}`` if no data is available.
        """
        if not self.has_data:
            return {"has_data": False}

        d = {
            "pmc_id": str(self.pmcid) if self.pmcid else "",
            "title": self.title or "",
            "has_data": self.has_data,
            "abstract": self.abstract_as_dict(),
            "abstract_text": self.abstract_as_str(),
            "body": self.body_as_dict(),
            "toc": self.get_toc(),
            "authors": self.authors if self.authors is not None else [],
            "non_author_contributors": (
                self.non_author_contributors
                if self.non_author_contributors is not None
                and not isinstance(self.non_author_contributors, str)
                else []
            ),
            "article_id": self.article_id if self.article_id is not None else {},
            "journal_title": (
                self.journal_title if self.journal_title is not None else ""
            ),
            "journal_id": self.journal_id if self.journal_id is not None else {},
            "issn": self.issn if self.issn is not None else {},
            "publisher_name": (
                self.publisher_name if self.publisher_name is not None else ""
            ),
            "publisher_location": (
                self.publisher_location if self.publisher_location is not None else ""
            ),
            "article_types": (
                self.article_types if self.article_types is not None else []
            ),
            "article_categories": (
                self.article_categories if self.article_categories is not None else []
            ),
            "keywords": self.keywords if self.keywords is not None else [],
            "published_date": (
                self.published_date if self.published_date is not None else {}
            ),
            "history_dates": (
                self.history_dates if self.history_dates is not None else {}
            ),
            "volume": self.volume if self.volume is not None else "",
            "issue": self.issue if self.issue is not None else "",
            "fpage": self.fpage if self.fpage is not None else "",
            "lpage": self.lpage if self.lpage is not None else "",
            "permissions": self.permissions if self.permissions is not None else {},
            "copyright": self.copyright if self.copyright is not None else "",
            "license": self.license if self.license is not None else "",
            "citations": self.citations if self.citations is not None else [],
            "tables": self.tables if self.tables is not None else [],
            "figures": self.figures if self.figures is not None else [],
            "equations": self.equations if self.equations is not None else [],
            "funding": self.funding if self.funding is not None else [],
            "ethics": self.ethics if self.ethics is not None else {},
            "supplementary_material": (
                self.supplementary if self.supplementary is not None else []
            ),
            "footnote": self.footnote if self.footnote is not None else "",
            "acknowledgements": (
                self.acknowledgements if self.acknowledgements is not None else []
            ),
            "notes": self.notes if self.notes is not None else [],
            "custom_meta": self.custom_meta if self.custom_meta is not None else {},
            "elocation_id": self.elocation_id if self.elocation_id is not None else "",
            "counts": self.counts if self.counts is not None else {},
            "self_uri": self.self_uri if self.self_uri is not None else [],
            "related_articles": (
                self.related_articles if self.related_articles is not None else []
            ),
            "conference": self.conference if self.conference is not None else {},
            "version_history": getattr(self, "version_history", None) or [],
            # Phase 5 additions
            "subtitle": getattr(self, "subtitle", None) or "",
            "author_notes": getattr(self, "author_notes", None) or {},
            "appendices": getattr(self, "appendices", None) or [],
            "glossary": getattr(self, "glossary", None) or [],
            "translated_titles": getattr(self, "translated_titles", None) or [],
            "translated_abstracts": getattr(self, "translated_abstracts", None) or [],
            "abstract_type": getattr(self, "abstract_type", None) or "",
            "tex_equations": getattr(self, "tex_equations", None) or [],
            # Nested / paragraph-level body views
            "body_nested": self.body_as_nested_dict(),
            "paragraphs": self.body_as_paragraphs(),
            "full_text": self.full_text(),
            "last_updated": getattr(self, "last_updated", ""),
        }
        return {k: normalize_value(v) for k, v in d.items()}

    def to_json(self, *, indent: int = 2, ensure_ascii: bool = False) -> str:
        """Return the Paper as a JSON string.

        Args:
            indent: Number of spaces for JSON indentation (default: 2)
            ensure_ascii: If True, escape non-ASCII characters (default: False)

        Returns:
            str: JSON representation of the paper
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=ensure_ascii)

    # -----------------------------------------------------------------
    # String representations
    # -----------------------------------------------------------------

    def __repr__(self) -> str:
        """Return detailed string representation for debugging."""
        if not self.has_data:
            return "Paper(has_data=False)"
        return f"Paper(pmcid={self.pmcid!r}, title={self.title!r})"

    def __str__(self) -> str:
        """Return human-readable string representation."""
        if not self.has_data:
            return "[No Data]"
        return f"[PMC{self.pmcid}] {self.title}"

    # -----------------------------------------------------------------
    # Text access methods
    # -----------------------------------------------------------------

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

    def abstract_as_dict(self) -> dict[str, str]:
        """Return the abstract as a structured dictionary.

        Converts the structured abstract sections into a dictionary mapping
        section titles to their text content. For unstructured abstracts
        (single paragraph), uses "Abstract" as the key.

        Returns:
            dict[str, str]: Mapping of section titles to text content.
                           Empty dict if no abstract is available.
        """
        if not self.abstract:
            return {}
        result: dict[str, str] = {}
        sec_counter = 1
        for element in self.abstract:
            title = getattr(element, "title", None)
            if title:
                # Use get_clean_text to avoid "SECTION:" prefix leaking in
                clean = getattr(element, "get_clean_text", None)
                if clean:
                    result[title] = clean()
                else:
                    result[title] = str(element).strip()
            else:
                key = (
                    f"Abstract Section {sec_counter}" if sec_counter > 1 else "Abstract"
                )
                clean = getattr(element, "get_clean_text", None)
                if clean:
                    result[key] = clean()
                else:
                    result[key] = str(element).strip()
                sec_counter += 1
        return result

    def body_as_dict(self) -> dict[str, str]:
        """Return the body as a flat dictionary (section title -> clean text).

        Converts the body sections into a dictionary mapping section titles
        to their clean text content, without ``SECTION:`` formatting artifacts.
        Subsection text is merged into the parent section.  For a nested
        representation use :meth:`body_as_nested_dict`.

        Returns:
            dict[str, str]: Mapping of section titles to text content.
                           Empty dict if no body content is available.
        """
        if not self.body:
            return {}
        result: dict[str, str] = {}
        sec_counter = 1
        for element in self.body:
            title = getattr(element, "title", None)
            if title:
                clean = getattr(element, "get_clean_text", None)
                if clean:
                    result[title] = clean()
                else:
                    result[title] = str(element).strip()
            else:
                key = f"Section {sec_counter}"
                clean = getattr(element, "get_clean_text", None)
                if clean:
                    result[key] = clean()
                else:
                    result[key] = str(element).strip()
                sec_counter += 1
        return result

    # ------------------------------------------------------------------
    # Nested / paragraph-level output helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _section_to_nested(section: "TextSection") -> dict:
        """Recursively convert a TextSection into a nested dict.

        Returns a dict whose keys are subsection titles (with their own
        nested dicts as values) plus a ``"_text"`` key holding any direct
        paragraph text belonging to this section.
        """
        direct_paragraphs: list[str] = []
        result: dict = {}
        for child in section.children:
            if isinstance(child, TextSection):
                child_title = child.title or "Untitled"
                result[child_title] = Paper._section_to_nested(child)
            else:
                text = str(child).strip()
                if text:
                    direct_paragraphs.append(text)
        if direct_paragraphs:
            result["_text"] = "\n".join(direct_paragraphs)
        return result

    def body_as_nested_dict(self) -> dict:
        """Return the body as a deeply-nested dictionary preserving hierarchy.

        Unlike :meth:`body_as_dict` which flattens subsections into their
        parent, this method produces a recursive dict::

            {
              "Introduction": {"_text": "..."},
              "Methods": {
                "_text": "...",
                "Study Design": {"_text": "...", "Participants": {"_text": "..."}},
                "Statistical Analysis": {"_text": "..."},
              },
            }

        The ``"_text"`` key holds direct paragraph content for a given
        section.  Subsection titles become additional keys with their own
        nested dicts.

        Returns:
            dict: Nested dictionary mirroring the original section hierarchy.
        """
        if not self.body:
            return {}
        result: dict = {}
        sec_counter = 1
        for element in self.body:
            if isinstance(element, TextSection):
                title = element.title or f"Section {sec_counter}"
                result[title] = Paper._section_to_nested(element)
                if not element.title:
                    sec_counter += 1
            else:
                # Top-level paragraph outside any section
                key = f"Section {sec_counter}"
                text = str(element).strip()
                if text:
                    existing = result.get(key, {})
                    prev = existing.get("_text", "")
                    existing["_text"] = (prev + "\n" + text).strip()
                    result[key] = existing
                sec_counter += 1
        return result

    def body_as_paragraphs(self) -> list[dict[str, str | int | None]]:
        """Return every paragraph in the body with section context.

        Produces a flat list of paragraph dicts ideal for RAG chunking,
        embedding, and sentence-level analysis::

            [
              {"section": "Introduction", "subsection": None,
               "paragraph_index": 0, "text": "..."},
              {"section": "Methods", "subsection": "Study Design",
               "paragraph_index": 0, "text": "..."},
            ]

        Returns:
            list[dict]: One entry per paragraph with section ancestry.
        """
        if not self.body:
            return []
        paragraphs: list[dict[str, str | int | None]] = []
        self._collect_paragraphs(self.body, None, None, paragraphs)
        return paragraphs

    @staticmethod
    def _collect_paragraphs(
        elements: list,
        section_title: str | None,
        subsection_title: str | None,
        out: list[dict[str, str | int | None]],
    ) -> None:
        """Recursively collect paragraphs from a list of text elements."""
        para_idx = 0
        for element in elements:
            if isinstance(element, TextSection):
                # Determine nesting level
                if section_title is None:
                    Paper._collect_paragraphs(
                        element.children, element.title, None, out
                    )
                else:
                    Paper._collect_paragraphs(
                        element.children, section_title, element.title, out
                    )
            elif isinstance(element, TextParagraph):
                text = str(element).strip()
                if text:
                    out.append(
                        {
                            "section": section_title,
                            "subsection": subsection_title,
                            "paragraph_index": para_idx,
                            "text": text,
                        }
                    )
                    para_idx += 1
            else:
                # TextTable, TextFigure, etc. -- render to text
                text = str(element).strip()
                if text:
                    out.append(
                        {
                            "section": section_title,
                            "subsection": subsection_title,
                            "paragraph_index": para_idx,
                            "text": text,
                        }
                    )
                    para_idx += 1

    def full_text(self) -> str:
        """Return the entire article as a single continuous string.

        Concatenates the abstract and body into one string with simple
        section markers.  Ideal for full-text embedding, indexing, and
        search.

        Returns:
            str: Complete article text (abstract + body).
        """
        parts: list[str] = []
        if self.abstract:
            parts.append(self.abstract_as_str())
        if self.body:
            for element in self.body:
                title = getattr(element, "title", None)
                clean = getattr(element, "get_clean_text", None)
                if title:
                    parts.append(f"\n{title}\n")
                if clean:
                    parts.append(clean())
                else:
                    parts.append(str(element).strip())
        return "\n".join(parts).strip()

    def get_toc(self) -> list[str]:
        """Return a table of contents as a flat list of section titles.

        Returns:
            list[str]: List of section titles from the body.
        """
        if not self.body:
            return []
        toc: list[str] = []
        for element in self.body:
            title = getattr(element, "title", None)
            if title:
                toc.append(title)
        return toc


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


def _render_block_element(elem: ET.Element) -> str:
    """Render a JATS block-level element into readable plain text.

    Handles ``<list>``, ``<def-list>``, ``<disp-formula>``,
    ``<disp-quote>``, ``<boxed-text>``, ``<preformat>``, ``<code>``,
    ``<verse-group>``, ``<speech>``, ``<statement>``, and other block
    elements by converting them into a readable string representation.
    """
    tag = elem.tag

    if tag == "list":
        items: list[str] = []
        list_type = elem.get("list-type", "bullet")
        for idx, item in enumerate(elem.findall("list-item"), 1):
            text = " ".join(item.itertext()).strip()
            if list_type in (
                "order",
                "alpha-lower",
                "alpha-upper",
                "roman-lower",
                "roman-upper",
            ):
                items.append(f"{idx}. {text}")
            else:
                items.append(f"- {text}")
        return "\n".join(items)

    if tag == "def-list":
        parts: list[str] = []
        for def_item in elem.findall("def-item"):
            term_el = def_item.find("term")
            def_el = def_item.find("def")
            term = "".join(term_el.itertext()).strip() if term_el is not None else ""
            defn = "".join(def_el.itertext()).strip() if def_el is not None else ""
            parts.append(f"{term}: {defn}")
        return "\n".join(parts)

    if tag in ("disp-formula", "inline-formula"):
        # Prefer <tex-math>, fall back to <mml:math>, then itertext
        tex = elem.find("tex-math")
        if tex is not None and tex.text:
            return tex.text.strip()
        mml = elem.find("{http://www.w3.org/1998/Math/MathML}math")
        if mml is not None:
            return ET.tostring(mml, encoding="unicode")
        alt = elem.find("alternatives")
        if alt is not None:
            tex2 = alt.find("tex-math")
            if tex2 is not None and tex2.text:
                return tex2.text.strip()
        return "".join(elem.itertext()).strip()

    if tag == "disp-quote":
        text = "".join(elem.itertext()).strip()
        return f'"{text}"'

    if tag == "boxed-text":
        title_el = elem.find("caption/title")
        title = "".join(title_el.itertext()).strip() if title_el is not None else ""
        body_parts = []
        for p in elem.findall(".//p"):
            body_parts.append("".join(p.itertext()).strip())
        body = "\n".join(body_parts)
        if title:
            return f"[{title}] {body}"
        return body

    if tag in ("preformat", "code"):
        return "".join(elem.itertext()).strip()

    if tag == "verse-group":
        lines: list[str] = []
        for vl in elem.findall("verse-line"):
            lines.append("".join(vl.itertext()).strip())
        return "\n".join(lines)

    if tag == "speech":
        speaker_el = elem.find("speaker")
        speaker = (
            "".join(speaker_el.itertext()).strip() if speaker_el is not None else ""
        )
        speech_parts = []
        for p in elem.findall("p"):
            speech_parts.append("".join(p.itertext()).strip())
        return (
            f"{speaker}: " + " ".join(speech_parts)
            if speaker
            else " ".join(speech_parts)
        )

    if tag == "statement":
        title_el = elem.find("title")
        title = "".join(title_el.itertext()).strip() if title_el is not None else ""
        body_text = "".join(elem.itertext()).strip()
        if title and body_text.startswith(title):
            return body_text
        return f"{title} {body_text}".strip()

    # Generic fallback: join all text content
    return "".join(elem.itertext()).strip()


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

        # Tags handled by converting their full text content into a
        # synthetic TextParagraph so that the content is never lost.
        _BLOCK_AS_PARAGRAPH_TAGS = frozenset(
            {
                "list",
                "def-list",
                "disp-formula",
                "disp-quote",
                "boxed-text",
                "preformat",
                "code",
                "verse-group",
                "speech",
                "statement",
                "supplementary-material",
                "table-wrap-group",
                "alternatives",
                "app",
                "glossary",
                "fn-group",
                "ref-list",
            }
        )
        # Tags that are purely structural / metadata and can be silently
        # skipped without losing body text.
        _SKIP_TAGS = frozenset(
            {
                "label",
                "caption",
                "object-id",
                "target",
            }
        )

        for child in sec_root:
            if child.tag == "title":
                if self.title:
                    warnings.warn(
                        "Multiple titles found; using the first.",
                        MultipleTitleWarning,
                        stacklevel=2,
                    )
                    continue
                self.title = "".join(child.itertext()).strip() or None
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
            elif child.tag in _BLOCK_AS_PARAGRAPH_TAGS:
                # Render the entire block element as text so content is
                # never silently dropped.  We create a synthetic <p>
                # wrapper so it flows through the normal TextParagraph
                # pipeline including reference extraction.
                synth = ET.SubElement(ET.Element("_root"), "p")
                synth.text = _render_block_element(child)
                if synth.text and synth.text.strip():
                    self.children.append(
                        TextParagraph(synth, parent=self, ref_map=self.get_ref_map())
                    )
            elif child.tag in _SKIP_TAGS:
                pass  # structural metadata, not body text
            else:
                # Last resort: extract any text content so nothing is lost
                fallback_text = "".join(child.itertext()).strip()
                if fallback_text:
                    synth = ET.SubElement(ET.Element("_root"), "p")
                    synth.text = fallback_text
                    self.children.append(
                        TextParagraph(synth, parent=self, ref_map=self.get_ref_map())
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

    def get_clean_text(self) -> str:
        """Return clean body text without 'SECTION:' prefixes or indentation.

        Unlike ``__str__`` which is for human display, this method returns
        text suitable for machine consumption: no ``SECTION:`` labels, no
        indentation artifacts, just paragraph content separated by newlines.

        Returns:
            str: Clean text content of this section and all nested children.
        """
        parts: list[str] = []
        for child in self.children:
            if isinstance(child, TextSection):
                parts.append(child.get_clean_text())
            else:
                text = str(child).strip()
                if text:
                    parts.append(text)
        return "\n".join(parts)

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
        label_parts = table_root.xpath("label/text()")
        caption_parts = table_root.xpath("caption/p/text()")
        self.table_id: str | None = table_root.get("id")
        self.label: str | None = label_parts[0] if label_parts else None
        self.caption: str | None = caption_parts[0] if caption_parts else None
        self.df: pd.io.formats.style.Styler | None = None

        # --- Structured representation (always populated if possible) ---
        self.table_dict: dict | None = None

        # --- Footnotes ---
        footnotes: list[str] = []
        for fn in table_root.xpath(".//table-wrap-foot//fn"):
            fn_text = "".join(fn.itertext()).strip()
            if fn_text:
                footnotes.append(fn_text)
        self.footnotes: list[str] = footnotes

        # pandas.read_html expects a string / file-like / URL. Passing raw bytes
        # can be interpreted as a filesystem path on newer pandas versions.
        table_xml_str = ET.tostring(table_root, encoding="unicode")

        # --- Attempt 1: pandas read_html ---
        try:
            tables = pd.read_html(table_xml_str)
            if tables:
                table_df = tables[0]
                title = (
                    f"{self.label}: {self.caption}"
                    if self.label and self.caption
                    else (self.label or self.caption)
                )
                if title:
                    table_df = table_df.style.set_caption(title)
                self.df = table_df
                # Build structured dict from pandas result
                raw_df = tables[0]
                self.table_dict = {
                    "id": self.table_id,
                    "label": self.label,
                    "caption": self.caption,
                    "columns": list(raw_df.columns),
                    "rows": raw_df.values.tolist(),
                    "footnotes": self.footnotes,
                }
        except (ValueError, AttributeError) as e:
            warnings.warn(
                f"Table parsing failed (label: {self.label}, caption: {self.caption}): {e}",
                ReadHTMLFailure,
                stacklevel=2,
            )

        # --- Attempt 2: lxml native fallback ---
        if self.table_dict is None:
            try:
                columns: list[str] = []
                rows: list[list[str]] = []
                # Find the actual <table> element
                table_el = table_root.find(".//table")
                if table_el is not None:
                    # Headers
                    for thead in table_el.findall(".//thead"):
                        for tr in thead.findall("tr"):
                            for th in tr.findall("th"):
                                columns.append("".join(th.itertext()).strip())
                    # Body rows
                    for tbody_or_table in table_el.findall(".//tbody") or [table_el]:
                        for tr in tbody_or_table.findall("tr"):
                            row: list[str] = []
                            for cell in tr:
                                if cell.tag in ("td", "th"):
                                    row.append("".join(cell.itertext()).strip())
                            if row:
                                rows.append(row)
                    if columns or rows:
                        self.table_dict = {
                            "id": self.table_id,
                            "label": self.label,
                            "caption": self.caption,
                            "columns": columns,
                            "rows": rows,
                            "footnotes": self.footnotes,
                        }
            except Exception:
                pass  # graceful fallback exhausted

    def __str__(self) -> str:
        """Return string representation of the parsed table.

        Returns:
            str: Formatted table string from pandas or structured text
        """
        if self.df is not None:
            return str(self.df)
        if self.table_dict and self.table_dict.get("rows"):
            header = (
                f"{self.label}: {self.caption}"
                if self.label
                else (self.caption or "Table")
            )
            return f"[{header}] ({len(self.table_dict['rows'])} rows)"
        return "Table could not be parsed"

    def __repr__(self) -> str:
        """Return detailed representation of the parsed table.

        Returns:
            str: Detailed table representation
        """
        return repr(self.df) if self.df is not None else repr(self.table_dict)
