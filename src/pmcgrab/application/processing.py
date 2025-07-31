from __future__ import annotations

"""Pure batch-processing helpers (application layer).

These functions contain **no user interaction code** – no tqdm progress bars,
no `print` statements. The aim is to make them reusable in any context
(programmatic, web, CLI, etc.).
"""

import contextlib
import gc
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed

from pmcgrab.application.paper_builder import build_paper_from_pmc
from pmcgrab.common.serialization import normalize_value
from pmcgrab.constants import TimeoutException
from pmcgrab.infrastructure.settings import next_email

__all__: list[str] = [
    "process_pmc_ids",
    "process_single_pmc",
]


# ---------------------------------------------------------------------------
# Single-article processing (unchanged logic, no prints)
# ---------------------------------------------------------------------------


def process_single_pmc(pmc_id: str) -> dict[str, str | dict | list] | None:
    """Download and parse one PMC article returning a normalised dict."""
    gc.collect()
    paper_info: dict[str, str | dict | list] = {}
    body_info: dict[str, str] = {}

    try:
        pmc_id_num = int(pmc_id)
        current_email = next_email()

        # Time-boxed network / parsing
        signal.alarm(60)
        try:
            paper = build_paper_from_pmc(
                pmc_id_num, email=current_email, download=True, validate=False
            )
        except TimeoutException:
            return None
        finally:
            signal.alarm(0)

        if paper is None:
            return None

        # ---------------- Text body extraction -------------------------
        body_sections = paper.body
        if body_sections is not None:
            try:
                iter(body_sections)  # Ensure iterable
                sec_counter = 1
                for section in body_sections:
                    try:
                        text = getattr(
                            section, "get_section_text", lambda s=section: str(s)
                        )()
                        title = (
                            section.title
                            if getattr(section, "title", None)
                            else f"Section {sec_counter}"
                        )
                        sec_counter += 1
                        body_info[title] = text
                    except Exception:
                        pass  # Robustness: ignore malformed sections
            except (TypeError, ValueError):
                pass

        # ---------------- Assemble output dict -------------------------
        paper_info["pmc_id"] = str(pmc_id_num)
        paper_info["abstract"] = paper.abstract_as_str() if paper.abstract else ""
        paper_info["has_data"] = str(paper.has_data)
        paper_info["body"] = body_info or {}
        paper_info["title"] = paper.title or ""
        paper_info["authors"] = (
            normalize_value(paper.authors) if paper.authors is not None else ""
        )
        paper_info["non_author_contributors"] = (
            normalize_value(paper.non_author_contributors)
            if paper.non_author_contributors is not None
            else ""
        )
        paper_info["publisher_name"] = (
            normalize_value(paper.publisher_name)
            if paper.publisher_name is not None
            else ""
        )
        paper_info["publisher_location"] = (
            normalize_value(paper.publisher_location)
            if paper.publisher_location is not None
            else ""
        )
        paper_info["article_id"] = (
            normalize_value(paper.article_id) if paper.article_id is not None else ""
        )
        paper_info["journal_title"] = (
            normalize_value(paper.journal_title)
            if paper.journal_title is not None
            else ""
        )
        paper_info["journal_id"] = (
            normalize_value(paper.journal_id) if paper.journal_id is not None else ""
        )
        paper_info["issn"] = (
            normalize_value(paper.issn) if paper.issn is not None else ""
        )
        paper_info["article_types"] = (
            normalize_value(paper.article_types)
            if paper.article_types is not None
            else ""
        )
        paper_info["article_categories"] = (
            normalize_value(paper.article_categories)
            if paper.article_categories is not None
            else ""
        )
        paper_info["published_date"] = (
            normalize_value(paper.published_date)
            if paper.published_date is not None
            else ""
        )
        paper_info["volume"] = (
            normalize_value(paper.volume) if paper.volume is not None else ""
        )
        paper_info["issue"] = (
            normalize_value(paper.issue) if paper.issue is not None else ""
        )
        paper_info["permissions"] = (
            normalize_value(paper.permissions) if paper.permissions is not None else ""
        )
        paper_info["copyright"] = (
            normalize_value(paper.copyright) if paper.copyright is not None else ""
        )
        paper_info["license"] = (
            normalize_value(paper.license) if paper.license is not None else ""
        )
        paper_info["funding"] = (
            normalize_value(paper.funding) if paper.funding is not None else ""
        )
        paper_info["footnote"] = (
            normalize_value(paper.footnote) if paper.footnote is not None else ""
        )
        paper_info["acknowledgements"] = (
            normalize_value(paper.acknowledgements)
            if paper.acknowledgements is not None
            else ""
        )
        paper_info["notes"] = (
            normalize_value(paper.notes) if paper.notes is not None else ""
        )
        paper_info["custom_meta"] = (
            normalize_value(paper.custom_meta) if paper.custom_meta is not None else ""
        )
        paper_info["last_updated"] = normalize_value(getattr(paper, "last_updated", ""))

        # Normalise nested structures one last time
        paper_info = {k: normalize_value(v) for k, v in paper_info.items()}
        if not paper_info.get("body"):
            return None
        return paper_info

    finally:
        with contextlib.suppress(Exception):
            del body_info, paper
        gc.collect()


# ---------------------------------------------------------------------------
# Batch processing – returns stats, no user interaction
# ---------------------------------------------------------------------------


def process_pmc_ids(pmc_ids: list[str], *, workers: int = 16) -> dict[str, bool]:
    """Process *pmc_ids* concurrently and return mapping `pmcid → success`."""
    results: dict[str, bool] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_id = {
            executor.submit(process_single_pmc, pid): pid for pid in pmc_ids
        }
        for future in as_completed(future_to_id):
            pid = future_to_id[future]
            try:
                results[pid] = future.result() is not None
            except Exception:
                results[pid] = False
    return results
