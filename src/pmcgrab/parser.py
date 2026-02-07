from __future__ import annotations

"""
pmcgrab.parser
==============

Top-level orchestrator for transforming a PMC (PubMed Central) `article`
XML document into a rich, *ready-to-serialize* Python dictionary.
The actual heavy-lifting—walking through the XML tree and extracting
individual bits of information—is delegated to a set of specialised
helpers that reside in the `pmcgrab.application.parsing` sub-package.
This module’s primary job is to glue those helpers together and present
a **simple, cohesive API** to users.

The public API is intentionally compact:

• `paper_dict_from_pmc` – one-shot convenience helper that
  1) downloads an article’s XML (with optional validation),
  2) feeds it into the parser, and
  3) returns a plain `dict` capturing metadata, sections, references,
     tables, figures, etc.

• `generate_paper_dict` – same as above but accepts an *already
  obtained* XML root element, giving callers more control over I/O.

• `build_complete_paper_dict` – low-level entry point that coordinates
  all the `gather_*` helper functions and assembles their outputs.

In addition, the module re-exports a collection of `gather_*`
functions (title, authors, abstract, body, journal info …) so that
callers do not need to remember the exact sub-module where each helper
lives.  They can simply do:

    from pmcgrab import parser
    title = parser.gather_title(xml_root)

Design Notes
------------
• Warnings vs. Errors:
  Parsing biomedical articles can be messy.  Callers are therefore
  offered fine-grained control via `suppress_warnings` and
  `suppress_errors` flags.

• Reference Resolution:
  Internal cross-references (e.g. citations, tables, figures) are
  first collected into a `BasicBiMap` to allow O(1) lookup in both
  *forward* and *reverse* directions, and then resolved to
  human-readable dicts/objects.

• Separation of Concerns:
  By pushing domain logic into the `application.parsing` package,
  this file remains lightweight and largely free of XML-traversal code,
  making it easier to test and maintain.

The corresponding unit tests can be found in `tests/test_*`.
They exercise both the high-level API and various edge-cases such as
DTD validation, HTML cleaning, and external service wrappers.
"""

import warnings

import lxml.etree as ET

from pmcgrab.application.parsing import content as _content
from pmcgrab.application.parsing import contributors as _contributors
from pmcgrab.application.parsing import metadata as _metadata
from pmcgrab.application.parsing import sections as _sections
from pmcgrab.constants import UnmatchedCitationWarning, UnmatchedTableWarning, logger
from pmcgrab.domain.value_objects import BasicBiMap
from pmcgrab.fetch import get_xml, parse_local_xml
from pmcgrab.model import TextFigure, TextTable

# ---------------------------------------------------------------------------
# Public helper re-exports (thin aliases)
# ---------------------------------------------------------------------------
# Article / journal metadata --------------------------------------------------
gather_title = _metadata.gather_title

gather_authors = _contributors.gather_authors
gather_non_author_contributors = _contributors.gather_non_author_contributors

gather_abstract = _sections.gather_abstract
gather_body = _sections.gather_body

gather_journal_id = _metadata.gather_journal_id
gather_journal_title = _metadata.gather_journal_title
gather_issn = _metadata.gather_issn
gather_publisher_name = _metadata.gather_publisher_name
gather_publisher_location = _metadata.gather_publisher_location
gather_article_id = _metadata.gather_article_id
gather_article_types = _metadata.gather_article_types
gather_article_categories = _metadata.gather_article_categories
gather_keywords = _metadata.gather_keywords
gather_published_date = _metadata.gather_published_date
gather_history_dates = _metadata.gather_history_dates
gather_volume = _metadata.gather_volume
gather_issue = _metadata.gather_issue

# Pages (remain local – trivial one-liners)


def gather_fpage(root: ET.Element) -> str | None:
    """Extract the first page number from PMC article metadata.

    Args:
        root: Root element of the PMC article XML document

    Returns:
        str | None: First page number as string, or None if not found

    Examples:
        >>> root = ET.fromstring(xml_content)
        >>> first_page = gather_fpage(root)
        >>> print(f"Article starts on page: {first_page}")
    """
    fpage = root.xpath("//article-meta/fpage/text()")
    return fpage[0] if fpage else None


def gather_lpage(root: ET.Element) -> str | None:
    """Extract the last page number from PMC article metadata.

    Args:
        root: Root element of the PMC article XML document

    Returns:
        str | None: Last page number as string, or None if not found

    Examples:
        >>> root = ET.fromstring(xml_content)
        >>> last_page = gather_lpage(root)
        >>> print(f"Article ends on page: {last_page}")
    """
    lpage = root.xpath("//article-meta/lpage/text()")
    return lpage[0] if lpage else None


def gather_elocation_id(root: ET.Element) -> str | None:
    """Extract the electronic location identifier from PMC article metadata.

    Modern articles use elocation-id instead of traditional page numbers.

    Args:
        root: Root element of the PMC article XML document

    Returns:
        str | None: Electronic location ID as string, or None if not found
    """
    eloc = root.xpath("//article-meta/elocation-id/text()")
    return eloc[0] if eloc else None


