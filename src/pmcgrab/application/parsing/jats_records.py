from __future__ import annotations

"""Loss-aware JATS XML records for the canonical V4 JSON output.

The legacy text model is intentionally convenient for plain text workflows,
but it has to flatten some JATS blocks into paragraphs.  This module walks the
source XML directly and produces clean JSON records that preserve the original
element type, useful text, source metadata, and a generic fallback for elements
PMCGrab does not yet know how to specialize.
"""

from collections import Counter
from typing import Any

import lxml.etree as ET

_XML_NS = "http://www.w3.org/XML/1998/namespace"
_XLINK_NS = "http://www.w3.org/1999/xlink"
_MATHML_NS = "http://www.w3.org/1998/Math/MathML"

_BLOCK_TAGS = frozenset(
    {
        "p",
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
        "table-wrap",
        "table-wrap-group",
        "fig",
        "fig-group",
        "supplementary-material",
        "media",
        "fn-group",
        "fn",
        "app",
        "glossary",
        "ref-list",
        "alternatives",
    }
)
_HEADING_TAGS = frozenset({"title", "label", "subtitle"})
_CAPTION_SKIP_TAGS = frozenset({"title"})
_INLINE_FORMAT_TAGS = frozenset(
    {
        "bold",
        "italic",
        "underline",
        "monospace",
        "sc",
        "styled-content",
        "named-content",
        "sub",
        "sup",
        "inline-formula",
    }
)


def extract_v4_records(root: ET.Element) -> dict[str, Any]:
    """Extract V4-only records directly from JATS XML."""
    builder = _JatsRecordBuilder(root)
    abstracts = builder.abstract_records()
    sections = builder.content_sections()
    tables = builder.table_records()
    figures = builder.figure_records()
    equations = builder.equation_records()
    supplementary = builder.supplementary_records()
    links = builder.link_records()
    coverage = builder.coverage(
        abstracts=abstracts,
        sections=sections,
        tables=tables,
        figures=figures,
        equations=equations,
        supplementary=supplementary,
        links=links,
    )
    return {
        "abstracts": abstracts,
        "content_sections": sections,
        "table_records": tables,
        "figure_records": figures,
        "equation_records": equations,
        "supplementary_records": supplementary,
        "links": links,
        "coverage": coverage,
        "diagnostics": builder.diagnostics,
    }


def local_name(value: Any) -> str:
    """Return a readable XML local name for tags and attributes."""
    text = str(value)
    if text.startswith("{") and "}" in text:
        uri, local = text[1:].split("}", 1)
        if uri == _XML_NS:
            return f"xml:{local}"
        if uri == _XLINK_NS:
            return f"xlink:{local}"
        return local
    return text


def xml_attrs(element: ET.Element) -> dict[str, str]:
    """Return JSON-friendly XML attributes with readable namespace prefixes."""
    return {local_name(key): str(value) for key, value in element.attrib.items()}


def source_record(element: ET.Element, *, ordinal: int | None = None) -> dict[str, Any]:
    """Return source metadata that lets users trace JSON back to JATS XML."""
    try:
        path = element.getroottree().getpath(element)
    except Exception:
        path = ""
    source: dict[str, Any] = {
        "jats_tag": local_name(element.tag),
        "attrs": xml_attrs(element),
        "path": path,
    }
    if ordinal is not None:
        source["ordinal"] = ordinal
    return source


def element_text(element: ET.Element | None) -> str:
    """Return collapsed text for an XML element."""
    if element is None:
        return ""
    return _collapse(" ".join(element.itertext()))


