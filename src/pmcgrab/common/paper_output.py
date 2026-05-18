from __future__ import annotations

"""Canonical JSON output schema for parsed PMC articles."""

import datetime as _dt
import json
from typing import TYPE_CHECKING, Any, cast

import lxml.etree as _ET

from pmcgrab.common.paper_view import to_paper_output
from pmcgrab.common.serialization import normalize_value

if TYPE_CHECKING:
    from pmcgrab.model import Paper

ArticleOutput = dict[str, Any]

_SCHEMA_VERSION_V2 = 2
_SCHEMA_VERSION_V3 = 3
_SCHEMA_VERSION_V4 = 4
_SCHEMA_VERSION = _SCHEMA_VERSION_V2
_DEFAULT_SCHEMA_VERSION = _SCHEMA_VERSION_V4
_EMPTY_GROUPS = {
    "identifiers": {
        "pmc_id": "",
        "pmcid": "",
        "pmid": "",
        "doi": "",
        "publisher_id": "",
        "other": {},
    },
    "title": {"main": "", "subtitle": "", "translated": []},
    "contributors": {
        "authors": [],
        "non_author_contributors": [],
        "author_notes": {},
    },
    "publication": {
        "journal": {"title": "", "alternate_titles": [], "ids": {}, "issn": {}},
        "publisher": {
            "name": "",
            "alternate_names": [],
            "location": "",
            "alternate_locations": [],
        },
        "classification": {"article_types": [], "article_categories": []},
        "dates": {"published": {}, "history": {}, "version_history": []},
        "issue": {
            "volume": "",
            "issue": "",
            "first_page": "",
            "last_page": "",
            "elocation_id": "",
        },
        "conference": {},
    },
    "content": {
        "abstract_type": "",
        "abstract": [],
        "translated_abstracts": [],
        "sections": [],
        "appendices": [],
        "glossary": [],
        "footnotes": "",
        "acknowledgements": [],
        "notes": [],
    },
    "assets": {
        "citations": [],
        "tables": [],
        "figures": [],
        "equations": {"mathml": [], "tex": []},
        "supplementary_material": [],
    },
    "compliance": {
        "permissions": {},
        "copyright": "",
        "license": "",
        "ethics": {},
        "funding": [],
    },
    "metadata": {
        "keywords": [],
        "counts": {},
        "self_uri": [],
        "related_articles": [],
        "custom_meta": {},
    },
}


def paper_to_output_dict(
    paper: Paper,
    *,
    pmc_id: str | int | None = None,
    include_processing_fields: bool = False,
    source: str | None = None,
    xml_path: str | None = None,
    require_body: bool = False,
    schema_version: int | None = None,
    output_style: str | None = None,
) -> ArticleOutput | None:
    """Return a public article dictionary for a parsed paper.

    ``Paper.to_dict()``, application processing helpers, and CLI output share
    this function so each JSON contract has one owner. The default output style
    is the clean paper view; pass ``output_style="full"`` for V2/V3/V4.
    """
    output_style, schema_version = _resolve_output_options(output_style, schema_version)
    if schema_version not in {
        _SCHEMA_VERSION_V2,
        _SCHEMA_VERSION_V3,
        _SCHEMA_VERSION_V4,
    }:
        raise ValueError("schema_version must be 2, 3, or 4")

    if not paper.has_data:
        if require_body:
            return None
        if schema_version == _SCHEMA_VERSION_V4:
            empty = _empty_output_v4()
        elif schema_version == _SCHEMA_VERSION_V3:
            empty = _empty_output_v3()
        else:
            empty = _empty_output()
        if output_style == "paper":
            return cast(ArticleOutput, to_paper_output(empty))
        return cast(ArticleOutput, normalize_value(empty))

    registry = _AssetRegistry()
    if schema_version == _SCHEMA_VERSION_V2:
        data = _article_output(
            paper,
            pmc_id=pmc_id,
            registry=registry,
            include_processing_fields=include_processing_fields,
            source=source,
            xml_path=xml_path,
        )
    elif schema_version == _SCHEMA_VERSION_V3:
        data = _article_output_v3(
            paper,
            pmc_id=pmc_id,
            registry=registry,
            include_processing_fields=include_processing_fields,
            source=source,
            xml_path=xml_path,
        )
    else:
        data = _article_output_v4(
            paper,
            pmc_id=pmc_id,
            registry=registry,
            include_processing_fields=include_processing_fields,
            source=source,
            xml_path=xml_path,
        )
    if require_body and not data["content"]["sections"]:
        return None
    if output_style == "paper":
        return cast(ArticleOutput, to_paper_output(data))
    return cast(ArticleOutput, normalize_value(data))


def _resolve_output_options(
    output_style: str | None, schema_version: int | None
) -> tuple[str, int]:
    """Resolve output-style defaults while preserving explicit schema calls."""
    if output_style is None:
        output_style = "full" if schema_version is not None else "paper"
    if output_style not in {"paper", "full"}:
        raise ValueError("output_style must be 'paper' or 'full'")
    if output_style == "paper":
        if schema_version not in (None, _SCHEMA_VERSION_V4):
            raise ValueError(
                "schema_version is only supported with output_style='full'"
            )
        return output_style, _SCHEMA_VERSION_V4
    return output_style, schema_version or _DEFAULT_SCHEMA_VERSION