def gather_counts(root: ET.Element) -> dict[str, int]:
    """Extract official content counts from PMC article metadata.

    PMC XML often includes <count> elements with official counts of figures,
    tables, pages, equations, references, etc.

    Args:
        root: Root element of the PMC article XML document

    Returns:
        dict[str, int]: Mapping of count types to values
    """
    counts: dict[str, int] = {}
    for count_elem in root.xpath("//article-meta/counts/count"):
        count_type = count_elem.get("count-type")
        if count_type:
            try:
                counts[count_type] = int(count_elem.get("count", "0"))
            except (ValueError, TypeError):
                pass
    # Also check specific named count elements
    for tag in (
        "fig-count",
        "table-count",
        "equation-count",
        "ref-count",
        "page-count",
        "word-count",
    ):
        elems = root.xpath(f"//article-meta/counts/{tag}")
        if elems:
            try:
                counts[tag.replace("-", "_")] = int(elems[0].get("count", "0"))
            except (ValueError, TypeError):
                pass
    return counts


def gather_self_uri(root: ET.Element) -> list[dict[str, str]]:
    """Extract self-URI elements pointing to article full-text links.

    Args:
        root: Root element of the PMC article XML document

    Returns:
        list[dict[str, str]]: List of URI dicts with 'href' and 'content_type' keys
    """
    uris: list[dict[str, str]] = []
    for uri in root.xpath("//article-meta/self-uri"):
        href = (
            uri.get("{http://www.w3.org/1999/xlink}href") or uri.get("xlink:href") or ""
        )
        content_type = uri.get("content-type", "")
        if href:
            uris.append({"href": href, "content_type": content_type})
    return uris


def gather_related_articles(root: ET.Element) -> list[dict[str, str]]:
    """Extract related article references (errata, commentaries, etc.).

    Args:
        root: Root element of the PMC article XML document

    Returns:
        list[dict[str, str]]: List of related article dicts
    """
    articles: list[dict[str, str]] = []
    for rel in root.xpath("//article-meta/related-article"):
        href = (
            rel.get("{http://www.w3.org/1999/xlink}href") or rel.get("xlink:href") or ""
        )
        articles.append(
            {
                "related_article_type": rel.get("related-article-type", ""),
                "ext_link_type": rel.get("ext-link-type", ""),
                "href": href,
                "id": rel.get("id", ""),
            }
        )
    return articles


def gather_conference_info(root: ET.Element) -> dict[str, str] | None:
    """Extract conference information for conference papers.

    Args:
        root: Root element of the PMC article XML document

    Returns:
        dict[str, str] | None: Conference info or None if not a conference paper
    """
    conf = root.xpath("//article-meta/conference")
    if not conf:
        return None
    c = conf[0]
    return {
        "conf_name": c.findtext("conf-name") or "",
        "conf_date": c.findtext("conf-date") or "",
        "conf_loc": c.findtext("conf-loc") or "",
        "conf_sponsor": c.findtext("conf-sponsor") or "",
        "conf_theme": c.findtext("conf-theme") or "",
        "conf_acronym": c.findtext("conf-acronym") or "",
    }


# Permissions / funding / misc content ---------------------------------------
gather_permissions = _content.gather_permissions
gather_funding = _content.gather_funding
gather_version_history = _content.gather_version_history
gather_equations = _content.gather_equations
gather_supplementary_material = _content.gather_supplementary_material
gather_ethics_disclosures = _content.gather_ethics_disclosures
gather_footnote = _content.gather_footnote
gather_acknowledgements = _content.gather_acknowledgements
gather_notes = _content.gather_notes
gather_custom_metadata = _content.gather_custom_metadata

# Abstract type (from sections module) ----------------------------------------
gather_abstract_type = _sections.gather_abstract_type


# ---------------------------------------------------------------------------
# Phase 5 extraction functions
# ---------------------------------------------------------------------------


def gather_subtitle(root: ET.Element) -> str | None:
    """Extract article subtitle from PMC XML."""
    subs = root.xpath("//article-meta/title-group/subtitle")
    if subs:
        return "".join(subs[0].itertext()).strip() or None
    return None


def gather_author_notes(root: ET.Element) -> dict[str, str | list[str]] | None:
    """Extract author-notes: correspondence, present addresses, footnotes."""
    notes_el = root.xpath("//article-meta/author-notes")
    if not notes_el:
        return None
    result: dict[str, str | list[str]] = {}
    # Correspondence
    corresp = []
    for c in notes_el[0].xpath("corresp"):
        corresp.append("".join(c.itertext()).strip())
    if corresp:
        result["correspondence"] = corresp
    # Footnotes within author-notes
    fns = []
    for fn in notes_el[0].xpath("fn"):
        fn_type = fn.get("fn-type", "")
        text = "".join(fn.itertext()).strip()
        if text:
            fns.append({"type": fn_type, "text": text})
    if fns:
        result["footnotes"] = fns
    return result or None


