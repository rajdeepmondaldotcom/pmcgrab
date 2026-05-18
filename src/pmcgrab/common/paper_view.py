from __future__ import annotations

"""Clean, reader-focused paper JSON projection.

The canonical V4 output is intentionally loss-aware and traceable.  This module
projects that rich representation into the default high signal-to-noise JSON:
the paper text plus the paper's figures/images and tables.
"""

from pathlib import Path
from typing import Any, cast

from pmcgrab.common.serialization import normalize_value

PAPER_SCHEMA = "pmcgrab.paper.v1"


def to_paper_output(article: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return the clean paper view for a full article output dictionary."""
    if article is None:
        return None
    if article.get("schema") == PAPER_SCHEMA:
        return article

    if not article.get("has_data"):
        return cast(
            dict[str, Any],
            normalize_value(
                {
                    "schema": PAPER_SCHEMA,
                    "has_data": False,
                    "identifiers": _identifiers(article),
                    "paper": {"title": "", "abstract": [], "body": []},
                    "assets": {"images": [], "tables": []},
                }
            ),
        )

    content = _dict(article.get("content"))
    assets = _dict(article.get("assets"))
    result = {
        "schema": PAPER_SCHEMA,
        "has_data": True,
        "identifiers": _identifiers(article),
        "paper": {
            "title": _title(article),
            "abstract": [
                _clean_abstract(item)
                for item in _list(content.get("abstracts"))
                if isinstance(item, dict)
            ],
            "body": [
                _clean_section(item)
                for item in _list(content.get("sections"))
                if isinstance(item, dict)
            ],
        },
        "assets": {
            "images": [
                _clean_image(item)
                for item in _list(assets.get("figures"))
                if isinstance(item, dict)
            ],
            "tables": [
                _clean_table(item)
                for item in _list(assets.get("tables"))
                if isinstance(item, dict)
            ],
        },
    }
    return cast(dict[str, Any], normalize_value(result))


def _identifiers(article: dict[str, Any]) -> dict[str, str]:
    article_group = _dict(article.get("article"))
    raw_ids = _dict(article_group.get("identifiers") or article.get("identifiers"))
    return {
        "pmcid": _str(raw_ids.get("pmcid")),
        "pmid": _str(raw_ids.get("pmid")),
        "doi": _str(raw_ids.get("doi")),
    }


def _title(article: dict[str, Any]) -> str:
    article_group = _dict(article.get("article"))
    title = _dict(article_group.get("title") or article.get("title"))
    return _str(title.get("main"))


def _clean_abstract(record: dict[str, Any]) -> dict[str, Any]:
    clean = {
        "id": _str(record.get("id")),
        "title": _str(record.get("title")) or "Abstract",
        "kind": _str(record.get("kind")),
        "content": _clean_blocks(record.get("blocks")),
        "sections": [
            _clean_section(item)
            for item in _list(record.get("children"))
            if isinstance(item, dict)
        ],
    }
    if not clean["content"] and not clean["sections"]:
        text = _str(record.get("text"))
        if text:
            clean["content"] = [{"type": "paragraph", "text": text}]
    return _compact(clean, keep_empty={"content", "sections"})


def _clean_section(section: dict[str, Any]) -> dict[str, Any]:
    clean = {
        "id": _str(section.get("id")),
        "title": _str(section.get("title")),
        "content": _clean_blocks(section.get("blocks")),
        "sections": [
            _clean_section(item)
            for item in _list(section.get("children"))
            if isinstance(item, dict)
        ],
    }
    if not clean["content"] and not clean["sections"]:
        text = _str(section.get("text"))
        if text:
            clean["content"] = [{"type": "paragraph", "text": text}]
    return _compact(clean, keep_empty={"content", "sections"})


def _clean_blocks(value: Any) -> list[dict[str, Any]]:
    return [_clean_block(item) for item in _list(value) if isinstance(item, dict)]


def _clean_block(block: dict[str, Any]) -> dict[str, Any]:
    block_type = _str(block.get("type")) or "text"
    if block_type == "paragraph":
        return _compact(
            {
                "id": _str(block.get("id")),
                "type": "paragraph",
                "text": _str(block.get("text")),
            }
        )
    if block_type == "list":
        return _compact(
            {
                "id": _str(block.get("id")),
                "type": "list",
                "list_type": _str(block.get("list_type")),
                "items": [
                    _clean_list_item(item)
                    for item in _list(block.get("items"))
                    if isinstance(item, dict)
                ],
                "text": _str(block.get("text")) if not block.get("items") else "",
            }
        )
    if block_type == "def_list":
        return _compact(
            {
                "id": _str(block.get("id")),
                "type": "definition_list",
                "title": _str(block.get("title")),
                "items": [
                    _clean_def_item(item)
                    for item in _list(block.get("items"))
                    if isinstance(item, dict)
                ],
            }
        )
    if block_type == "formula":
        return _compact(
            {
                "id": _str(block.get("id")),
                "type": "formula",
                "label": _str(block.get("label")),
                "text": _str(block.get("text")),
                "tex": _str(block.get("tex")),
                "display": block.get("display"),
                "mathml": block.get("mathml") or {},
            }
        )
    if block_type in {"figure_ref", "table_ref", "supplementary_ref"}:
        return _compact(
            {
                "id": _str(block.get("id")),
                "type": block_type,
                "target_id": _str(block.get("target_id")),
                "label": _str(block.get("label")),
            }
        )
    if block_type in {"quote", "statement", "boxed_text"}:
        return _clean_container_block(block, block_type)
    if block_type in {"preformat", "code"}:
        return _compact(
            {
                "id": _str(block.get("id")),
                "type": block_type,
                "language": _str(block.get("language")),
                "text": _str(block.get("text")),
            }
        )
    if block_type == "verse":
        lines = [
            _str(item.get("text"))
            for item in _list(block.get("lines"))
            if isinstance(item, dict) and _str(item.get("text"))
        ]
        return _compact(
            {
                "id": _str(block.get("id")),
                "type": "verse",
                "text": "\n".join(lines) or _str(block.get("text")),
            }
        )
    if block_type == "speech":
        return _compact(
            {
                "id": _str(block.get("id")),
                "type": "speech",
                "speaker": _str(block.get("speaker")),
                "content": _clean_blocks(block.get("blocks")),
                "text": _str(block.get("text")) if not block.get("blocks") else "",
            }
        )
    if block_type == "unknown_block":
        return _compact(
            {
                "id": _str(block.get("id")),
                "type": "unknown_block",
                "jats_tag": _str(block.get("jats_tag")),
                "title": _str(block.get("title")),
                "label": _str(block.get("label")),
                "text": _str(block.get("text")),
                "children": [
                    _clean_generic_child(item)
                    for item in _list(block.get("children"))
                    if isinstance(item, dict)
                ],
            }
        )
    return _clean_container_block(block, block_type)


def _clean_container_block(block: dict[str, Any], block_type: str) -> dict[str, Any]:
    children = _clean_blocks(block.get("blocks"))
    return _compact(
        {
            "id": _str(block.get("id")),
            "type": block_type,
            "title": _str(block.get("title")),
            "label": _str(block.get("label")),
            "caption": _str(block.get("caption")),
            "content": children,
            "text": _str(block.get("text")) if not children else "",
        }
    )


def _clean_list_item(item: dict[str, Any]) -> dict[str, Any]:
    blocks = _clean_blocks(item.get("blocks"))
    return _compact(
        {
            "label": _str(item.get("label")),
            "content": blocks,
            "text": _str(item.get("text")) if not blocks else "",
        }
    )


def _clean_def_item(item: dict[str, Any]) -> dict[str, Any]:
    blocks = _clean_blocks(item.get("definition_blocks"))
    return _compact(
        {
            "term": _str(item.get("term")),
            "definition": _str(item.get("definition")) if not blocks else "",
            "content": blocks,
        }
    )


def _clean_generic_child(item: dict[str, Any]) -> dict[str, Any]:
    return _compact(
        {
            "type": _str(item.get("jats_tag") or item.get("type")),
            "text": _str(item.get("text")),
            "children": [
                _clean_generic_child(child)
                for child in _list(item.get("children"))
                if isinstance(child, dict)
            ],
        }
    )


def _clean_image(figure: dict[str, Any]) -> dict[str, Any]:
    files = _image_files(figure)
    return _compact(
        {
            "id": _str(figure.get("id")),
            "label": _str(figure.get("label")),
            "caption": _str(figure.get("caption")),
            "alt_text": _str(figure.get("alt_text")),
            "long_desc": _str(figure.get("long_desc")),
            "files": files,
        },
        keep_empty={"files"},
    )


def _image_files(figure: dict[str, Any]) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    graphics = [
        item for item in _list(figure.get("graphics")) if isinstance(item, dict)
    ]
    if graphics:
        for graphic in graphics:
            _append_image_file(
                files,
                seen,
                href=_str(graphic.get("href")),
                local_path=_str(graphic.get("local_path")),
                status=_str(graphic.get("download_status")),
                mime_type=_str(graphic.get("mime_type")),
                content_type=_str(graphic.get("content_type")),
            )
        return files

    candidates = [_str(figure.get("link"))]
    candidates.extend(_str(item) for item in _list(figure.get("alternate_links")))
    figure_path = _str(figure.get("local_path"))
    figure_status = _str(figure.get("download_status")) or "not_attempted"
    for index, href in enumerate([item for item in candidates if item]):
        local_path = (
            figure_path
            if index == 0 or Path(figure_path).name == Path(href).name
            else ""
        )
        _append_image_file(
            files,
            seen,
            href=href,
            local_path=local_path,
            status=figure_status if local_path or index == 0 else "not_attempted",
            mime_type="",
            content_type="",
        )
    if not files and figure_path:
        _append_image_file(
            files,
            seen,
            href="",
            local_path=figure_path,
            status=figure_status,
            mime_type="",
            content_type="",
        )
    return files


def _append_image_file(
    files: list[dict[str, Any]],
    seen: set[tuple[str, str]],
    *,
    href: str,
    local_path: str,
    status: str,
    mime_type: str,
    content_type: str,
) -> None:
    key = (href, local_path)
    if key in seen or (not href and not local_path):
        return
    seen.add(key)
    files.append(
        _compact(
            {
                "href": href,
                "local_path": local_path,
                "status": status or "not_attempted",
                "mime_type": mime_type,
                "content_type": content_type,
            }
        )
    )


def _clean_table(table: dict[str, Any]) -> dict[str, Any]:
    columns = [_str(item) for item in _list(table.get("columns")) if _str(item)]
    if not columns:
        columns = _columns_from_header_rows(table.get("header_rows"))
    rows = _table_rows(table, columns)
    return _compact(
        {
            "id": _str(table.get("id")),
            "label": _str(table.get("label")),
            "caption": _str(table.get("caption")),
            "columns": columns,
            "rows": rows,
            "footnotes": _table_footnotes(table.get("footnotes")),
        },
        keep_empty={"columns", "rows", "footnotes"},
    )


def _columns_from_header_rows(value: Any) -> list[str]:
    rows = _list(value)
    if not rows or not isinstance(rows[0], dict):
        return []
    return [
        _str(cell.get("text"))
        for cell in _list(rows[0].get("cells"))
        if isinstance(cell, dict) and _str(cell.get("text"))
    ]


def _table_rows(table: dict[str, Any], columns: list[str]) -> list[Any]:
    records = _list(table.get("records"))
    if records:
        return records
    rows = _list(table.get("rows"))
    clean_rows: list[Any] = []
    for row in rows:
        if isinstance(row, dict):
            cells = [
                _str(cell.get("text"))
                for cell in _list(row.get("cells"))
                if isinstance(cell, dict)
            ]
            clean_rows.append(
                dict(zip(columns, cells, strict=False)) if columns else cells
            )
        elif isinstance(row, list):
            clean_rows.append(dict(zip(columns, row, strict=False)) if columns else row)
        else:
            text = _str(row)
            if text:
                clean_rows.append(text)
    return clean_rows


def _table_footnotes(value: Any) -> list[dict[str, str]]:
    footnotes = []
    for item in _list(value):
        if isinstance(item, dict):
            text = _str(item.get("text"))
            if text:
                footnotes.append(
                    _compact(
                        {
                            "id": _str(item.get("id")),
                            "label": _str(item.get("label")),
                            "text": text,
                        }
                    )
                )
    return footnotes


def _compact(
    value: dict[str, Any], *, keep_empty: set[str] | None = None
) -> dict[str, Any]:
    keep_empty = keep_empty or set()
    result: dict[str, Any] = {}
    for key, item in value.items():
        if key in keep_empty:
            result[key] = item
        elif _is_empty(item):
            continue
        else:
            result[key] = item
    return result


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value == "":
        return True
    return isinstance(value, (list, dict)) and not value


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()