def _article_output(
    paper: Paper,
    *,
    pmc_id: str | int | None,
    registry: _AssetRegistry,
    include_processing_fields: bool,
    source: str | None,
    xml_path: str | None,
) -> ArticleOutput:
    """Build the canonical grouped article output."""
    effective_pmc_id = pmc_id if pmc_id is not None else getattr(paper, "pmcid", None)
    sections = _content_sections(getattr(paper, "body", None), registry)
    journal_title, alternate_journal_titles = _primary_with_alternates(
        getattr(paper, "journal_title", None)
    )
    publisher_name, alternate_publisher_names = _primary_with_alternates(
        getattr(paper, "publisher_name", None)
    )
    publisher_location, alternate_publisher_locations = _primary_with_alternates(
        getattr(paper, "publisher_location", None)
    )

    if not registry.tables:
        for table in _raw_list(getattr(paper, "tables", None)):
            registry.add_table(table)
    if not registry.figures:
        for figure in _raw_list(getattr(paper, "figures", None)):
            registry.add_figure(figure)

    return {
        "schema_version": _SCHEMA_VERSION,
        "has_data": True,
        "identifiers": _identifiers(
            getattr(paper, "article_id", None), effective_pmc_id
        ),
        "title": {
            "main": _as_string(getattr(paper, "title", None)),
            "subtitle": _as_string(getattr(paper, "subtitle", None)),
            "translated": _as_list(getattr(paper, "translated_titles", None)),
        },
        "contributors": {
            "authors": _as_list(getattr(paper, "authors", None)),
            "non_author_contributors": _contributors(
                getattr(paper, "non_author_contributors", None)
            ),
            "author_notes": _as_dict(getattr(paper, "author_notes", None)),
        },
        "publication": {
            "journal": {
                "title": journal_title,
                "alternate_titles": alternate_journal_titles,
                "ids": _as_dict(getattr(paper, "journal_id", None)),
                "issn": _as_dict(getattr(paper, "issn", None)),
            },
            "publisher": {
                "name": publisher_name,
                "alternate_names": alternate_publisher_names,
                "location": publisher_location,
                "alternate_locations": alternate_publisher_locations,
            },
            "classification": {
                "article_types": _as_list(getattr(paper, "article_types", None)),
                "article_categories": _as_list(
                    getattr(paper, "article_categories", None)
                ),
            },
            "dates": {
                "published": _as_dict(getattr(paper, "published_date", None)),
                "history": _as_dict(getattr(paper, "history_dates", None)),
                "version_history": _as_list(getattr(paper, "version_history", None)),
            },
            "issue": {
                "volume": _as_string(getattr(paper, "volume", None)),
                "issue": _as_string(getattr(paper, "issue", None)),
                "first_page": _as_string(getattr(paper, "fpage", None)),
                "last_page": _as_string(getattr(paper, "lpage", None)),
                "elocation_id": _as_string(getattr(paper, "elocation_id", None)),
            },
            "conference": _as_dict(getattr(paper, "conference", None)),
        },
        "content": {
            "abstract_type": _as_string(getattr(paper, "abstract_type", None)),
            "abstract": _abstract_sections(getattr(paper, "abstract", None)),
            "translated_abstracts": _as_list(
                getattr(paper, "translated_abstracts", None)
            ),
            "sections": sections,
            "appendices": _as_list(getattr(paper, "appendices", None)),
            "glossary": _as_list(getattr(paper, "glossary", None)),
            "footnotes": _as_string(getattr(paper, "footnote", None)),
            "acknowledgements": _as_list(getattr(paper, "acknowledgements", None)),
            "notes": _as_list(getattr(paper, "notes", None)),
        },
        "assets": {
            "citations": _as_list(getattr(paper, "citations", None)),
            "tables": registry.tables,
            "figures": registry.figures,
            "equations": {
                "mathml": _as_list(getattr(paper, "equations", None)),
                "tex": _as_list(getattr(paper, "tex_equations", None)),
            },
            "supplementary_material": _as_list(getattr(paper, "supplementary", None)),
        },
        "compliance": {
            "permissions": _as_dict(getattr(paper, "permissions", None)),
            "copyright": _as_string(getattr(paper, "copyright", None)),
            "license": _as_string(getattr(paper, "license", None)),
            "ethics": _as_dict(getattr(paper, "ethics", None)),
            "funding": _as_list(getattr(paper, "funding", None)),
        },
        "metadata": {
            "keywords": _as_list(getattr(paper, "keywords", None)),
            "counts": _as_dict(getattr(paper, "counts", None)),
            "self_uri": _as_list(getattr(paper, "self_uri", None)),
            "related_articles": _as_list(getattr(paper, "related_articles", None)),
            "custom_meta": _as_dict(getattr(paper, "custom_meta", None)),
        },
        "provenance": _provenance(
            paper,
            include_processing_fields=include_processing_fields,
            source=source,
            xml_path=xml_path,
        ),
    }


def _article_output_v3(
    paper: Paper,
    *,
    pmc_id: str | int | None,
    registry: _AssetRegistry,
    include_processing_fields: bool,
    source: str | None,
    xml_path: str | None,
) -> ArticleOutput:
    """Build the fidelity-first V3 article output."""
    effective_pmc_id = pmc_id if pmc_id is not None else getattr(paper, "pmcid", None)
    sections = _content_sections(getattr(paper, "body", None), registry)
    abstracts = _abstract_sections_v3(paper)
    primary_abstract = next(
        (item for item in abstracts if item.get("is_primary")),
        abstracts[0] if abstracts else {},
    )

    if not registry.tables:
        for table in _raw_list(getattr(paper, "tables", None)):
            registry.add_table(table)
    if not registry.figures:
        for figure in _raw_list(getattr(paper, "figures", None)):
            registry.add_figure(figure)

    journal_title, alternate_journal_titles = _primary_with_alternates(
        getattr(paper, "journal_title", None)
    )
    publisher_name, alternate_publisher_names = _primary_with_alternates(
        getattr(paper, "publisher_name", None)
    )
    publisher_location, alternate_publisher_locations = _primary_with_alternates(
        getattr(paper, "publisher_location", None)
    )

    diagnostics = _diagnostics(paper, sections=sections, abstracts=abstracts)
    return {
        "schema_version": _SCHEMA_VERSION_V3,
        "has_data": True,
        "article": {
            "identifiers": _identifiers(
                getattr(paper, "article_id", None), effective_pmc_id
            ),
            "title": {
                "main": _as_string(getattr(paper, "title", None)),
                "subtitle": _as_string(getattr(paper, "subtitle", None)),
                "translated": _as_list(getattr(paper, "translated_titles", None)),
            },
            "contributors": {
                "authors": _as_list(getattr(paper, "authors", None)),
                "non_author_contributors": _contributors(
                    getattr(paper, "non_author_contributors", None)
                ),
                "author_notes": _as_dict(getattr(paper, "author_notes", None)),
            },
            "publication": {
                "journal": {
                    "title": journal_title,
                    "alternate_titles": alternate_journal_titles,
                    "ids": _as_dict(getattr(paper, "journal_id", None)),
                    "issn": _as_dict(getattr(paper, "issn", None)),
                },
                "publisher": {
                    "name": publisher_name,
                    "alternate_names": alternate_publisher_names,
                    "location": publisher_location,
                    "alternate_locations": alternate_publisher_locations,
                },
                "classification": {
                    "article_types": _as_list(getattr(paper, "article_types", None)),
                    "article_categories": _as_list(
                        getattr(paper, "article_categories", None)
                    ),
                },
                "dates": _date_records_for_output(paper),
                "issue": {
                    "volume": _as_string(getattr(paper, "volume", None)),
                    "issue": _as_string(getattr(paper, "issue", None)),
                    "first_page": _as_string(getattr(paper, "fpage", None)),
                    "last_page": _as_string(getattr(paper, "lpage", None)),
                    "elocation_id": _as_string(getattr(paper, "elocation_id", None)),
                },
                "conference": _as_dict(getattr(paper, "conference", None)),
            },
            "compliance": {
                "permissions": _as_dict(getattr(paper, "permissions", None)),
                "copyright": _as_string(getattr(paper, "copyright", None)),
                "license": _as_string(getattr(paper, "license", None)),
                "ethics": _as_dict(getattr(paper, "ethics", None)),
                "funding": _as_list(getattr(paper, "funding", None)),
            },
            "metadata": {
                "keywords": _as_list(getattr(paper, "keywords", None)),
                "counts": _as_dict(getattr(paper, "counts", None)),
                "self_uri": _as_list(getattr(paper, "self_uri", None)),
                "related_articles": _as_list(getattr(paper, "related_articles", None)),
                "custom_meta": _as_dict(getattr(paper, "custom_meta", None)),
            },
        },
        "content": {
            "abstracts": abstracts,
            "primary_abstract": primary_abstract,
            "sections": sections,
            "appendices": _as_list(getattr(paper, "appendices", None)),
            "glossary": _as_list(getattr(paper, "glossary", None)),
            "footnotes": _as_string(getattr(paper, "footnote", None)),
            "acknowledgements": _as_list(getattr(paper, "acknowledgements", None)),
            "notes": _as_list(getattr(paper, "notes", None)),
        },
        "assets": {
            "references": _references_for_output(paper),
            "tables": [_table_record_v3(table) for table in registry.tables],
            "figures": [_figure_record_v3(figure) for figure in registry.figures],
            "equations": {
                "mathml": _as_list(getattr(paper, "equations", None)),
                "tex": _as_list(getattr(paper, "tex_equations", None)),
            },
            "supplementary_material": _as_list(getattr(paper, "supplementary", None)),
        },
        "links": _as_list(getattr(paper, "reference_links", None)),
        "quality": {
            "status": _quality_status(sections, diagnostics),
            "diagnostics": diagnostics,
            "summary": {
                "abstract_count": len(abstracts),
                "section_count": len(sections),
                "reference_count": len(_references_for_output(paper)),
                "link_count": len(_as_list(getattr(paper, "reference_links", None))),
            },
        },
        "provenance": _provenance(
            paper,
            include_processing_fields=include_processing_fields,
            source=source,
            xml_path=xml_path,
        ),
    }