def gather_appendices(root: ET.Element) -> list[dict[str, str]] | None:
    """Extract appendices from <back>/<app-group>/<app>."""
    apps: list[dict[str, str]] = []
    for app in root.xpath("//back//app"):
        title_el = app.find("title")
        title = "".join(title_el.itertext()).strip() if title_el is not None else ""
        text = "".join(app.itertext()).strip()
        if title and text.startswith(title):
            text = text[len(title) :].strip()
        apps.append({"title": title, "text": text})
    return apps or None


def gather_glossary(root: ET.Element) -> list[dict[str, str]] | None:
    """Extract glossary / definition-list entries from <back>/<glossary>."""
    entries: list[dict[str, str]] = []
    for glossary in root.xpath("//back//glossary"):
        for def_item in glossary.xpath(".//def-item"):
            term_el = def_item.find("term")
            def_el = def_item.find("def")
            term = "".join(term_el.itertext()).strip() if term_el is not None else ""
            defn = "".join(def_el.itertext()).strip() if def_el is not None else ""
            entries.append({"term": term, "definition": defn})
    return entries or None


def gather_translated_titles(root: ET.Element) -> list[dict[str, str]] | None:
    """Extract translated titles from <trans-title-group>."""
    titles: list[dict[str, str]] = []
    for ttg in root.xpath("//article-meta/title-group/trans-title-group"):
        lang = ttg.get("{http://www.w3.org/XML/1998/namespace}lang", "")
        tt = ttg.find("trans-title")
        if tt is not None:
            titles.append({"lang": lang, "title": "".join(tt.itertext()).strip()})
    return titles or None


def gather_translated_abstracts(root: ET.Element) -> list[dict[str, str]] | None:
    """Extract translated abstracts from <trans-abstract>."""
    abstracts: list[dict[str, str]] = []
    for ta in root.xpath("//trans-abstract"):
        lang = ta.get("{http://www.w3.org/XML/1998/namespace}lang", "")
        text = "".join(ta.itertext()).strip()
        abstracts.append({"lang": lang, "text": text})
    return abstracts or None