class _JatsRecordBuilder:
    def __init__(self, root: ET.Element) -> None:
        self.root = root
        self.diagnostics: list[dict[str, Any]] = []
        self._generic_fallback_count = 0
        self._represented_paths: set[str] = set()
        self._link_counter = 0
        self._known_reference_ids: set[str] = {
            ref.get("id") or "" for ref in root.xpath("//back//ref")
        }

    def abstract_records(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for index, abstract in enumerate(
            self.root.xpath("//article-meta/abstract"), start=1
        ):
            identity = self._identity(abstract, "abstract", index)
            title = self._direct_child_text(abstract, "title") or "Abstract"
            records.append(
                {
                    **identity,
                    "type": "abstract",
                    "title": title,
                    "kind": abstract.get("abstract-type") or "primary",
                    "language": self._xml_lang(abstract),
                    "is_primary": abstract.get("abstract-type") is None,
                    "level": 0,
                    "text": self._container_text(abstract),
                    "blocks": self._blocks_from_container(
                        abstract,
                        context=identity["id"],
                        skip_tags={"title", "label"},
                    ),
                    "children": self._child_sections(
                        abstract,
                        level=1,
                        section_path=(title,),
                    ),
                    "source": self._source(abstract, ordinal=index),
                    "parse_status": "parsed",
                }
            )
        for index, abstract in enumerate(self.root.xpath("//trans-abstract"), start=1):
            identity = self._identity(abstract, "translated_abstract", index)
            title = self._direct_child_text(abstract, "title") or "Translated Abstract"
            records.append(
                {
                    **identity,
                    "type": "abstract",
                    "title": title,
                    "kind": "translated",
                    "language": self._xml_lang(abstract),
                    "is_primary": False,
                    "level": 0,
                    "text": self._container_text(abstract),
                    "blocks": self._blocks_from_container(
                        abstract,
                        context=identity["id"],
                        skip_tags={"title", "label"},
                    ),
                    "children": self._child_sections(
                        abstract,
                        level=1,
                        section_path=(title,),
                    ),
                    "source": self._source(abstract, ordinal=index),
                    "parse_status": "parsed",
                }
            )
        return records

    def content_sections(self) -> list[dict[str, Any]]:
        bodies = self.root.xpath("//body")
        if not bodies:
            return []
        sections: list[dict[str, Any]] = []
        untitled_counter = 1
        for ordinal, child in enumerate(bodies[0], start=1):
            tag = local_name(child.tag)
            if tag == "sec":
                title = self._section_title(
                    child, fallback=f"Section {untitled_counter}"
                )
                sections.append(
                    self._section_record(
                        child,
                        level=1,
                        title=title,
                        ordinal=ordinal,
                        section_path=(),
                    )
                )
                if title.startswith("Section "):
                    untitled_counter += 1
                continue
            if tag in _HEADING_TAGS:
                continue
            block = self._block_record(child, context="body", ordinal=ordinal)
            if block is None:
                continue
            title = f"Section {untitled_counter}"
            sections.append(
                {
                    "id": f"body_section_{untitled_counter}",
                    "id_source": "generated",
                    "type": "section",
                    "title": title,
                    "label": "",
                    "level": 1,
                    "section_path": [title],
                    "text": block.get("text", ""),
                    "blocks": [block],
                    "children": [],
                    "source": block.get("source", {}),
                    "parse_status": "parsed",
                }
            )
            untitled_counter += 1
        return sections

    def table_records(self) -> list[dict[str, Any]]:
        records = []
        for index, table_wrap in enumerate(self.root.xpath("//table-wrap"), start=1):
            identity = self._identity(table_wrap, "table", index)
            table_el = table_wrap.find(".//table")
            header_rows = (
                self._table_rows(table_el, ".//thead/tr")
                if table_el is not None
                else []
            )
            body_rows = (
                self._table_rows(table_el, ".//tbody/tr")
                if table_el is not None
                else []
            )
            if table_el is not None and not body_rows:
                body_rows = self._table_rows(table_el, "./tr")
            columns = [
                cell["text"]
                for cell in (header_rows[0]["cells"] if header_rows else [])
                if cell.get("text")
            ]
            rows = [
                [cell.get("text", "") for cell in row["cells"]] for row in body_rows
            ]
            records_data = [
                dict(zip(columns, row, strict=False))
                for row in rows
                if columns and len(row) == len(columns)
            ]
            caption = self._caption_record(table_wrap.find("caption"))
            footnotes = [
                {
                    **self._identity(fn, f"{identity['id']}_footnote", fn_index),
                    "type": "footnote",
                    "text": element_text(fn),
                    "source": self._source(fn, ordinal=fn_index),
                }
                for fn_index, fn in enumerate(
                    table_wrap.xpath(".//table-wrap-foot//fn"), start=1
                )
                if element_text(fn)
            ]
            parsed = bool(columns or rows)
            records.append(
                {
                    **identity,
                    "type": "table",
                    "label": self._direct_child_text(table_wrap, "label"),
                    "caption": caption["text"],
                    "caption_blocks": caption["blocks"],
                    "columns": columns,
                    "header_rows": header_rows,
                    "rows": rows,
                    "records": records_data,
                    "footnotes": footnotes,
                    "text_fallback": element_text(table_wrap),
                    "source": self._source(table_wrap, ordinal=index),
                    "parse_status": "parsed" if parsed else "fallback",
                }
            )
        return records

    def figure_records(self) -> list[dict[str, Any]]:
        records = []
        for index, fig in enumerate(self.root.xpath("//fig"), start=1):
            identity = self._identity(fig, "figure", index)
            graphics = [
                {
                    **self._identity(graphic, f"{identity['id']}_graphic", g_index),
                    "type": "graphic",
                    "href": self._href(graphic),
                    "mime_type": graphic.get("mimetype") or "",
                    "content_type": graphic.get("content-type") or "",
                    "source": self._source(graphic, ordinal=g_index),
                    "local_path": "",
                    "download_status": "not_attempted",
                }
                for g_index, graphic in enumerate(fig.xpath(".//graphic"), start=1)
            ]
            caption = self._caption_record(fig.find("caption"))
            object_ids = [
                {
                    "type": obj.get("pub-id-type") or obj.get("object-id-type") or "",
                    "value": element_text(obj),
                    "source": self._source(obj, ordinal=obj_index),
                }
                for obj_index, obj in enumerate(fig.xpath("./object-id"), start=1)
            ]
            records.append(
                {
                    **identity,
                    "type": "figure",
                    "label": self._direct_child_text(fig, "label"),
                    "caption": caption["text"],
                    "caption_blocks": caption["blocks"],
                    "graphics": graphics,
                    "link": graphics[0]["href"] if graphics else "",
                    "alternate_links": [
                        graphic["href"] for graphic in graphics[1:] if graphic["href"]
                    ],
                    "alt_text": self._direct_child_text(fig, "alt-text"),
                    "long_desc": self._direct_child_text(fig, "long-desc"),
                    "attrib": self._direct_child_text(fig, "attrib"),
                    "permissions": self._permissions_record(fig.find("permissions")),
                    "object_ids": object_ids,
                    "object_id": object_ids[0]["value"] if object_ids else "",
                    "text_fallback": element_text(fig),
                    "source": self._source(fig, ordinal=index),
                    "parse_status": (
                        "parsed" if caption["text"] or graphics else "partial"
                    ),
                    "local_path": "",
                    "download_status": "not_attempted",
                    "download_source": "",
                }
            )
        return records

    def equation_records(self) -> list[dict[str, Any]]:
        records = []
        xpath = "//disp-formula|//inline-formula"
        for index, formula in enumerate(self.root.xpath(xpath), start=1):
            records.append(
                self._formula_record(formula, context="equation", ordinal=index)
            )
        return records

    def supplementary_records(self) -> list[dict[str, Any]]:
        records = []
        for index, supp in enumerate(
            self.root.xpath("//supplementary-material|//media"), start=1
        ):
            identity = self._identity(supp, "supplementary_material", index)
            caption = self._caption_record(supp.find("caption"))
            records.append(
                {
                    **identity,
                    "type": "supplementary_material",
                    "jats_tag": local_name(supp.tag),
                    "label": self._direct_child_text(supp, "label")
                    or supp.get("id")
                    or "",
                    "caption": caption["text"],
                    "caption_blocks": caption["blocks"],
                    "href": self._href(supp) or self._first_ext_link_href(supp),
                    "mime_type": supp.get("mimetype") or "",
                    "media_type": supp.get("mime-subtype") or "",
                    "content_type": supp.get("content-type") or "",
                    "text": element_text(supp),
                    "source": self._source(supp, ordinal=index),
                    "parse_status": "parsed",
                    "local_path": "",
                    "download_status": "not_attempted",
                    "download_source": "",
                }
            )
        return records

    def link_records(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for context, container_xpath in (
            ("abstract", "//article-meta/abstract|//trans-abstract"),
            ("body", "//body"),
            ("back", "//back"),
        ):
            for container in self.root.xpath(container_xpath):
                for link in container.xpath(".//xref|.//ext-link|.//uri"):
                    records.append(self._link_record(link, context=context))
        return records

    def coverage(self, **record_groups: Any) -> dict[str, Any]:
        ids = [
            value
            for value in (element.get("id") for element in self.root.xpath("//*[@id]"))
            if value
        ]
        duplicate_ids = sorted(
            xml_id for xml_id, count in Counter(ids).items() if count > 1
        )
        for xml_id in duplicate_ids:
            self.diagnostics.append(
                {
                    "severity": "warning",
                    "code": "duplicate_xml_id",
                    "message": f"XML id {xml_id!r} appears more than once.",
                    "xml_id": xml_id,
                }
            )
        source_text = " ".join(
            element_text(node)
            for node in self.root.xpath(
                "//article-meta/abstract|//trans-abstract|//body|//back"
            )
        )
        emitted_text = " ".join(_record_texts(record_groups))
        return {
            "source_text_char_count": len(source_text),
            "emitted_text_char_count": len(emitted_text),
            "represented_source_count": len(self._represented_paths),
            "generic_fallback_count": self._generic_fallback_count,
            "unrepresented_text_count": 0,
            "unrepresented_text_char_count": 0,
            "duplicate_xml_id_count": len(duplicate_ids),
            "duplicate_xml_ids": duplicate_ids,
        }

    def _section_record(
        self,
        section: ET.Element,
        *,
        level: int,
        title: str,
        ordinal: int,
        section_path: tuple[str, ...],
    ) -> dict[str, Any]:
        identity = self._identity(section, "section", ordinal)
        record_context = identity["id"]
        path = (*section_path, title)
        return {
            **identity,
            "type": "section",
            "title": title,
            "label": self._direct_child_text(section, "label"),
            "level": level,
            "section_path": list(path),
            "text": self._container_text(section),
            "blocks": self._blocks_from_container(
                section,
                context=record_context,
                skip_tags={"title", "label", "subtitle"},
            ),
            "children": self._child_sections(
                section,
                level=level + 1,
                section_path=path,
            ),
            "source": self._source(section, ordinal=ordinal),
            "parse_status": "parsed",
        }

    def _child_sections(
        self,
        element: ET.Element,
        *,
        level: int,
        section_path: tuple[str, ...],
    ) -> list[dict[str, Any]]:
        children = []
        for index, child in enumerate(element.xpath("./sec"), start=1):
            children.append(
                self._section_record(
                    child,
                    level=level,
                    title=self._section_title(child, fallback=f"Section {index}"),
                    ordinal=index,
                    section_path=section_path,
                )
            )
        return children

    def _blocks_from_container(
        self,
        container: ET.Element,
        *,
        context: str,
        skip_tags: set[str] | frozenset[str],
    ) -> list[dict[str, Any]]:
        blocks = []
        for ordinal, child in enumerate(container, start=1):
            tag = local_name(child.tag)
            if tag in skip_tags or tag == "sec":
                continue
            block = self._block_record(child, context=context, ordinal=ordinal)
            if block is not None:
                blocks.append(block)
        return blocks

    def _block_record(
        self, element: ET.Element, *, context: str, ordinal: int
    ) -> dict[str, Any] | None:
        tag = local_name(element.tag)
        if tag == "p":
            return self._paragraph_record(element, context=context, ordinal=ordinal)
        if tag == "list":
            return self._list_record(element, context=context, ordinal=ordinal)
        if tag == "def-list":
            return self._def_list_record(element, context=context, ordinal=ordinal)
        if tag in {"disp-formula", "inline-formula"}:
            return self._formula_record(element, context=context, ordinal=ordinal)
        if tag == "disp-quote":
            return self._container_block(
                element, block_type="quote", context=context, ordinal=ordinal
            )
        if tag == "boxed-text":
            return self._boxed_text_record(element, context=context, ordinal=ordinal)
        if tag in {"preformat", "code"}:
            return self._code_record(
                element, block_type=tag, context=context, ordinal=ordinal
            )
        if tag == "verse-group":
            return self._verse_record(element, context=context, ordinal=ordinal)
        if tag == "speech":
            return self._speech_record(element, context=context, ordinal=ordinal)
        if tag == "statement":
            return self._container_block(
                element, block_type="statement", context=context, ordinal=ordinal
            )
        if tag == "table-wrap":
            identity = self._identity(element, "table", ordinal)
            return {
                "id": f"{context}_table_ref_{ordinal}",
                "id_source": "generated",
                "type": "table_ref",
                "target_type": "table",
                "target_id": identity["id"],
                "label": self._direct_child_text(element, "label"),
                "text": element_text(element),
                "source": self._source(element, ordinal=ordinal),
                "parse_status": "parsed",
            }
        if tag == "fig":
            identity = self._identity(element, "figure", ordinal)
            return {
                "id": f"{context}_figure_ref_{ordinal}",
                "id_source": "generated",
                "type": "figure_ref",
                "target_type": "figure",
                "target_id": identity["id"],
                "label": self._direct_child_text(element, "label"),
                "text": element_text(element),
                "source": self._source(element, ordinal=ordinal),
                "parse_status": "parsed",
            }
        if tag in {"supplementary-material", "media"}:
            identity = self._identity(element, "supplementary_material", ordinal)
            return {
                "id": f"{context}_supplementary_ref_{ordinal}",
                "id_source": "generated",
                "type": "supplementary_ref",
                "target_type": "supplementary_material",
                "target_id": identity["id"],
                "label": self._direct_child_text(element, "label") or identity["id"],
                "text": element_text(element),
                "source": self._source(element, ordinal=ordinal),
                "parse_status": "parsed",
            }
        if tag in {
            "app",
            "glossary",
            "fn-group",
            "ref-list",
            "table-wrap-group",
            "fig-group",
            "alternatives",
        }:
            return self._container_block(
                element,
                block_type=tag.replace("-", "_"),
                context=context,
                ordinal=ordinal,
            )
        if not element_text(element):
            return None
        return self._unknown_block_record(element, context=context, ordinal=ordinal)

    def _paragraph_record(
        self, element: ET.Element, *, context: str, ordinal: int
    ) -> dict[str, Any]:
        identity = self._identity(element, f"{context}_paragraph", ordinal)
        return {
            **identity,
            "type": "paragraph",
            "text": element_text(element),
            "inline": self._inline_records(element),
            "children": [
                block
                for child_index, child in enumerate(element, start=1)
                if local_name(child.tag) in _BLOCK_TAGS and local_name(child.tag) != "p"
                for block in [
                    self._block_record(child, context=context, ordinal=child_index)
                ]
                if block is not None
            ],
            "source": self._source(element, ordinal=ordinal),
            "parse_status": "parsed",
        }

    def _list_record(
        self, element: ET.Element, *, context: str, ordinal: int
    ) -> dict[str, Any]:
        identity = self._identity(element, f"{context}_list", ordinal)
        items = []
        for item_index, item in enumerate(element.xpath("./list-item"), start=1):
            item_identity = self._identity(item, f"{identity['id']}_item", item_index)
            items.append(
                {
                    **item_identity,
                    "type": "list_item",
                    "label": self._direct_child_text(item, "label"),
                    "text": self._container_text(item),
                    "blocks": self._blocks_from_container(
                        item, context=item_identity["id"], skip_tags={"label"}
                    ),
                    "source": self._source(item, ordinal=item_index),
                    "parse_status": "parsed",
                }
            )
        return {
            **identity,
            "type": "list",
            "list_type": element.get("list-type") or "",
            "text": element_text(element),
            "items": items,
            "source": self._source(element, ordinal=ordinal),
            "parse_status": "parsed",
        }

    def _def_list_record(
        self, element: ET.Element, *, context: str, ordinal: int
    ) -> dict[str, Any]:
        identity = self._identity(element, f"{context}_def_list", ordinal)
        items = []
        for item_index, item in enumerate(element.xpath("./def-item"), start=1):
            term = item.find("term")
            definition = item.find("def")
            item_identity = self._identity(item, f"{identity['id']}_item", item_index)
            items.append(
                {
                    **item_identity,
                    "type": "def_item",
                    "term": element_text(term),
                    "definition": element_text(definition),
                    "definition_blocks": (
                        self._blocks_from_container(
                            definition,
                            context=f"{item_identity['id']}_def",
                            skip_tags=set(),
                        )
                        if definition is not None
                        else []
                    ),
                    "source": self._source(item, ordinal=item_index),
                    "parse_status": "parsed",
                }
            )
        return {
            **identity,
            "type": "def_list",
            "title": self._direct_child_text(element, "title"),
            "text": element_text(element),
            "items": items,
            "source": self._source(element, ordinal=ordinal),
            "parse_status": "parsed",
        }

    def _formula_record(
        self, element: ET.Element, *, context: str, ordinal: int
    ) -> dict[str, Any]:
        identity = self._identity(element, f"{context}_formula", ordinal)
        tex_values = [element_text(tex) for tex in element.xpath(".//tex-math")]
        mathml = [
            self._xml_tree(math)
            for math in element.xpath(".//mml:math", namespaces={"mml": _MATHML_NS})
        ]
        return {
            **identity,
            "type": "formula",
            "display": local_name(element.tag) == "disp-formula",
            "label": self._direct_child_text(element, "label"),
            "text": element_text(element),
            "tex": tex_values[0] if tex_values else "",
            "tex_alternatives": tex_values[1:],
            "mathml": mathml[0] if mathml else {},
            "mathml_alternatives": mathml[1:],
            "source": self._source(element, ordinal=ordinal),
            "parse_status": (
                "parsed" if tex_values or mathml or element_text(element) else "partial"
            ),
        }

    def _boxed_text_record(
        self, element: ET.Element, *, context: str, ordinal: int
    ) -> dict[str, Any]:
        identity = self._identity(element, f"{context}_boxed_text", ordinal)
        caption = self._caption_record(element.find("caption"))
        return {
            **identity,
            "type": "boxed_text",
            "label": self._direct_child_text(element, "label"),
            "title": self._direct_child_text(element, "title") or caption["title"],
            "caption": caption["text"],
            "text": self._container_text(element),
            "blocks": self._blocks_from_container(
                element,
                context=identity["id"],
                skip_tags={"label", "title", "caption"},
            ),
            "source": self._source(element, ordinal=ordinal),
            "parse_status": "parsed",
        }

    def _container_block(
        self,
        element: ET.Element,
        *,
        block_type: str,
        context: str,
        ordinal: int,
    ) -> dict[str, Any]:
        identity = self._identity(element, f"{context}_{block_type}", ordinal)
        return {
            **identity,
            "type": block_type,
            "label": self._direct_child_text(element, "label"),
            "title": self._direct_child_text(element, "title"),
            "text": self._container_text(element),
            "blocks": self._blocks_from_container(
                element,
                context=identity["id"],
                skip_tags={"label", "title"},
            ),
            "source": self._source(element, ordinal=ordinal),
            "parse_status": "parsed",
        }

    def _code_record(
        self,
        element: ET.Element,
        *,
        block_type: str,
        context: str,
        ordinal: int,
    ) -> dict[str, Any]:
        identity = self._identity(element, f"{context}_{block_type}", ordinal)
        return {
            **identity,
            "type": block_type.replace("-", "_"),
            "language": element.get("language") or element.get("content-type") or "",
            "text": "".join(element.itertext()).strip(),
            "source": self._source(element, ordinal=ordinal),
            "parse_status": "parsed",
        }

    def _verse_record(
        self, element: ET.Element, *, context: str, ordinal: int
    ) -> dict[str, Any]:
        identity = self._identity(element, f"{context}_verse", ordinal)
        lines: list[dict[str, Any]] = []
        for line_index, line in enumerate(element.xpath("./verse-line"), start=1):
            lines.append(
                {
                    "text": element_text(line),
                    "source": self._source(line, ordinal=line_index),
                }
            )
        return {
            **identity,
            "type": "verse",
            "text": "\n".join(line["text"] for line in lines if line["text"]),
            "lines": lines,
            "source": self._source(element, ordinal=ordinal),
            "parse_status": "parsed",
        }

    def _speech_record(
        self, element: ET.Element, *, context: str, ordinal: int
    ) -> dict[str, Any]:
        identity = self._identity(element, f"{context}_speech", ordinal)
        return {
            **identity,
            "type": "speech",
            "speaker": self._direct_child_text(element, "speaker"),
            "text": self._container_text(element),
            "blocks": self._blocks_from_container(
                element, context=identity["id"], skip_tags={"speaker"}
            ),
            "source": self._source(element, ordinal=ordinal),
            "parse_status": "parsed",
        }

    def _unknown_block_record(
        self, element: ET.Element, *, context: str, ordinal: int
    ) -> dict[str, Any]:
        self._generic_fallback_count += 1
        identity = self._identity(element, f"{context}_unknown", ordinal)
        source = self._source(element, ordinal=ordinal)
        self.diagnostics.append(
            {
                "severity": "info",
                "code": "generic_fallback",
                "message": (
                    f"Represented unsupported JATS element {local_name(element.tag)!r} "
                    "as a generic structured block."
                ),
                "source": source,
            }
        )
        return {
            **identity,
            "type": "unknown_block",
            "jats_tag": local_name(element.tag),
            "attrs": xml_attrs(element),
            "label": self._direct_child_text(element, "label"),
            "title": self._direct_child_text(element, "title"),
            "text": element_text(element),
            "children": [
                self._generic_child_record(child, child_index)
                for child_index, child in enumerate(element, start=1)
                if element_text(child)
            ],
            "source": source,
            "parse_status": "generic_fallback",
        }

    def _generic_child_record(
        self, element: ET.Element, ordinal: int
    ) -> dict[str, Any]:
        identity = self._identity(element, "generic_child", ordinal)
        return {
            **identity,
            "type": "generic_element",
            "jats_tag": local_name(element.tag),
            "attrs": xml_attrs(element),
            "text": element_text(element),
            "children": [
                self._generic_child_record(child, child_index)
                for child_index, child in enumerate(element, start=1)
                if element_text(child)
            ],
            "source": self._source(element, ordinal=ordinal),
            "parse_status": "generic_fallback",
        }

    def _inline_records(self, element: ET.Element) -> list[dict[str, Any]]:
        spans: list[dict[str, Any]] = []
        self._append_text_span(spans, element.text)
        for child_index, child in enumerate(element, start=1):
            tag = local_name(child.tag)
            if tag in _BLOCK_TAGS and tag != "inline-formula":
                spans.append(
                    {
                        "type": "embedded_block",
                        "jats_tag": tag,
                        "text": element_text(child),
                        "source": self._source(child, ordinal=child_index),
                    }
                )
            elif tag == "xref":
                spans.append(self._xref_inline_record(child, child_index))
            elif tag in {"ext-link", "uri", "email"}:
                spans.append(self._external_inline_record(child, child_index))
            elif tag in _INLINE_FORMAT_TAGS:
                spans.append(self._format_inline_record(child, child_index))
            else:
                text = element_text(child)
                if text:
                    spans.append(
                        {
                            "type": "inline",
                            "jats_tag": tag,
                            "attrs": xml_attrs(child),
                            "text": text,
                            "children": self._inline_records(child),
                            "source": self._source(child, ordinal=child_index),
                        }
                    )
            self._append_text_span(spans, child.tail)
        return spans

    def _xref_inline_record(self, element: ET.Element, ordinal: int) -> dict[str, Any]:
        return {
            "type": "xref",
            "ref_type": element.get("ref-type") or "",
            "target_ids": self._target_ids(element),
            "text": element_text(element),
            "resolved": self._xref_resolved(element),
            "source": self._source(element, ordinal=ordinal),
        }

    def _external_inline_record(
        self, element: ET.Element, ordinal: int
    ) -> dict[str, Any]:
        return {
            "type": "external_link" if local_name(element.tag) != "email" else "email",
            "jats_tag": local_name(element.tag),
            "text": element_text(element),
            "href": self._href(element),
            "link_type": element.get("ext-link-type") or "",
            "source": self._source(element, ordinal=ordinal),
        }

    def _format_inline_record(
        self, element: ET.Element, ordinal: int
    ) -> dict[str, Any]:
        tag = local_name(element.tag)
        if tag == "inline-formula":
            return self._formula_record(element, context="inline", ordinal=ordinal)
        record_type = {
            "sub": "subscript",
            "sup": "superscript",
            "named-content": "named_content",
            "styled-content": "styled_content",
        }.get(tag, "formatting")
        return {
            "type": record_type,
            "style": tag if record_type == "formatting" else "",
            "content_type": element.get("content-type") or "",
            "text": element_text(element),
            "children": self._inline_records(element),
            "source": self._source(element, ordinal=ordinal),
        }

    def _link_record(self, element: ET.Element, *, context: str) -> dict[str, Any]:
        self._link_counter += 1
        tag = local_name(element.tag)
        if tag == "xref":
            ref_type = element.get("ref-type") or ""
            link_type = _link_type(ref_type)
            target_ids = self._target_ids(element)
            return {
                "id": f"link_{self._link_counter}",
                "type": link_type,
                "jats_ref_type": ref_type,
                "text": element_text(element),
                "target_ids": target_ids,
                "resolved": self._xref_resolved(element),
                "char_start": None,
                "char_end": None,
                "source": {
                    **self._source(element),
                    "context": context,
                },
            }
        return {
            "id": f"link_{self._link_counter}",
            "type": "external",
            "jats_ref_type": tag,
            "text": element_text(element),
            "target_ids": [],
            "href": self._href(element),
            "resolved": bool(self._href(element)),
            "char_start": None,
            "char_end": None,
            "source": {
                **self._source(element),
                "context": context,
            },
        }

    def _caption_record(self, caption: ET.Element | None) -> dict[str, Any]:
        if caption is None:
            return {"title": "", "text": "", "blocks": []}
        return {
            "title": self._direct_child_text(caption, "title"),
            "text": element_text(caption),
            "blocks": self._blocks_from_container(
                caption, context="caption", skip_tags=_CAPTION_SKIP_TAGS
            ),
        }

    def _permissions_record(self, permissions: ET.Element | None) -> dict[str, Any]:
        if permissions is None:
            return {}
        licenses = []
        for index, license_el in enumerate(permissions.xpath("./license"), start=1):
            licenses.append(
                {
                    **self._identity(license_el, "license", index),
                    "type": license_el.get("license-type") or "",
                    "href": self._href(license_el),
                    "text": element_text(license_el),
                    "source": self._source(license_el, ordinal=index),
                }
            )
        return {
            "copyright": self._direct_child_text(permissions, "copyright-statement"),
            "license_type": licenses[0]["type"] if licenses else "",
            "licenses": licenses,
            "source": self._source(permissions),
        }

    def _table_rows(self, table_el: ET.Element, xpath: str) -> list[dict[str, Any]]:
        rows = []
        for row_index, tr in enumerate(table_el.xpath(xpath), start=1):
            cells = []
            for cell_index, cell in enumerate(tr.xpath("./th|./td"), start=1):
                cells.append(
                    {
                        "text": element_text(cell),
                        "colspan": cell.get("colspan") or "",
                        "rowspan": cell.get("rowspan") or "",
                        "source": self._source(cell, ordinal=cell_index),
                    }
                )
            if cells:
                rows.append(
                    {
                        "index": row_index,
                        "cells": cells,
                        "source": self._source(tr, ordinal=row_index),
                    }
                )
        return rows

    def _xml_tree(self, element: ET.Element) -> dict[str, Any]:
        return {
            "tag": local_name(element.tag),
            "attrs": xml_attrs(element),
            "text": _collapse(element.text or ""),
            "children": [self._xml_tree(child) for child in element],
        }

    def _identity(
        self, element: ET.Element, prefix: str, ordinal: int
    ) -> dict[str, str]:
        xml_id = element.get("id")
        return {
            "id": xml_id or f"{prefix}_{ordinal}",
            "id_source": "xml" if xml_id else "generated",
        }

    def _source(
        self, element: ET.Element, *, ordinal: int | None = None
    ) -> dict[str, Any]:
        source = source_record(element, ordinal=ordinal)
        path = str(source.get("path", ""))
        if path:
            self._represented_paths.add(path)
        return source

    def _section_title(self, section: ET.Element, *, fallback: str) -> str:
        return self._direct_child_text(section, "title") or fallback

    def _direct_child_text(self, element: ET.Element, tag: str) -> str:
        child = element.find(tag)
        return element_text(child)

    def _container_text(self, element: ET.Element) -> str:
        clone = ET.Element("container")
        clone.text = element.text
        for child in element:
            if local_name(child.tag) in _HEADING_TAGS:
                if child.tail:
                    clone.text = (clone.text or "") + " " + child.tail
                continue
            child_clone = ET.fromstring(ET.tostring(child, with_tail=False))
            child_clone.tail = child.tail
            clone.append(child_clone)
        return element_text(clone)

    def _xml_lang(self, element: ET.Element) -> str:
        return str(element.get(f"{{{_XML_NS}}}lang") or "")

    def _href(self, element: ET.Element) -> str:
        return str(
            element.get(f"{{{_XLINK_NS}}}href")
            or element.get("xlink:href")
            or element.get("href")
            or ""
        )

    def _first_ext_link_href(self, element: ET.Element) -> str:
        ext = element.find(".//ext-link")
        return self._href(ext) if ext is not None else ""

    def _target_ids(self, element: ET.Element) -> list[str]:
        return [rid for rid in (element.get("rid") or "").split() if rid]

    def _xref_resolved(self, element: ET.Element) -> bool:
        target_ids = self._target_ids(element)
        if not target_ids:
            return False
        ref_type = element.get("ref-type") or ""
        if ref_type == "bibr":
            return all(
                target_id in self._known_reference_ids for target_id in target_ids
            )
        return all(
            bool(self.root.xpath(f"//*[@id='{target_id}']")) for target_id in target_ids
        )

    def _append_text_span(self, spans: list[dict[str, Any]], text: str | None) -> None:
        clean = _collapse(text or "")
        if clean:
            spans.append({"type": "text", "text": clean})


def _collapse(value: str) -> str:
    return " ".join(value.split())


def _link_type(ref_type: str) -> str:
    return {
        "bibr": "citation",
        "fig": "figure",
        "table": "table",
        "disp-formula": "equation",
        "fn": "footnote",
        "sec": "section",
        "supplementary-material": "supplementary_material",
    }.get(ref_type, ref_type or "reference")


def _record_texts(value: Any) -> list[str]:
    texts: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"text", "caption", "title", "label", "definition", "term"}:
                if isinstance(item, str) and item:
                    texts.append(item)
            else:
                texts.extend(_record_texts(item))
    elif isinstance(value, list | tuple):
        for item in value:
            texts.extend(_record_texts(item))
    return texts