def _article_output_v4(
    paper: Paper,
    *,
    pmc_id: str | int | None,
    registry: _AssetRegistry,
    include_processing_fields: bool,
    source: str | None,
    xml_path: str | None,
) -> ArticleOutput:
    """Build the canonical, loss-aware V4 article output."""
    effective_pmc_id = pmc_id if pmc_id is not None else getattr(paper, "pmcid", None)
    sections = _parse_result_list(paper, "content_sections")
    if not sections:
        sections = _content_sections_v4(getattr(paper, "body", None), registry)
    abstracts = _abstract_sections_v4(paper)
    primary_abstract = next(
        (item for item in abstracts if item.get("is_primary")),
        abstracts[0] if abstracts else {},
    )

    table_records = _parse_result_list(paper, "table_records")
    figure_records = _parse_result_list(paper, "figure_records")

    if not table_records and not registry.tables:
        for table in _raw_list(getattr(paper, "tables", None)):
            registry.add_table(table)
    if not figure_records and not registry.figures:
        for figure in _raw_list(getattr(paper, "figures", None)):
            registry.add_figure(figure)

    references = _references_for_output_v4(paper)
    tables = [_table_record_v4(table) for table in (table_records or registry.tables)]
    figures = [
        _figure_record_v4(figure) for figure in (figure_records or registry.figures)
    ]
    contributors = _contributors_v4(paper)
    affiliations = _parse_result_list(paper, "affiliations")
    relations = _relations_v4(paper)
    coverage = _parse_result_dict(paper, "coverage")
    diagnostics = _diagnostics(paper, sections=sections, abstracts=abstracts)
    summary = _summary_v4(
        abstracts=abstracts,
        sections=sections,
        references=references,
        tables=tables,
        figures=figures,
        contributors=contributors,
        affiliations=affiliations,
        relations=relations,
        coverage=coverage,
    )
    diagnostics = _diagnostics_v4(
        diagnostics,
        paper=paper,
        summary=summary,
        relations=relations,
    )

    journal_title, alternate_journal_titles = _primary_with_alternates(
        getattr(paper, "journal_title", None)
    )
    publisher_name, alternate_publisher_names = _primary_with_alternates(
        getattr(paper, "publisher_name", None)
    )
    publisher_location, alternate_publisher_locations = _primary_with_alternates(
        getattr(paper, "publisher_location", None)
    )

    return {
        "schema_version": _SCHEMA_VERSION_V4,
        "has_data": True,
        "article": {
            "identifiers": _identifiers_v4(
                getattr(paper, "article_id", None), effective_pmc_id, paper
            ),
            "title": _title_v4(paper),
            "publication": {
                "journal": {
                    "title": journal_title,
                    "alternate_titles": alternate_journal_titles,
                    "ids": _as_dict(getattr(paper, "journal_id", None)),
                    "issn": _as_dict(getattr(paper, "issn", None)),
                },
                "publisher": {
                    "name": publisher_name,
                    "alternate_names": alternate_publisher_names,
                    "location": publisher_location,
                    "alternate_locations": alternate_publisher_locations,
                },
                "classification": {
                    "article_types": _as_list(getattr(paper, "article_types", None)),
                    "article_categories": _as_list(
                        getattr(paper, "article_categories", None)
                    ),
                    "subject_groups": _parse_result_list(paper, "subject_groups"),
                },
                "dates": _date_records_for_output_v4(paper),
                "issue": {
                    "volume": _as_string(getattr(paper, "volume", None)),
                    "issue": _as_string(getattr(paper, "issue", None)),
                    "first_page": _as_string(getattr(paper, "fpage", None)),
                    "last_page": _as_string(getattr(paper, "lpage", None)),
                    "elocation_id": _as_string(getattr(paper, "elocation_id", None)),
                },
                "conference": _as_dict(getattr(paper, "conference", None)),
            },
            "compliance": {
                "permissions": _as_dict(getattr(paper, "permissions", None)),
                "copyright": _as_string(getattr(paper, "copyright", None)),
                "license": _as_string(getattr(paper, "license", None)),
                "licenses": _parse_result_list(paper, "license_records"),
                "ethics": _as_dict(getattr(paper, "ethics", None)),
                "funding": _as_list(getattr(paper, "funding", None)),
            },
            "metadata": {
                "keywords": _as_list(getattr(paper, "keywords", None)),
                "keyword_groups": _parse_result_list(paper, "keyword_groups"),
                "counts": _as_dict(getattr(paper, "counts", None)),
                "self_uri": _as_list(getattr(paper, "self_uri", None)),
                "related_articles": _as_list(getattr(paper, "related_articles", None)),
                "custom_meta": _as_dict(getattr(paper, "custom_meta", None)),
            },
        },
        "contributors": {
            "people": contributors,
            "affiliations": affiliations,
            "author_notes": _as_dict(getattr(paper, "author_notes", None)),
            "non_author_contributors": _contributors(
                getattr(paper, "non_author_contributors", None)
            ),
        },
        "content": {
            "abstracts": abstracts,
            "primary_abstract": primary_abstract,
            "sections": sections,
            "appendices": _as_list(getattr(paper, "appendices", None)),
            "glossary": _as_list(getattr(paper, "glossary", None)),
            "footnotes": _as_string(getattr(paper, "footnote", None)),
            "acknowledgements": _as_list(getattr(paper, "acknowledgements", None)),
            "notes": _as_list(getattr(paper, "notes", None)),
        },
        "assets": {
            "references": references,
            "tables": tables,
            "figures": figures,
            "equations": _equations_v4(paper),
            "supplementary_material": _parse_result_list(paper, "supplementary_records")
            or _as_list(getattr(paper, "supplementary", None)),
        },
        "relations": relations,
        "quality": {
            "status": _quality_status(sections, diagnostics),
            "diagnostics": diagnostics,
            "summary": summary,
            "coverage": coverage or _empty_coverage(),
        },
        "provenance": {
            **_provenance(
                paper,
                include_processing_fields=include_processing_fields,
                source=source,
                xml_path=xml_path,
            ),
        },
    }