def gather_tex_equations(root: ET.Element) -> list[str] | None:
    """Extract TeX/LaTeX equations from <tex-math> elements."""
    eqs: list[str] = []
    for tex in root.xpath("//tex-math"):
        if tex.text:
            eqs.append(tex.text.strip())
    return eqs or None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_citation(
    citation_root: ET.Element,
) -> dict[str, list[str] | str] | str:
    """Parse a citation XML element into structured reference information.

    Extracts bibliographic information from a PMC citation element, including
    authors, title, source, publication details, and identifiers. Handles
    both structured citations and mixed-citation formats.

    Args:
        citation_root: XML element containing citation information (<ref>)

    Returns:
        dict[str, list[str] | str] | str: Structured citation dictionary with keys:
            - authors: List of author names as "Given Surname"
            - title: Article title
            - source: Journal/source name
            - year: Publication year
            - volume: Journal volume
            - first_page: First page number
            - last_page: Last page number
            - doi: DOI identifier
            - pmid: PubMed ID
        If structured parsing fails, returns raw mixed-citation text as string.

    Warns:
        RuntimeWarning: If no authors are found in citation

    Examples:
        >>> citation_elem = root.xpath("//ref[@id='B1']")[0]
        >>> citation_data = _parse_citation(citation_elem)
        >>> print(f"Authors: {citation_data['authors']}")
        >>> print(f"Title: {citation_data['title']}")
    """
    # --- Author extraction (name + collab + etal) ---
    author_names: list[str] = []

    # Named authors (person-group type="author")
    for pg in citation_root.xpath('.//person-group[@person-group-type="author"]'):
        for name_el in pg.xpath("name"):
            given = _extract_xpath_text(name_el, "given-names") or ""
            surname = _extract_xpath_text(name_el, "surname") or ""
            name = f"{given} {surname}".strip()
            if name:
                author_names.append(name)
        # Collaborative group authors
        for collab in pg.xpath("collab"):
            collab_text = "".join(collab.itertext()).strip()
            if collab_text:
                author_names.append(collab_text)

    # Fallback: <name> directly under the element-citation/mixed-citation
    if not author_names:
        for name_el in citation_root.xpath(".//name"):
            given = _extract_xpath_text(name_el, "given-names") or ""
            surname = _extract_xpath_text(name_el, "surname") or ""
            name = f"{given} {surname}".strip()
            if name:
                author_names.append(name)

    # Standalone <collab> outside person-group
    if not author_names:
        for collab in citation_root.xpath(".//collab"):
            collab_text = "".join(collab.itertext()).strip()
            if collab_text:
                author_names.append(collab_text)

    # Check for <etal/>
    has_etal = len(citation_root.xpath(".//etal")) > 0

    if not author_names:
        mixed = citation_root.xpath(".//mixed-citation/text()")
        if mixed:
            return str(mixed[0])
        warnings.warn(
            f"No authors found in citation {citation_root.get('id')}",
            RuntimeWarning,
            stacklevel=2,
        )

    # --- Determine citation type ---
    pub_type = None
    for child_tag in ("element-citation", "mixed-citation", "nlm-citation"):
        child = citation_root.find(f".//{child_tag}")
        if child is not None:
            pub_type = child.get("publication-type")
            break

    # --- Build result dict ---
    result: dict[str, list[str] | str | None | bool] = {
        "authors": author_names,
        "has_etal": has_etal,
        "publication_type": pub_type,
        "title": (
            _extract_xpath_text(citation_root, ".//article-title")
            or _extract_xpath_text(citation_root, ".//chapter-title")
        ),
        "source": _extract_xpath_text(citation_root, ".//source"),
        "year": _extract_xpath_text(citation_root, ".//year"),
        "volume": _extract_xpath_text(citation_root, ".//volume"),
        "issue": _extract_xpath_text(citation_root, ".//issue"),
        "first_page": _extract_xpath_text(citation_root, ".//fpage"),
        "last_page": _extract_xpath_text(citation_root, ".//lpage"),
        "elocation_id": _extract_xpath_text(citation_root, ".//elocation-id"),
        "doi": _extract_xpath_text(citation_root, './/pub-id[@pub-id-type="doi"]'),
        "pmid": _extract_xpath_text(citation_root, './/pub-id[@pub-id-type="pmid"]'),
        "pmcid": _extract_xpath_text(citation_root, './/pub-id[@pub-id-type="pmcid"]'),
        "isbn": _extract_xpath_text(citation_root, ".//isbn"),
        "publisher_name": _extract_xpath_text(citation_root, ".//publisher-name"),
        "publisher_loc": _extract_xpath_text(citation_root, ".//publisher-loc"),
        "edition": _extract_xpath_text(citation_root, ".//edition"),
        "comment": _extract_xpath_text(citation_root, ".//comment"),
        # Book-specific fields
        "chapter_title": _extract_xpath_text(citation_root, ".//chapter-title"),
        "part_title": _extract_xpath_text(citation_root, ".//part-title"),
        # Conference-specific fields
        "conf_name": _extract_xpath_text(citation_root, ".//conf-name"),
        "conf_date": _extract_xpath_text(citation_root, ".//conf-date"),
        "conf_loc": _extract_xpath_text(citation_root, ".//conf-loc"),
        # Data citation fields
        "data_title": _extract_xpath_text(citation_root, ".//data-title"),
        # Patent fields
        "patent": _extract_xpath_text(citation_root, ".//patent"),
        # External links / URIs
        "uri": _extract_xpath_text(citation_root, ".//uri"),
    }

    # Editors
    editor_names: list[str] = []
    for pg in citation_root.xpath('.//person-group[@person-group-type="editor"]'):
        for name_el in pg.xpath("name"):
            given = _extract_xpath_text(name_el, "given-names") or ""
            surname = _extract_xpath_text(name_el, "surname") or ""
            name = f"{given} {surname}".strip()
            if name:
                editor_names.append(name)
    if editor_names:
        result["editors"] = editor_names

    # External links
    ext_links = []
    for ext in citation_root.xpath(".//ext-link"):
        href = ext.get("{http://www.w3.org/1999/xlink}href") or ext.get(
            "xlink:href", ""
        )
        if href:
            ext_links.append(href)
    if ext_links:
        result["ext_links"] = ext_links

    # Add full mixed-citation text as fallback
    mixed_elems = citation_root.xpath(".//mixed-citation")
    if mixed_elems:
        result["mixed_citation_text"] = "".join(mixed_elems[0].itertext()).strip()

    return result


def _extract_xpath_text(root: ET.Element, xpath: str, *, multiple: bool = False):
    """Extract text content from XML elements matching the given XPath.

    Utility function for safely extracting text from XML elements with
    support for both single and multiple matches. Handles missing elements
    gracefully by returning None or empty list as appropriate.

    Args:
        root: Root XML element to search within
        xpath: XPath expression to locate target elements
        multiple: If False (default), return first match text only.
                 If True, return list of all matching element texts.

    Returns:
        str | None | list[str]:
            - If multiple=False: First matching element's text or None if no matches
            - If multiple=True: List of all matching element texts (empty list if no matches)

    Examples:
        >>> # Extract single value
        >>> title = _extract_xpath_text(root, ".//article-title")
        >>>
        >>> # Extract multiple values
        >>> keywords = _extract_xpath_text(root, ".//kwd", multiple=True)
    """
    matches = root.xpath(xpath)
    if not matches:
        return [] if multiple else None
    if multiple:
        return [el.text for el in matches if el is not None and el.text is not None]
    return matches[0].text


