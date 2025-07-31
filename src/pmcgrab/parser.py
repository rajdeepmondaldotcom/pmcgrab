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

import copy
import warnings

import lxml.etree as ET

from pmcgrab.application.parsing import content as _content
from pmcgrab.application.parsing import contributors as _contributors
from pmcgrab.application.parsing import metadata as _metadata
from pmcgrab.application.parsing import sections as _sections
from pmcgrab.constants import UnmatchedCitationWarning, UnmatchedTableWarning, logger
from pmcgrab.domain.value_objects import BasicBiMap
from pmcgrab.fetch import get_xml
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
    """Return first page number if available."""
    fpage = root.xpath("//article-meta/fpage/text()")
    return fpage[0] if fpage else None


def gather_lpage(root: ET.Element) -> str | None:
    """Return last page number if available."""
    lpage = root.xpath("//article-meta/lpage/text()")
    return lpage[0] if lpage else None


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

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_citation(
    citation_root: ET.Element,
) -> dict[str, list[str] | str] | str:
    """Parse a citation entry into a dictionary of reference details."""
    authors = citation_root.xpath('.//person-group[@person-group-type="author"]/name')
    if not authors:
        mixed = citation_root.xpath("//mixed-citation/text()")
        if mixed:
            return str(mixed[0])
        warnings.warn(
            f"No authors found in citation {citation_root.get('id')}",
            RuntimeWarning,
            stacklevel=2,
        )
    return {
        "authors": [
            f"{_extract_xpath_text(author, 'given-names')} {_extract_xpath_text(author, 'surname')}"
            for author in authors
        ],
        "title": _extract_xpath_text(citation_root, ".//article-title"),
        "source": _extract_xpath_text(citation_root, ".//source"),
        "year": _extract_xpath_text(citation_root, ".//year"),
        "volume": _extract_xpath_text(citation_root, ".//volume"),
        "first_page": _extract_xpath_text(citation_root, ".//fpage"),
        "last_page": _extract_xpath_text(citation_root, ".//lpage"),
        "doi": _extract_xpath_text(citation_root, './/pub-id[@pub-id-type="doi"]'),
        "pmid": _extract_xpath_text(citation_root, './/pub-id[@pub-id-type="pmid"]'),
    }


def _extract_xpath_text(root: ET.Element, xpath: str, *, multiple: bool = False):
    """Return the text(s) at *xpath*.

    If *multiple* is ``False`` (default) the first matching element's text is
    returned, otherwise a list with **all** matched element texts is returned.
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
    """Resolve reference map items to structured citation / table / figure objects."""
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
    if isinstance(value, TextTable):
        return "table"
    if isinstance(value, TextFigure):
        return "fig"
    if isinstance(value, dict):
        return "fig" if "Caption" in value else "citation"
    return "citation"


def _split_citations_tables_figs(ref_map: BasicBiMap):
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
    if verbose:
        logger.info("Generating Paper object for PMCID=%s …", pmcid)
    tree = get_xml(pmcid, email, download, validate, verbose=verbose)
    root = tree.getroot()
    return generate_paper_dict(pmcid, root, verbose, suppress_warnings, suppress_errors)


def generate_paper_dict(
    pmcid: int,
    root: ET.Element,
    verbose: bool = False,
    suppress_warnings: bool = False,
    suppress_errors: bool = False,
) -> dict[str, str | int | dict | list]:
    if suppress_warnings:
        warnings.simplefilter("ignore")
    try:
        data = build_complete_paper_dict(pmcid, root, verbose)
    except Exception as exc:
        data = {} if suppress_errors else (_raise(exc))
    finally:
        if suppress_warnings:
            warnings.simplefilter("default")
    return data


def _raise(exc):  # helper for EAFP pattern above
    raise exc


def build_complete_paper_dict(
    pmcid: int, root: ET.Element, verbose: bool = False
) -> dict[str, str | int | dict | list]:
    ref_map: BasicBiMap = BasicBiMap()
    d: dict[str, str | int | dict | list] = {
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
        "Publisher Location": gather_publisher_location(root),
        "Article ID": gather_article_id(root),
        "Article Types": gather_article_types(root),
        "Article Categories": gather_article_categories(root),
        "Keywords": gather_keywords(root),
        "Published Date": gather_published_date(root),
        "Version History": gather_version_history(root),
        "History Dates": gather_history_dates(root),
        "Volume": gather_volume(root),
        "Issue": gather_issue(root),
        "FPage": gather_fpage(root),
        "LPage": gather_lpage(root),
        "First Page": gather_fpage(root),
        "Last Page": gather_lpage(root),
        "Permissions": gather_permissions(root),
        "Funding": gather_funding(root),
        "Ethics": gather_ethics_disclosures(root),
        "Supplementary Material": gather_supplementary_material(root),
        "Footnote": gather_footnote(root),
        "Acknowledgements": gather_acknowledgements(root),
        "Notes": gather_notes(root),
        "Custom Meta": gather_custom_metadata(root),
        "Ref Map With Tags": copy.deepcopy(ref_map),
        "Ref Map": process_reference_map(root, ref_map),
    }

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
