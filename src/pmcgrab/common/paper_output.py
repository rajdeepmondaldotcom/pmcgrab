from __future__ import annotations

"""Canonical JSON output schema for parsed PMC articles."""

import datetime as _dt
import json
from typing import TYPE_CHECKING, Any, cast

from pmcgrab.common.serialization import normalize_value

if TYPE_CHECKING:
    from pmcgrab.model import Paper

ArticleOutput = dict[str, Any]

_SCHEMA_VERSION = 2
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
) -> ArticleOutput | None:
    """Return the public v2 article dictionary for a parsed paper.

    ``Paper.to_dict()``, application processing helpers, and CLI output share
    this function so the JSON contract has one owner. The schema intentionally
    stores article text once, under ``content``.
    """
    if not paper.has_data:
        if require_body:
            return None
        return cast(ArticleOutput, normalize_value(_empty_output()))

    registry = _AssetRegistry()
    data = _article_output(
        paper,
        pmc_id=pmc_id,
        registry=registry,
        include_processing_fields=include_processing_fields,
        source=source,
        xml_path=xml_path,
    )
    if require_body and not data["content"]["sections"]:
        return None
    return cast(ArticleOutput, normalize_value(data))


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