def process_reference_map(
    paper_root: ET.Element, ref_map: BasicBiMap | None = None
) -> BasicBiMap:
    """Resolve cross-reference map items to structured objects.

    Takes a reference map containing XML snippets and resolves them to
    structured objects (citations, tables, figures) by looking up the
    actual target elements in the full document. This enables linking
    between text references and their definitions.

    Args:
        paper_root: Root element of the complete PMC article XML
        ref_map: Bidirectional map containing reference placeholders.
                If None, creates a new map from document <ref> elements.

    Returns:
        BasicBiMap: Resolved reference map where values are structured objects:
            - Citations: Dictionaries with author, title, year, etc.
            - Tables: TextTable objects with parsed DataFrame
            - Figures: TextFigure objects with metadata
            - Other: String representations of unhandled elements

    Warns:
        UnmatchedCitationWarning: When citation references cannot be resolved
        UnmatchedTableWarning: When table references cannot be resolved

    Examples:
        >>> # Process references from existing map
        >>> resolved_map = process_reference_map(root, ref_map)
        >>> citation = resolved_map[1]  # Get first citation
        >>> print(citation['title'])
        >>>
        >>> # Auto-generate from document refs
        >>> ref_map = process_reference_map(root, None)
    """
    if ref_map is None:
        ref_map = BasicBiMap()
    cleaned: dict[int, TextTable | TextFigure | dict[str, str] | str] = {}

    # Fallback: if the ref_map is empty populate it from <ref> elements so that
    # downstream logic and tests receive *something* meaningful to work with.
    if not ref_map:
        for idx, ref in enumerate(paper_root.xpath("//ref")):
            cleaned[idx] = _parse_citation(ref)
        return BasicBiMap(cleaned)

    # Resolve existing placeholder references from *ref_map* ------------
    for key, item in ref_map.items():
        root = ET.fromstring(item)
        if root.tag == "xref":
            rtype = root.get("ref-type")
            rid = root.get("rid")
            if rtype == "bibr":
                if not rid:
                    warnings.warn(
                        "Citation without reference id",
                        UnmatchedCitationWarning,
                        stacklevel=2,
                    )
                    continue
                matches = paper_root.xpath(f"//ref[@id='{rid}']")
                if not matches:
                    warnings.warn(
                        "Citation id not found", UnmatchedCitationWarning, stacklevel=2
                    )
                    continue
                cleaned[key] = _parse_citation(matches[0])
            elif rtype == "table":
                if not rid:
                    warnings.warn(
                        "Table ref without id", UnmatchedTableWarning, stacklevel=2
                    )
                    continue
                matches = paper_root.xpath(f"//table-wrap[@id='{rid}']")
                if matches:
                    cleaned[key] = TextTable(matches[0])
            elif rtype == "fig":
                if not rid:
                    continue
                matches = paper_root.xpath(f"//fig[@id='{rid}']")
                if matches:
                    cleaned[key] = TextFigure(matches[0])
            elif rtype == "fn" and rid:
                # Footnote references
                matches = paper_root.xpath(f"//fn[@id='{rid}']")
                if matches:
                    cleaned[key] = "".join(matches[0].itertext()).strip()
            elif rtype == "supplementary-material" and rid:
                matches = paper_root.xpath(f"//supplementary-material[@id='{rid}']")
                if matches:
                    cleaned[key] = {
                        "type": "supplementary-material",
                        "id": rid,
                        "text": "".join(matches[0].itertext()).strip(),
                    }
            elif rtype == "disp-formula" and rid:
                matches = paper_root.xpath(f"//disp-formula[@id='{rid}']")
                if matches:
                    cleaned[key] = {
                        "type": "formula",
                        "id": rid,
                        "text": "".join(matches[0].itertext()).strip(),
                    }
            elif rtype == "app" and rid:
                matches = paper_root.xpath(f"//app[@id='{rid}']")
                if matches:
                    cleaned[key] = {
                        "type": "appendix",
                        "id": rid,
                        "text": "".join(matches[0].itertext()).strip()[:200],
                    }
            elif rtype == "sec" and rid:
                matches = paper_root.xpath(f"//sec[@id='{rid}']")
                if matches:
                    title = matches[0].find("title")
                    cleaned[key] = {
                        "type": "section",
                        "id": rid,
                        "title": (
                            "".join(title.itertext()).strip()
                            if title is not None
                            else ""
                        ),
                    }
            elif rtype == "boxed-text" and rid:
                matches = paper_root.xpath(f"//boxed-text[@id='{rid}']")
                if matches:
                    cleaned[key] = {
                        "type": "boxed-text",
                        "id": rid,
                        "text": "".join(matches[0].itertext()).strip()[:200],
                    }
            elif rtype == "scheme" and rid:
                matches = paper_root.xpath(f"//*[@id='{rid}']")
                if matches:
                    cleaned[key] = {
                        "type": "scheme",
                        "id": rid,
                        "text": "".join(matches[0].itertext()).strip()[:200],
                    }
            elif rtype and rid:
                # Generic fallback for any other xref type
                matches = paper_root.xpath(f"//*[@id='{rid}']")
                if matches:
                    cleaned[key] = {
                        "type": rtype,
                        "id": rid,
                        "text": "".join(matches[0].itertext()).strip()[:200],
                    }
        elif root.tag == "table-wrap":
            cleaned[key] = TextTable(root)
        elif root.tag == "fig":
            cleaned[key] = TextFigure(root)
        else:
            cleaned[key] = ET.tostring(root)

    # Resolve back-references (numeric indirection)
    for key, val in cleaned.items():
        if isinstance(val, int):
            cleaned[key] = cleaned.get(val, val)
    return BasicBiMap(cleaned)


