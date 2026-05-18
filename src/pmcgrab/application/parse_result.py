from __future__ import annotations

"""Internal parse-result record used by the V3/V4 output renderers."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class JatsParseResult:
    """Richer structured facts collected while parsing one JATS article.

    The legacy parser dictionary remains the compatibility surface for V2.
    This record is the deeper internal model newer renderers use when fidelity
    needs data the legacy dictionary cannot express cleanly.
    """

    abstracts: list[dict[str, Any]] = field(default_factory=list)
    references: list[dict[str, Any]] = field(default_factory=list)
    links: list[dict[str, Any]] = field(default_factory=list)
    date_records: dict[str, Any] = field(default_factory=dict)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    article_ids: list[dict[str, Any]] = field(default_factory=list)
    title_records: list[dict[str, Any]] = field(default_factory=list)
    keyword_groups: list[dict[str, Any]] = field(default_factory=list)
    subject_groups: list[dict[str, Any]] = field(default_factory=list)
    contributors: list[dict[str, Any]] = field(default_factory=list)
    affiliations: list[dict[str, Any]] = field(default_factory=list)
    contributor_affiliation_links: list[dict[str, Any]] = field(default_factory=list)
    license_records: list[dict[str, Any]] = field(default_factory=list)
    content_sections: list[dict[str, Any]] = field(default_factory=list)
    table_records: list[dict[str, Any]] = field(default_factory=list)
    figure_records: list[dict[str, Any]] = field(default_factory=list)
    equation_records: list[dict[str, Any]] = field(default_factory=list)
    supplementary_records: list[dict[str, Any]] = field(default_factory=list)
    coverage: dict[str, Any] = field(default_factory=dict)