def _empty_output() -> ArticleOutput:
    data = {
        "schema_version": _SCHEMA_VERSION,
        "has_data": False,
        **_deepcopy_groups(),
        "provenance": {
            "pmcgrab_version": _pmcgrab_version(),
            "parse_timestamp": "",
            "source": "",
            "xml_source_path": "",
        },
    }
    return data


def _empty_output_v3() -> ArticleOutput:
    return {
        "schema_version": _SCHEMA_VERSION_V3,
        "has_data": False,
        "article": {
            "identifiers": _deepcopy_groups()["identifiers"],
            "title": _deepcopy_groups()["title"],
            "contributors": _deepcopy_groups()["contributors"],
            "publication": _deepcopy_groups()["publication"],
            "compliance": _deepcopy_groups()["compliance"],
            "metadata": _deepcopy_groups()["metadata"],
        },
        "content": {
            "abstracts": [],
            "primary_abstract": {},
            "sections": [],
            "appendices": [],
            "glossary": [],
            "footnotes": "",
            "acknowledgements": [],
            "notes": [],
        },
        "assets": {
            "references": [],
            "tables": [],
            "figures": [],
            "equations": {"records": [], "mathml": [], "tex": []},
            "supplementary_material": [],
        },
        "links": [],
        "quality": {
            "status": "empty",
            "diagnostics": [],
            "summary": {
                "abstract_count": 0,
                "section_count": 0,
                "reference_count": 0,
                "link_count": 0,
            },
        },
        "provenance": {
            "pmcgrab_version": _pmcgrab_version(),
            "parse_timestamp": "",
            "source": "",
            "xml_source_path": "",
        },
    }


def _empty_output_v4() -> ArticleOutput:
    return {
        "schema_version": _SCHEMA_VERSION_V4,
        "has_data": False,
        "article": {
            "identifiers": {
                **_deepcopy_groups()["identifiers"],
                "all": [],
            },
            "title": {**_deepcopy_groups()["title"], "records": []},
            "publication": _deepcopy_groups()["publication"],
            "compliance": {
                **_deepcopy_groups()["compliance"],
                "licenses": [],
            },
            "metadata": {
                **_deepcopy_groups()["metadata"],
                "keyword_groups": [],
            },
        },
        "contributors": {
            "people": [],
            "affiliations": [],
            "author_notes": {},
            "non_author_contributors": [],
        },
        "content": {
            "abstracts": [],
            "primary_abstract": {},
            "sections": [],
            "appendices": [],
            "glossary": [],
            "footnotes": "",
            "acknowledgements": [],
            "notes": [],
        },
        "assets": {
            "references": [],
            "tables": [],
            "figures": [],
            "equations": {"mathml": [], "tex": []},
            "supplementary_material": [],
        },
        "relations": [],
        "quality": {
            "status": "empty",
            "diagnostics": [],
            "summary": {
                "abstract_count": 0,
                "section_count": 0,
                "block_count": 0,
                "reference_count": 0,
                "table_count": 0,
                "figure_count": 0,
                "contributor_count": 0,
                "affiliation_count": 0,
                "relation_count": 0,
                "generic_fallback_count": 0,
                "duplicate_xml_id_count": 0,
            },
            "coverage": _empty_coverage(),
        },
        "provenance": {
            "pmcgrab_version": _pmcgrab_version(),
            "parse_timestamp": "",
            "source": "",
            "xml_source_path": "",
        },
    }


def _deepcopy_groups() -> ArticleOutput:
    """Copy nested schema defaults without importing copy for a tiny structure."""
    return cast(ArticleOutput, json.loads(json.dumps(_EMPTY_GROUPS)))


def _identifiers(article_id: Any, pmc_id: str | int | None) -> dict[str, Any]:
    ids = {str(k): _as_string(v) for k, v in _as_dict(article_id).items()}
    raw_pmc = _first_nonempty(ids.get("pmcid"), ids.get("pmc"), pmc_id)
    numeric_pmc = _numeric_pmc_id(raw_pmc)
    publisher_id = _first_nonempty(ids.get("publisher-id"), ids.get("publisher_id"))
    reserved = {"pmcid", "pmc", "pmid", "doi", "publisher-id", "publisher_id"}
    other = {key: value for key, value in ids.items() if key not in reserved}
    return {
        "pmc_id": numeric_pmc,
        "pmcid": f"PMC{numeric_pmc}" if numeric_pmc else "",
        "pmid": _as_string(ids.get("pmid")),
        "doi": _as_string(ids.get("doi")),
        "publisher_id": _as_string(publisher_id),
        "other": other,
    }


def _identifiers_v4(
    article_id: Any, pmc_id: str | int | None, paper: Paper
) -> dict[str, Any]:
    identifiers = _identifiers(article_id, pmc_id)
    identifiers["all"] = _parse_result_list(paper, "article_ids")
    return identifiers


def _title_v4(paper: Paper) -> dict[str, Any]:
    return {
        "main": _as_string(getattr(paper, "title", None)),
        "subtitle": _as_string(getattr(paper, "subtitle", None)),
        "translated": _as_list(getattr(paper, "translated_titles", None)),
        "records": _parse_result_list(paper, "title_records"),
    }


def _parse_result_list(paper: Paper, field: str) -> list[Any]:
    parse_result = getattr(paper, "parse_result", None)
    if parse_result is None:
        return []
    return _as_list(getattr(parse_result, field, None))


def _parse_result_dict(paper: Paper, field: str) -> dict[str, Any]:
    parse_result = getattr(paper, "parse_result", None)
    if parse_result is None:
        return {}
    return _as_dict(getattr(parse_result, field, None))


def _abstract_sections(value: Any) -> list[dict[str, Any]]:
    sections = []
    elements = _raw_list(value)
    for index, element in enumerate(elements, start=1):
        title = _as_string(getattr(element, "title", None))
        if not title:
            title = "Abstract" if index == 1 else f"Abstract Section {index}"
        blocks = _text_blocks_from_element(element)
        if not blocks:
            text = _as_string(element)
            if text:
                blocks = [{"type": "paragraph", "id": "", "text": text}]
        sections.append(
            {
                "id": _element_id(element),
                "title": title,
                "level": 0,
                "blocks": blocks,
                "children": [],
            }
        )
    return sections


def _abstract_sections_v3(paper: Paper) -> list[dict[str, Any]]:
    """Return all abstract records V3 knows about."""
    source_records = _as_list(getattr(paper, "all_abstracts", None))
    if source_records:
        return source_records

    primary = _abstract_sections(getattr(paper, "abstract", None))
    abstract_type = _as_string(getattr(paper, "abstract_type", None))
    for item in primary:
        item["kind"] = abstract_type or "primary"
        item["language"] = ""
        item["is_primary"] = True

    translated = []
    for index, item in enumerate(
        _as_list(getattr(paper, "translated_abstracts", None)), start=1
    ):
        if isinstance(item, dict):
            text = _as_string(item.get("text"))
            lang = _as_string(item.get("lang"))
        else:
            text = _as_string(item)
            lang = ""
        translated.append(
            {
                "id": f"translated_abstract_{index}",
                "title": "Translated Abstract",
                "kind": "translated",
                "language": lang,
                "is_primary": False,
                "level": 0,
                "blocks": (
                    [{"type": "paragraph", "id": "", "text": text}] if text else []
                ),
                "children": [],
            }
        )
    return primary + translated