# Helper for build_complete_paper_dict ---------------------------------------


def _get_ref_type(value):
    """Determine the type of reference based on object type and content.

    Classifies reference objects into categories (citation, table, figure)
    based on their Python type and content characteristics. This enables
    proper categorization and processing of different reference types.

    Args:
        value: Reference object to classify (TextTable, TextFigure, dict, or other)

    Returns:
        str: Reference type classification:
            - "table": For TextTable instances
            - "fig": For TextFigure instances or dicts with "Caption" key
            - "citation": For all other references (default)

    Examples:
        >>> table_obj = TextTable(table_element)
        >>> _get_ref_type(table_obj)
        'table'
        >>> figure_dict = {"Caption": "Figure 1", "Label": "F1"}
        >>> _get_ref_type(figure_dict)
        'fig'
    """
    if isinstance(value, TextTable):
        return "table"
    if isinstance(value, TextFigure):
        return "fig"
    if isinstance(value, dict):
        return "fig" if "Caption" in value else "citation"
    return "citation"


def _split_citations_tables_figs(ref_map: BasicBiMap):
    """Categorize references from reference map into citations, tables, and figures.

    Processes all items in the reference map and separates them into different
    categories based on their type and content. This enables type-specific
    processing and output formatting.

    Args:
        ref_map: Bidirectional map containing resolved reference objects

    Returns:
        tuple[list, list, list]: A tuple containing:
            - citations: List of citation dictionaries
            - tables: List of pandas DataFrames from resolved tables
            - figures: List of figure dictionaries with metadata

    Examples:
        >>> citations, tables, figures = _split_citations_tables_figs(ref_map)
        >>> print(f"Found {len(citations)} citations, {len(tables)} tables, {len(figures)} figures")
    """
    citations, tables, figures = [], [], []
    for item in ref_map.values():
        rtype = _get_ref_type(item)
        if rtype == "citation":
            citations.append(item)
        elif rtype == "table" and hasattr(item, "df"):
            tables.append(item.df)
        elif rtype == "fig":
            figures.append(item if isinstance(item, dict) else item.fig_dict)
    return citations, tables, figures


# ---------------------------------------------------------------------------
# Public orchestrators
# ---------------------------------------------------------------------------


def paper_dict_from_pmc(
    pmcid: int,
    *,
    email: str,
    download: bool = False,
    validate: bool = True,
    verbose: bool = False,
    suppress_warnings: bool = False,
    suppress_errors: bool = False,
) -> dict[str, str | int | dict | list]:
    """Download and parse a PMC article into a structured dictionary.

    One-shot convenience function that downloads PMC article XML from NCBI,
    validates it, and parses it into a comprehensive dictionary containing
    all article metadata, content sections, references, tables, and figures.

    This is the main entry point for converting PMC articles into AI-ready
    structured data suitable for downstream processing, RAG applications,
    and machine learning pipelines.

    Args:
        pmcid: PubMed Central ID (numeric)
        email: Contact email required by NCBI Entrez API
        download: If True, cache the raw XML locally in data/ directory
        validate: If True, perform DTD validation of the XML structure
        verbose: If True, emit progress logging messages
        suppress_warnings: If True, suppress parsing warnings
        suppress_errors: If True, return empty dict on errors instead of raising

    Returns:
        dict[str, str | int | dict | list]: Comprehensive article dictionary with keys:
            - PMCID: Article identifier
            - Title: Article title
            - Authors: Author information
            - Abstract: Structured abstract sections
            - Body: Main article content sections
            - Citations: Reference list
            - Tables: Parsed table data
            - Figures: Figure metadata
            - Journal metadata (title, ISSN, publisher, etc.)
            - Publication metadata (dates, volume, issue, pages, etc.)
            - Content metadata (keywords, funding, ethics, etc.)

    Raises:
        HTTPError: If article download fails after retries
        ValidationError: If XML validation fails (when validate=True)
        Various XML parsing errors: If suppress_errors=False

    Examples:
        >>> # Basic usage
        >>> article = paper_dict_from_pmc(7181753, email="user@example.com")
        >>> print(article['Title'])
        >>> print(len(article['Body']))
        >>>
        >>> # With caching and validation
        >>> article = paper_dict_from_pmc(
        ...     7181753,
        ...     email="user@example.com",
        ...     download=True,
        ...     validate=True,
        ...     verbose=True
        ... )
    """
    if verbose:
        logger.info("Generating Paper object for PMCID=%s …", pmcid)
    tree = get_xml(pmcid, email, download, validate, verbose=verbose)
    root = tree.getroot()
    return generate_paper_dict(pmcid, root, verbose, suppress_warnings, suppress_errors)


