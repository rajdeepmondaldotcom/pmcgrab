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
    """Download and parse a single PMC article into normalized dictionary format.

    Application-layer function that handles the complete processing pipeline
    for a single PMC article: fetching XML, parsing content, extracting
    structured data, and normalizing for JSON serialization. Includes
    timeout protection and robust error handling.

    Args:
        pmc_id: String representation of the PMC ID (e.g., "7181753")

    Returns:
        dict[str, str | dict | list] | None: Normalized article dictionary with keys:
            - pmc_id: Article identifier
            - title: Article title
            - abstract: Plain text abstract
            - body: Dictionary of section titles mapped to text content
            - authors: Normalized author information
            - Journal and publication metadata
            - Content metadata (funding, ethics, etc.)
        Returns None if processing fails or article has no usable content.

    Examples:
        >>> article_data = process_single_pmc("7181753")
        >>> if article_data:
        ...     print(f"Title: {article_data['title']}")
        ...     print(f"Sections: {list(article_data['body'].keys())}")
        ...     print(f"Authors: {len(article_data['authors'])}")

    Note:
        This function includes a 60-second timeout for network/parsing operations
        and performs garbage collection for memory management in batch scenarios.
        All values are normalized using normalize_value() for JSON compatibility.
    """
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


def process_pmc_ids(
    pmc_ids: list[str], *, workers: int | None = None, batch_size: int | None = None
) -> dict[str, bool]:
    """Process multiple PMC IDs concurrently and return success mapping.

    Application-layer batch processing function that handles concurrent
    article processing without user interaction (no progress bars or print
    statements). Designed for integration into various interfaces (CLI, web, API).

    Args:
        pmc_ids: List of PMC ID strings to process
        workers: Number of concurrent worker threads (default: 16)

    Returns:
        dict[str, bool]: Mapping from PMC ID to processing success status.
                        True indicates successful processing, False indicates failure.

    Examples:
        >>> ids = ["7181753", "3539614", "5454911"]
        >>> results = process_pmc_ids(ids, workers=8)
        >>> successful = [pid for pid, success in results.items() if success]
        >>> print(f"Successfully processed {len(successful)} articles")
        >>>
        >>> # Check individual results
        >>> for pid, success in results.items():
        ...     status = "SUCCESS" if success else "FAILED"
        ...     print(f"PMC{pid}: {status}")

    Note:
        This function is pure application logic with no UI concerns.
        Individual article processing is delegated to process_single_pmc().
        Exceptions during processing are caught and recorded as failures.
    """
    # Resolve worker count (batch_size is kept for backward compatibility)
    if batch_size is not None:
        workers = batch_size
    if workers is None:
        workers = 16

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