def _abstract_sections_v4(paper: Paper) -> list[dict[str, Any]]:
    records = _parse_result_list(paper, "abstracts")
    if not records:
        records = _abstract_sections_v3(paper)
    enriched = []
    for index, record in enumerate(records, start=1):
        item = (
            dict(record) if isinstance(record, dict) else {"text": _as_string(record)}
        )
        item.setdefault("id", f"abstract_{index}")
        item.setdefault("type", "abstract")
        item.setdefault("title", "Abstract" if index == 1 else f"Abstract {index}")
        item.setdefault("kind", "primary" if index == 1 else "")
        item.setdefault("language", "")
        item.setdefault("is_primary", index == 1)
        item.setdefault("level", 0)
        item.setdefault("blocks", [])
        item.setdefault("children", [])
        item.setdefault("source", {})
        enriched.append(item)
    return enriched


def _content_sections_v4(
    value: Any,
    registry: _AssetRegistry,
    *,
    level: int = 1,
    section_path: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    untitled_counter = 1
    for ordinal, element in enumerate(_raw_list(value), start=1):
        if _is_section(element):
            title = _as_string(getattr(element, "title", None))
            if not title:
                title = f"Section {untitled_counter}"
                untitled_counter += 1
            sections.append(
                _section_record_v4(
                    element,
                    title,
                    level,
                    registry,
                    ordinal=ordinal,
                    section_path=section_path,
                )
            )
        else:
            block = _content_block_v4(
                element,
                registry,
                context="body",
                ordinal=ordinal,
            )
            if block is None:
                continue
            title = f"Section {untitled_counter}"
            sections.append(
                {
                    "id": _record_id(element, f"section_{ordinal}"),
                    "type": "section",
                    "title": title,
                    "level": level,
                    "section_path": [*section_path, title],
                    "text": block.get("text", ""),
                    "blocks": [block],
                    "children": [],
                    "source": _source_from_element(element, ordinal=ordinal),
                }
            )
            untitled_counter += 1
    return sections


def _section_record_v4(
    section: Any,
    title: str,
    level: int,
    registry: _AssetRegistry,
    *,
    ordinal: int,
    section_path: tuple[str, ...],
) -> dict[str, Any]:
    path = (*section_path, title)
    blocks: list[dict[str, Any]] = []
    children: list[dict[str, Any]] = []
    child_counter = 1
    for child_ordinal, child in enumerate(
        _raw_list(getattr(section, "children", None)), start=1
    ):
        if _is_section(child):
            child_title = _as_string(getattr(child, "title", None))
            if not child_title:
                child_title = f"Section {child_counter}"
                child_counter += 1
            children.append(
                _section_record_v4(
                    child,
                    child_title,
                    level + 1,
                    registry,
                    ordinal=child_ordinal,
                    section_path=path,
                )
            )
        else:
            block = _content_block_v4(
                child,
                registry,
                context="body",
                ordinal=child_ordinal,
            )
            if block is not None:
                blocks.append(block)
    return {
        "id": _record_id(section, f"section_{ordinal}"),
        "type": "section",
        "title": title,
        "level": level,
        "section_path": list(path),
        "text": _as_string(getattr(section, "get_clean_text", lambda: "")()),
        "blocks": blocks,
        "children": children,
        "source": _source_from_element(section, ordinal=ordinal),
    }


def _content_block_v4(
    element: Any,
    registry: _AssetRegistry,
    *,
    context: str,
    ordinal: int,
) -> dict[str, Any] | None:
    source = _source_from_element(element, ordinal=ordinal)
    if _is_paragraph(element):
        text = _as_string(getattr(element, "text", None) or element)
        if not text:
            return None
        text_with_refs = _as_string(getattr(element, "text_with_refs", text))
        return {
            "id": _record_id(element, f"{context}_paragraph_{ordinal}"),
            "type": "paragraph",
            "text": text,
            "text_with_refs": text_with_refs,
            "source": source,
        }
    if _is_table(element):
        target_id = registry.add_table(element)
        return {
            "id": f"{context}_table_ref_{ordinal}",
            "type": "table_ref",
            "target_type": "table",
            "target_id": target_id,
            "source": source,
        }
    if _is_figure(element):
        target_id = registry.add_figure(element)
        return {
            "id": f"{context}_figure_ref_{ordinal}",
            "type": "figure_ref",
            "target_type": "figure",
            "target_id": target_id,
            "source": source,
        }
    text = _as_string(element)
    if not text:
        return None
    return {
        "id": _record_id(element, f"{context}_block_{ordinal}"),
        "type": "text",
        "text": text,
        "source": source,
    }


def _content_sections(
    value: Any, registry: _AssetRegistry, *, level: int = 1
) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    untitled_counter = 1
    for element in _raw_list(value):
        if _is_section(element):
            title = _as_string(getattr(element, "title", None))
            if not title:
                title = f"Section {untitled_counter}"
                untitled_counter += 1
            sections.append(_section_record(element, title, level, registry))
        else:
            block = _content_block(element, registry)
            if block is None:
                continue
            sections.append(
                {
                    "id": _element_id(element),
                    "title": f"Section {untitled_counter}",
                    "level": level,
                    "blocks": [block],
                    "children": [],
                }
            )
            untitled_counter += 1
    return sections


def _section_record(
    section: Any, title: str, level: int, registry: _AssetRegistry
) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = []
    children: list[dict[str, Any]] = []
    child_counter = 1
    for child in _raw_list(getattr(section, "children", None)):
        if _is_section(child):
            child_title = _as_string(getattr(child, "title", None))
            if not child_title:
                child_title = f"Section {child_counter}"
                child_counter += 1
            children.append(_section_record(child, child_title, level + 1, registry))
        else:
            block = _content_block(child, registry)
            if block is not None:
                blocks.append(block)
    return {
        "id": _element_id(section),
        "title": title,
        "level": level,
        "blocks": blocks,
        "children": children,
    }


def _content_block(element: Any, registry: _AssetRegistry) -> dict[str, Any] | None:
    if _is_paragraph(element):
        text = _as_string(getattr(element, "text", None) or element)
        if not text:
            return None
        return {"type": "paragraph", "id": _element_id(element), "text": text}
    if _is_table(element):
        return {"type": "table_ref", "id": registry.add_table(element)}
    if _is_figure(element):
        return {"type": "figure_ref", "id": registry.add_figure(element)}
    text = _as_string(element)
    if not text:
        return None
    return {"type": "paragraph", "id": _element_id(element), "text": text}


def _text_blocks_from_element(element: Any) -> list[dict[str, Any]]:
    if _is_section(element):
        blocks = []
        for child in _raw_list(getattr(element, "children", None)):
            if _is_section(child):
                text = _as_string(getattr(child, "text", None) or child)
            else:
                text = _as_string(getattr(child, "text", None) or child)
            if text:
                blocks.append(
                    {"type": "paragraph", "id": _element_id(child), "text": text}
                )
        return blocks
    text = _as_string(getattr(element, "text", None) or element)
    return (
        [{"type": "paragraph", "id": _element_id(element), "text": text}]
        if text
        else []
    )


class _AssetRegistry:
    """Collect content assets once while assigning stable local IDs."""

    def __init__(self) -> None:
        self.tables: list[dict[str, Any]] = []
        self.figures: list[dict[str, Any]] = []
        self._table_object_ids: dict[int, str] = {}
        self._figure_object_ids: dict[int, str] = {}
        self._table_keys: dict[str, str] = {}
        self._figure_keys: dict[str, str] = {}

    def add_table(self, table: Any) -> str:
        object_key = id(table)
        if object_key in self._table_object_ids:
            return self._table_object_ids[object_key]
        record = _table_record(table, len(self.tables) + 1)
        table_id = _as_string(record.get("id")) or f"table_{len(self.tables) + 1}"
        record["id"] = table_id
        dedupe_key = _dedupe_key(record)
        if dedupe_key in self._table_keys:
            existing_id = self._table_keys[dedupe_key]
            self._table_object_ids[object_key] = existing_id
            return existing_id
        self.tables.append(record)
        self._table_keys[dedupe_key] = table_id
        self._table_object_ids[object_key] = table_id
        return table_id

    def add_figure(self, figure: Any) -> str:
        object_key = id(figure)
        if object_key in self._figure_object_ids:
            return self._figure_object_ids[object_key]
        record = _figure_record(figure, len(self.figures) + 1)
        figure_id = _as_string(record.get("id")) or f"figure_{len(self.figures) + 1}"
        record["id"] = figure_id
        dedupe_key = _dedupe_key(record)
        if dedupe_key in self._figure_keys:
            existing_id = self._figure_keys[dedupe_key]
            self._figure_object_ids[object_key] = existing_id
            return existing_id
        self.figures.append(record)
        self._figure_keys[dedupe_key] = figure_id
        self._figure_object_ids[object_key] = figure_id
        return figure_id


def _table_record(table: Any, index: int) -> dict[str, Any]:
    if hasattr(table, "table_dict") and table.table_dict is not None:
        record = normalize_value(table.table_dict)
    else:
        record = {"records": normalize_value(table)}
    if not isinstance(record, dict):
        record = {"records": record}
    record.setdefault("id", _element_id(table) or f"table_{index}")
    record.setdefault("label", _as_string(getattr(table, "label", None)))
    record.setdefault("caption", _as_string(getattr(table, "caption", None)))
    record.setdefault("source", _source_from_element(table, ordinal=index))
    return record


def _figure_record(figure: Any, index: int) -> dict[str, Any]:
    raw = getattr(figure, "fig_dict", figure)
    raw = normalize_value(raw)
    raw = raw if isinstance(raw, dict) else {"caption": _as_string(raw)}
    graphics = _as_list(_first_nonempty(raw.get("all_graphics"), raw.get("graphics")))
    primary_link = _as_string(_first_nonempty(raw.get("link"), raw.get("Link")))
    if not graphics and primary_link:
        graphics = [primary_link]
    if not primary_link and graphics:
        primary_link = _as_string(graphics[0])
    alternate_links = [_as_string(link) for link in graphics if link != primary_link]
    return {
        "id": _as_string(raw.get("id")) or _element_id(figure) or f"figure_{index}",
        "label": _as_string(_first_nonempty(raw.get("label"), raw.get("Label"))),
        "caption": _as_string(_first_nonempty(raw.get("caption"), raw.get("Caption"))),
        "link": primary_link,
        "alternate_links": alternate_links,
        "alt_text": _as_string(raw.get("alt_text")),
        "long_desc": _as_string(raw.get("long_desc")),
        "attrib": _as_string(raw.get("attrib")),
        "permissions": _as_dict(raw.get("permissions")),
        "object_id": _as_string(raw.get("object_id")),
        "source": _source_from_element(figure, ordinal=index),
    }


def _table_record_v3(record: dict[str, Any]) -> dict[str, Any]:
    table = dict(record)
    parsed = bool(table.get("rows") or table.get("records") or table.get("columns"))
    table.setdefault("parse_status", "parsed" if parsed else "fallback")
    table.setdefault("source", {})
    table.setdefault("raw_text", "" if parsed else _as_string(table))
    return table


def _figure_record_v3(record: dict[str, Any]) -> dict[str, Any]:
    figure = dict(record)
    figure.setdefault("parse_status", "parsed" if figure.get("caption") else "partial")
    figure.setdefault("source", {})
    figure.setdefault("raw_text", "")
    return figure


def _table_record_v4(record: dict[str, Any]) -> dict[str, Any]:
    table = _table_record_v3(record)
    table.setdefault("type", "table")
    table.setdefault("source", {})
    table.setdefault("footnotes", [])
    raw_text = table.pop("raw_text", "")
    table.setdefault("text_fallback", raw_text)
    return table


def _figure_record_v4(record: dict[str, Any]) -> dict[str, Any]:
    figure = _figure_record_v3(record)
    figure.setdefault("type", "figure")
    figure.setdefault("source", {})
    figure.setdefault("alternate_links", [])
    raw_text = figure.pop("raw_text", "")
    figure.setdefault("text_fallback", raw_text)
    figure.setdefault("local_path", "")
    figure.setdefault("download_status", "not_attempted")
    figure.setdefault("download_source", "")
    graphics = figure.get("graphics")
    if isinstance(graphics, list):
        for graphic in graphics:
            if isinstance(graphic, dict):
                graphic.setdefault("local_path", "")
                graphic.setdefault("download_status", "not_attempted")
    return figure


def _references_for_output(paper: Paper) -> list[Any]:
    references = _as_list(getattr(paper, "all_references", None))
    if references:
        return references
    citations = _as_list(getattr(paper, "citations", None))
    return [
        {
            "id": f"ref_{index}",
            "label": "",
            "citation": citation,
            "source": {"tag": "", "ordinal": index},
        }
        for index, citation in enumerate(citations, start=1)
    ]


def _references_for_output_v4(paper: Paper) -> list[Any]:
    references = _parse_result_list(paper, "references")
    if not references:
        references = _references_for_output(paper)
    enriched = []
    for index, reference in enumerate(references, start=1):
        item = (
            dict(reference) if isinstance(reference, dict) else {"citation": reference}
        )
        item.setdefault("id", f"ref_{index}")
        item.setdefault("type", "reference")
        item.setdefault("label", "")
        item.setdefault("citation", {})
        citation_text = _as_string(item.pop("citation_raw", ""))
        item.setdefault(
            "citation_text", citation_text or _as_string(item.get("citation"))
        )
        item.setdefault(
            "source",
            {"jats_tag": "ref", "attrs": {}, "path": "", "ordinal": index},
        )
        enriched.append(item)
    return enriched


def _contributors_v4(paper: Paper) -> list[Any]:
    contributors = _parse_result_list(paper, "contributors")
    if contributors:
        return contributors
    authors = _as_list(getattr(paper, "authors", None))
    result = []
    for index, author in enumerate(authors, start=1):
        if isinstance(author, dict):
            given = _as_string(author.get("First_Name"))
            surname = _as_string(author.get("Last_Name"))
            contributor = {
                "id": f"contrib_{index}",
                "type": _as_string(author.get("Contributor_Type")) or "author",
                "display_name": " ".join(part for part in (given, surname) if part),
                "name": {
                    "given": given,
                    "surname": surname,
                    "prefix": "",
                    "suffix": "",
                },
                "emails": [
                    email
                    for email in [_as_string(author.get("Email_Address"))]
                    if email
                ],
                "ids": [
                    {"type": key.lower(), "value": _as_string(author.get(key))}
                    for key in ("ORCID", "ISNI")
                    if _as_string(author.get(key))
                ],
                "roles": [],
                "degrees": [],
                "affiliation_ids": [],
                "affiliations": _as_list(author.get("Affiliations")),
                "corresponding": False,
                "equal_contrib": bool(author.get("Equal_Contrib")),
                "source": {},
            }
        else:
            contributor = {
                "id": f"contrib_{index}",
                "type": "author",
                "display_name": _as_string(author),
                "source": {},
            }
        result.append(contributor)
    return result


def _relations_v4(paper: Paper) -> list[dict[str, Any]]:
    relations: list[dict[str, Any]] = []
    for link in _as_list(getattr(paper, "reference_links", None)):
        if not isinstance(link, dict):
            continue
        relations.append(
            {
                "id": link.get("id") or f"relation_{len(relations) + 1}",
                "type": "xref",
                "subtype": link.get("type", ""),
                "source": {
                    **_as_dict(link.get("source")),
                    "char_start": link.get("char_start"),
                    "char_end": link.get("char_end"),
                },
                "target_type": link.get("type", ""),
                "target_ids": _as_list(link.get("target_ids")),
                "inline_text": _as_string(link.get("text")),
                "resolved": bool(link.get("resolved")),
                "jats_ref_type": _as_string(link.get("jats_ref_type")),
            }
        )
    for link in _parse_result_list(paper, "contributor_affiliation_links"):
        if not isinstance(link, dict):
            continue
        relations.append(
            {
                "id": link.get("id") or f"relation_{len(relations) + 1}",
                "type": "contributor_affiliation",
                "source": {
                    "id": link.get("source_id", ""),
                    "type": link.get("source_type", "contributor"),
                },
                "target_type": link.get("target_type", "affiliation"),
                "target_ids": [_as_string(link.get("target_id"))],
                "inline_text": "",
                "resolved": bool(link.get("resolved")),
            }
        )
    return relations


def _equations_v4(paper: Paper) -> dict[str, list[Any]]:
    records = _parse_result_list(paper, "equation_records")
    if records:
        return {
            "records": records,
            "mathml": [
                record.get("mathml")
                for record in records
                if isinstance(record, dict) and record.get("mathml")
            ],
            "tex": [
                record.get("tex")
                for record in records
                if isinstance(record, dict) and record.get("tex")
            ],
        }
    legacy_mathml = []
    for value in _as_list(getattr(paper, "equations", None)):
        structured = _structured_xml_string(value)
        if structured:
            legacy_mathml.append(structured)
    return {
        "records": [],
        "mathml": legacy_mathml,
        "tex": _as_list(getattr(paper, "tex_equations", None)),
    }


def _date_records_for_output(paper: Paper) -> dict[str, Any]:
    date_records = _parse_result_dict(paper, "date_records") or _as_dict(
        getattr(paper, "date_records", None)
    )
    if date_records:
        return date_records
    return {
        "published": _date_values_to_records(getattr(paper, "published_date", None)),
        "history": _date_values_to_records(getattr(paper, "history_dates", None)),
        "version_history": _as_list(getattr(paper, "version_history", None)),
    }


def _date_records_for_output_v4(paper: Paper) -> dict[str, Any]:
    """Return V4 date records with readable source text field names."""
    return cast(
        dict[str, Any],
        _rename_key_recursive(_date_records_for_output(paper), "raw", "source_text"),
    )


def _date_values_to_records(value: Any) -> dict[str, Any]:
    records: dict[str, Any] = {}
    for key, item in _as_dict(value).items():
        text = _as_string(item)
        records[str(key)] = {
            "raw": text,
            "date": text,
            "precision": "day" if text else "unknown",
            "year": text[:4] if len(text) >= 4 else "",
            "month": text[5:7] if len(text) >= 7 else "",
            "day": text[8:10] if len(text) >= 10 else "",
        }
    return records


def _rename_key_recursive(value: Any, old_key: str, new_key: str) -> Any:
    if isinstance(value, dict):
        renamed = {}
        for key, item in value.items():
            target_key = new_key if key == old_key else key
            renamed[target_key] = _rename_key_recursive(item, old_key, new_key)
        return renamed
    if isinstance(value, list):
        return [_rename_key_recursive(item, old_key, new_key) for item in value]
    return value


def _diagnostics(
    paper: Paper, *, sections: list[dict[str, Any]], abstracts: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    diagnostics = _as_list(getattr(paper, "diagnostics", None))
    existing_codes = {
        item.get("code") for item in diagnostics if isinstance(item, dict)
    }
    if not sections and "missing_body" not in existing_codes:
        diagnostics.append(
            {
                "severity": "warning",
                "code": "missing_body",
                "message": "No body sections were emitted.",
            }
        )
    if not abstracts and "missing_abstract" not in existing_codes:
        diagnostics.append(
            {
                "severity": "warning",
                "code": "missing_abstract",
                "message": "No abstract records were emitted.",
            }
        )
    return diagnostics


def _quality_status(
    sections: list[dict[str, Any]], diagnostics: list[dict[str, Any]]
) -> str:
    if not sections:
        return "partial"
    if any(item.get("severity") == "error" for item in diagnostics):
        return "partial"
    return "complete"


def _summary_v4(
    *,
    abstracts: list[dict[str, Any]],
    sections: list[dict[str, Any]],
    references: list[Any],
    tables: list[Any],
    figures: list[Any],
    contributors: list[Any],
    affiliations: list[Any],
    relations: list[Any],
    coverage: dict[str, Any] | None = None,
) -> dict[str, int]:
    coverage = coverage or {}
    return {
        "abstract_count": len(abstracts),
        "section_count": _count_sections(sections),
        "block_count": _count_blocks(sections),
        "reference_count": len(references),
        "table_count": len(tables),
        "figure_count": len(figures),
        "contributor_count": len(contributors),
        "affiliation_count": len(affiliations),
        "relation_count": len(relations),
        "unresolved_relation_count": sum(
            1
            for relation in relations
            if isinstance(relation, dict) and not relation.get("resolved", True)
        ),
        "generic_fallback_count": _as_int(coverage.get("generic_fallback_count")) or 0,
        "duplicate_xml_id_count": _as_int(coverage.get("duplicate_xml_id_count")) or 0,
    }


def _count_sections(sections: list[dict[str, Any]]) -> int:
    return sum(
        1 + _count_sections(_as_list(section.get("children")))
        for section in sections
        if isinstance(section, dict)
    )


def _count_blocks(sections: list[dict[str, Any]]) -> int:
    total = 0
    for section in sections:
        total += sum(
            _count_block_tree(block) for block in _as_list(section.get("blocks"))
        )
        total += _count_blocks(_as_list(section.get("children")))
    return total


def _count_block_tree(block: Any) -> int:
    if not isinstance(block, dict):
        return 0
    total = 1
    for key in ("blocks", "children", "items", "definition_blocks"):
        total += sum(_count_block_tree(child) for child in _as_list(block.get(key)))
    return total


def _diagnostics_v4(
    diagnostics: list[dict[str, Any]],
    *,
    paper: Paper,
    summary: dict[str, int],
    relations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result = list(diagnostics)
    existing_codes = {item.get("code") for item in result if isinstance(item, dict)}
    for relation in relations:
        if relation.get("resolved", True):
            continue
        result.append(
            {
                "severity": "warning",
                "code": "unresolved_relation",
                "message": (
                    f"Unresolved {relation.get('type', 'relation')} "
                    f"to {relation.get('target_ids', [])}."
                ),
            }
        )
    counts = _as_dict(getattr(paper, "counts", None))
    for expected_key, actual_key in (
        ("ref_count", "reference_count"),
        ("fig_count", "figure_count"),
        ("table_count", "table_count"),
    ):
        expected = _as_int(counts.get(expected_key))
        if expected is None:
            continue
        actual = summary.get(actual_key, 0)
        code = f"{expected_key}_mismatch"
        if expected != actual and code not in existing_codes:
            result.append(
                {
                    "severity": "warning",
                    "code": code,
                    "message": (
                        f"XML declares {expected_key}={expected}, "
                        f"but V4 emitted {actual_key}={actual}."
                    ),
                }
            )
    return result


def _empty_coverage() -> dict[str, Any]:
    return {
        "source_text_char_count": 0,
        "emitted_text_char_count": 0,
        "represented_source_count": 0,
        "generic_fallback_count": 0,
        "unrepresented_text_count": 0,
        "unrepresented_text_char_count": 0,
        "duplicate_xml_id_count": 0,
        "duplicate_xml_ids": [],
    }


def _dedupe_key(record: dict[str, Any]) -> str:
    return json.dumps(normalize_value(record), sort_keys=True, default=str)


def _provenance(
    paper: Paper,
    *,
    include_processing_fields: bool,
    source: str | None,
    xml_path: str | None,
) -> dict[str, str]:
    parse_timestamp = _now_iso() if include_processing_fields else ""
    if not parse_timestamp:
        parse_timestamp = _as_string(getattr(paper, "last_updated", None))
    return {
        "pmcgrab_version": _pmcgrab_version(),
        "parse_timestamp": parse_timestamp,
        "source": _as_string(source),
        "xml_source_path": _as_string(xml_path),
    }


def _contributors(value: Any) -> list[Any]:
    if isinstance(value, str):
        return []
    return _as_list(value)


def _as_string(value: Any) -> str:
    if _is_missing(value):
        return ""
    return str(value)


def _as_int(value: Any) -> int | None:
    try:
        if _is_missing(value) or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_dict(value: Any) -> dict[Any, Any]:
    if _is_missing(value) or not isinstance(value, dict):
        return {}
    return value


def _as_list(value: Any) -> list[Any]:
    if _is_missing(value):
        return []
    normalized = normalize_value(value)
    if isinstance(normalized, list):
        return normalized
    if isinstance(normalized, tuple):
        return list(normalized)
    return [normalized]


def _raw_list(value: Any) -> list[Any]:
    if _is_missing(value):
        return []
    if isinstance(value, list | tuple):
        return list(value)
    return [value]


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    return (
        isinstance(value, str) and value.startswith("No ") and value.endswith("found.")
    )


def _first_nonempty(*values: Any) -> Any:
    for value in values:
        if not _is_missing(value) and value not in ("", [], {}):
            return value
    return ""


def _primary_with_alternates(value: Any) -> tuple[str, list[str]]:
    values = [_as_string(item) for item in _raw_list(value) if not _is_missing(item)]
    values = [item for item in values if item]
    if not values:
        return "", []
    return values[0], values[1:]


def _numeric_pmc_id(value: Any) -> str:
    text = _as_string(value)
    if text.lower().startswith("pmc"):
        return text[3:]
    return text


def _element_id(element: Any) -> str:
    direct_id = getattr(element, "id", None)
    if direct_id:
        return str(direct_id)
    table_id = getattr(element, "table_id", None)
    if table_id:
        return str(table_id)
    root = getattr(element, "root", None)
    if root is not None and hasattr(root, "get"):
        return _as_string(root.get("id"))
    return ""


def _record_id(element: Any, fallback: str) -> str:
    return _element_id(element) or fallback


def _source_from_element(element: Any, *, ordinal: int | None = None) -> dict[str, Any]:
    root = getattr(element, "root", None)
    if root is None and isinstance(element, _ET._Element):
        root = element
    if root is None:
        source: dict[str, Any] = {}
        if ordinal is not None:
            source["ordinal"] = ordinal
        return source
    try:
        path = root.getroottree().getpath(root)
    except Exception:
        path = ""
    source = {
        "jats_tag": _xml_name(getattr(root, "tag", "")),
        "attrs": _xml_attrs(root),
        "path": path,
    }
    if ordinal is not None:
        source["ordinal"] = ordinal
    return source


def _xml_attrs(element: Any) -> dict[str, str]:
    attrs = getattr(element, "attrib", {})
    return {_xml_name(key): str(value) for key, value in attrs.items()}


def _structured_xml_string(value: Any) -> dict[str, Any]:
    text = _as_string(value).strip()
    if not text:
        return {}
    try:
        root = _ET.fromstring(text.encode())
    except Exception:
        return {"text": text}
    return _structured_xml_element(root)


def _structured_xml_element(element: Any) -> dict[str, Any]:
    return {
        "tag": _xml_name(getattr(element, "tag", "")),
        "attrs": _xml_attrs(element),
        "text": " ".join(str(getattr(element, "text", "") or "").split()),
        "children": [_structured_xml_element(child) for child in list(element)],
    }


def _xml_name(value: Any) -> str:
    text = str(value)
    if text.startswith("{") and "}" in text:
        uri, local = text[1:].split("}", 1)
        if uri == "http://www.w3.org/XML/1998/namespace":
            return f"xml:{local}"
        if uri == "http://www.w3.org/1999/xlink":
            return f"xlink:{local}"
        return local
    return text


def _is_section(value: Any) -> bool:
    return value.__class__.__name__ == "TextSection" or hasattr(value, "children")


def _is_paragraph(value: Any) -> bool:
    return type(value).__name__ == "TextParagraph"


def _is_table(value: Any) -> bool:
    return value.__class__.__name__ == "TextTable" or hasattr(value, "table_dict")


def _is_figure(value: Any) -> bool:
    return value.__class__.__name__ == "TextFigure" or hasattr(value, "fig_dict")


def _now_iso() -> str:
    utc = getattr(_dt, "UTC", _dt.timezone.utc)
    return _dt.datetime.now(utc).isoformat()


def _pmcgrab_version() -> str:
    from pmcgrab import __version__

    return __version__