def paper_dict_from_local_xml(
    xml_path: str,
    *,
    verbose: bool = False,
    suppress_warnings: bool = False,
    suppress_errors: bool = False,
    strip_text_styling: bool = True,
    validate: bool = False,
) -> dict[str, str | int | dict | list]:
    """Parse a local JATS XML file into a structured article dictionary.

    This is the local-file counterpart of :func:`paper_dict_from_pmc`.
    Instead of downloading XML from NCBI Entrez, it reads a pre-downloaded
    JATS XML file from disk, making it ideal for processing bulk-exported
    PMC data (e.g. from ``https://ftp.ncbi.nlm.nih.gov/pub/pmc/``).

    Because no network I/O is involved, this function is orders of magnitude
    faster than :func:`paper_dict_from_pmc` and does not require an email
    address or timeouts.

    Args:
        xml_path: Path to a JATS XML file on disk.
        verbose: If True, emit progress logging messages.
        suppress_warnings: If True, suppress parsing warnings.
        suppress_errors: If True, return empty dict on errors instead of raising.
        strip_text_styling: If True, remove HTML-style formatting tags.
        validate: If True, perform DTD validation against PMC schema.

    Returns:
        dict[str, str | int | dict | list]: Comprehensive article dictionary
            with the same structure as :func:`paper_dict_from_pmc` output.

    Raises:
        FileNotFoundError: If *xml_path* does not exist.

    Examples:
        >>> article = paper_dict_from_local_xml("path/to/PMC7181753.xml")
        >>> print(article["Title"])
        >>> print(len(article["Body"]))
        >>>
        >>> # Batch-friendly: suppress errors and warnings
        >>> article = paper_dict_from_local_xml(
        ...     "article.xml",
        ...     suppress_warnings=True,
        ...     suppress_errors=True,
        ... )
    """
    tree, pmcid = parse_local_xml(
        xml_path,
        strip_text_styling=strip_text_styling,
        validate=validate,
        verbose=verbose,
    )
    root = tree.getroot()
    effective_pmcid = pmcid if pmcid is not None else 0
    if verbose:
        logger.info("Parsing local XML for PMCID=%s from %s", effective_pmcid, xml_path)
    return generate_paper_dict(
        effective_pmcid, root, verbose, suppress_warnings, suppress_errors
    )


def generate_paper_dict(
    pmcid: int,
    root: ET.Element,
    verbose: bool = False,
    suppress_warnings: bool = False,
    suppress_errors: bool = False,
) -> dict[str, str | int | dict | list]:
    """Parse PMC article XML into structured dictionary with error handling.

    Wrapper around build_complete_paper_dict() that provides configurable
    warning suppression and error handling. Accepts pre-parsed XML root
    element rather than downloading, giving callers control over the XML
    acquisition process.

    Args:
        pmcid: PubMed Central ID for identification
        root: Root element of parsed PMC article XML document
        verbose: If True, emit progress logging messages
        suppress_warnings: If True, suppress all warnings during parsing
        suppress_errors: If True, return empty dict on errors instead of raising

    Returns:
        dict[str, str | int | dict | list]: Complete article dictionary structure,
                                           or empty dict if suppress_errors=True and parsing fails

    Examples:
        >>> tree = ET.parse("article.xml")
        >>> root = tree.getroot()
        >>> article = generate_paper_dict(7181753, root, verbose=True)
        >>>
        >>> # With error suppression for batch processing
        >>> article = generate_paper_dict(
        ...     pmcid, root,
        ...     suppress_warnings=True,
        ...     suppress_errors=True
        ... )
        >>> if article:  # Check if parsing succeeded
        ...     process_article(article)
    """
    with warnings.catch_warnings():
        if suppress_warnings:
            warnings.simplefilter("ignore")
        try:
            data = build_complete_paper_dict(pmcid, root, verbose)
        except Exception as exc:
            data = {} if suppress_errors else (_raise(exc))
    return data


def _raise(exc):
    """Helper function for EAFP (Easier to Ask for Forgiveness than Permission) pattern.

    Args:
        exc: Exception to re-raise

    Raises:
        The provided exception
    """
    raise exc


def build_complete_paper_dict(
    pmcid: int,
    root: ET.Element,
    verbose: bool = False,
    *,
    include_ref_map_with_tags: bool = False,
) -> dict[str, str | int | dict | list]:
    """Low-level orchestrator that coordinates all parsing operations.

    Core function that coordinates all the specialized gather_* functions
    to extract every piece of information from a PMC article XML document.
    Builds reference maps, resolves cross-references, and assembles the
    complete structured representation.

    This function represents the main parsing pipeline that transforms
    raw XML into the structured dictionary format expected by the Paper
    class and downstream applications.

    Args:
        pmcid: PubMed Central ID for identification and logging
        root: Root element of the PMC article XML document
        verbose: If True, emit progress logging messages

    Returns:
        dict[str, str | int | dict | list]: Complete article dictionary containing:
            - Metadata: PMCID, title, authors, journal info, publication details
            - Content: Abstract sections, body sections, structured text
            - References: Citations, cross-reference mappings
            - Data: Tables (as DataFrames), figures, equations
            - Supplementary: Permissions, funding, ethics, notes, custom metadata

    The returned dictionary structure matches the format expected by the
    Paper class constructor and contains all information needed for
    comprehensive article analysis.

    Examples:
        >>> tree = ET.parse("pmc_article.xml")
        >>> root = tree.getroot()
        >>> article_dict = build_complete_paper_dict(7181753, root, verbose=True)
        >>> print(f"Title: {article_dict['Title']}")
        >>> print(f"Sections: {len(article_dict['Body'])}")
        >>> print(f"Citations: {len(article_dict['Citations'])}")
    """
    ref_map: BasicBiMap = BasicBiMap()

    def _safe(fn, *args, default=None, **kwargs):
        """Call *fn* and return *default* if it raises."""
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            logger.warning(
                "gather_%s failed for PMCID %s: %s",
                getattr(fn, "__name__", "?"),
                pmcid,
                exc,
            )
            return default

    d: dict[str, str | int | dict | list] = {
        "PMCID": pmcid,
        "Title": _safe(gather_title, root),
        "Authors": _safe(gather_authors, root),
        "Non-Author Contributors": _safe(
            gather_non_author_contributors, root, default=""
        ),
        "Abstract": _safe(gather_abstract, root, ref_map),
        "Body": _safe(gather_body, root, ref_map),
        "Journal ID": _safe(gather_journal_id, root, default={}),
        "Journal Title": _safe(gather_journal_title, root),
        "ISSN": _safe(gather_issn, root, default={}),
        "Publisher Name": _safe(gather_publisher_name, root, default=""),
        "Publisher Location": _safe(gather_publisher_location, root),
        "Article ID": _safe(gather_article_id, root, default={}),
        "Article Types": _safe(gather_article_types, root),
        "Article Categories": _safe(gather_article_categories, root),
        "Keywords": _safe(gather_keywords, root),
        "Published Date": _safe(gather_published_date, root, default={}),
        "Version History": _safe(gather_version_history, root),
        "History Dates": _safe(gather_history_dates, root),
        "Volume": _safe(gather_volume, root),
        "Issue": _safe(gather_issue, root),
        "FPage": _safe(gather_fpage, root),
        "LPage": _safe(gather_lpage, root),
        "Elocation ID": _safe(gather_elocation_id, root),
        "Permissions": _safe(gather_permissions, root),
        "Funding": _safe(gather_funding, root),
        "Ethics": _safe(gather_ethics_disclosures, root),
        "Supplementary Material": _safe(gather_supplementary_material, root),
        "Footnote": _safe(gather_footnote, root),
        "Acknowledgements": _safe(gather_acknowledgements, root, default=[]),
        "Notes": _safe(gather_notes, root, default=[]),
        "Custom Meta": _safe(gather_custom_metadata, root),
        "Counts": _safe(gather_counts, root, default={}),
        "Self URI": _safe(gather_self_uri, root, default=[]),
        "Related Articles": _safe(gather_related_articles, root, default=[]),
        "Conference": _safe(gather_conference_info, root),
        # Phase 5 extractions
        "Subtitle": _safe(gather_subtitle, root),
        "Author Notes": _safe(gather_author_notes, root),
        "Appendices": _safe(gather_appendices, root),
        "Glossary": _safe(gather_glossary, root),
        "Translated Titles": _safe(gather_translated_titles, root),
        "Translated Abstracts": _safe(gather_translated_abstracts, root),
        "Abstract Type": _safe(gather_abstract_type, root),
        "TeX Equations": _safe(gather_tex_equations, root),
    }

    # Only deep-copy the ref_map when explicitly requested (expensive operation)
    if include_ref_map_with_tags:
        import copy

        d["Ref Map With Tags"] = copy.deepcopy(ref_map)
    else:
        d["Ref Map With Tags"] = BasicBiMap()

    d["Ref Map"] = process_reference_map(root, ref_map)

    citations, tables, figures = _split_citations_tables_figs(d["Ref Map"])
    d.update(
        {
            "Citations": citations,
            "Tables": tables,
            "Figures": figures,
            "Equations": gather_equations(root),
        }
    )

    if verbose:
        logger.info("Finished generating Paper object for PMCID=%s", pmcid)
    return d
