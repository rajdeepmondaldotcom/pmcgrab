from __future__ import annotations

"""Pure batch-processing helpers (application layer).

These functions contain **no user interaction code** -- no tqdm progress bars,
no ``print`` statements.  The aim is to make them reusable in any context
(programmatic, web, CLI, etc.).

In addition to network-based processing (``process_single_pmc``), this module
provides **local XML file processing** (``process_single_local_xml``,
``process_local_xml_dir``) for working with bulk-exported PMC data that has
already been downloaded to disk.  Local processing bypasses the network
entirely and is orders of magnitude faster.
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

_logger = logging.getLogger(__name__)

from pmcgrab.application.paper_builder import build_paper_from_pmc
from pmcgrab.common.serialization import normalize_value
from pmcgrab.constants import TimeoutException
from pmcgrab.infrastructure.settings import next_email
from pmcgrab.model import Paper
from pmcgrab.parser import paper_dict_from_local_xml

__all__: list[str] = [
    "process_local_xml_dir",
    "process_pmc_ids",
    "process_single_local_xml",
    "process_single_pmc",
]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _or(val, default):
    """Return *val* if not None and not a sentinel string, else *default*."""
    if val is None:
        return default
    if isinstance(val, str) and val.startswith("No ") and val.endswith("found."):
        return default
    return val


def _extract_paper_dict(
    paper: Paper,
    pmc_id: str | int,
    *,
    metadata_only: bool = False,
    _source: str = "ncbi_entrez",
    _xml_path: str | None = None,
) -> dict[str, str | dict | list | bool | int | None] | None:
    """Extract a normalized dictionary from a Paper object.

    Centralised helper so that both ``process_single_pmc`` and
    ``process_single_local_xml`` share the same extraction logic
    without duplicating code.

    Returns a comprehensive, snake_case, JSON-serializable dictionary
    containing all parsed fields from the article.
    """
    import datetime as _dt

    import pmcgrab

    # --- Body (flat + nested + paragraph-level) ---
    body_info = paper.body_as_dict()
    body_nested = paper.body_as_nested_dict()
    paragraphs = paper.body_as_paragraphs()

    # --- Abstract ---
    abstract_dict = paper.abstract_as_dict()
    abstract_text = paper.abstract_as_str() if paper.abstract else ""

    # --- Table of contents ---
    toc = paper.get_toc()

    # --- Full text ---
    full_text = paper.full_text()

    # --- Compute word/char counts ---
    body_text_all = "\n".join(body_info.values())
    body_word_count = len(body_text_all.split()) if body_text_all else 0
    body_char_count = len(body_text_all)
    abstract_word_count = len(abstract_text.split()) if abstract_text else 0

    # --- Section-level statistics ---
    section_stats: list[dict] = []
    if paper.body:
        from pmcgrab.model import TextFigure, TextParagraph, TextSection, TextTable

        for element in paper.body:
            if isinstance(element, TextSection):
                clean_text = element.get_clean_text()
                n_paragraphs = sum(
                    1 for c in element.children if isinstance(c, TextParagraph)
                )
                n_subsections = sum(
                    1 for c in element.children if isinstance(c, TextSection)
                )
                section_stats.append(
                    {
                        "title": element.title or "",
                        "word_count": len(clean_text.split()) if clean_text else 0,
                        "char_count": len(clean_text),
                        "paragraph_count": n_paragraphs,
                        "subsection_count": n_subsections,
                        "has_tables": any(
                            isinstance(c, TextTable) for c in element.children
                        ),
                        "has_figures": any(
                            isinstance(c, TextFigure) for c in element.children
                        ),
                    }
                )

    now_iso = _dt.datetime.now(_dt.UTC).isoformat()

    paper_info: dict[str, str | dict | list | bool | int | None] = {
        # --- Identifiers ---
        "pmc_id": str(pmc_id),
        "article_id": _or(paper.article_id, {}),
        # --- Core metadata ---
        "title": paper.title or "",
        "has_data": paper.has_data,
        # --- Abstract (structured + plain text) ---
        "abstract": abstract_dict,
        "abstract_text": abstract_text,
        # --- Body (section title -> clean text) ---
        "body": body_info,
        "body_nested": body_nested,
        "paragraphs": paragraphs,
        "full_text": full_text,
        "toc": toc,
        # --- Authors & contributors ---
        "authors": _or(paper.authors, []),
        "non_author_contributors": (
            paper.non_author_contributors
            if paper.non_author_contributors is not None
            and not isinstance(paper.non_author_contributors, str)
            else []
        ),
        # --- Journal info ---
        "journal_title": _or(paper.journal_title, ""),
        "journal_id": _or(paper.journal_id, {}),
        "issn": _or(paper.issn, {}),
        "publisher_name": _or(paper.publisher_name, ""),
        "publisher_location": _or(paper.publisher_location, ""),
        # --- Classification ---
        "article_types": _or(paper.article_types, []),
        "article_categories": _or(paper.article_categories, []),
        "keywords": _or(paper.keywords, []),
        # --- Dates ---
        "published_date": _or(paper.published_date, {}),
        "history_dates": _or(paper.history_dates, {}),
        # --- Volume / issue / pages ---
        "volume": _or(paper.volume, ""),
        "issue": _or(paper.issue, ""),
        "fpage": _or(paper.fpage, ""),
        "lpage": _or(paper.lpage, ""),
        # --- Permissions ---
        "permissions": _or(paper.permissions, {}),
        "copyright": _or(paper.copyright, ""),
        "license": _or(paper.license, ""),
        # --- References & cross-references ---
        "citations": _or(paper.citations, []),
        "tables": _or(paper.tables, []),
        "figures": _or(paper.figures, []),
        "equations": _or(paper.equations, []),
        # --- Funding & ethics ---
        "funding": _or(paper.funding, []),
        "ethics": _or(paper.ethics, {}),
        # --- Supplementary ---
        "supplementary_material": _or(paper.supplementary, []),
        "footnote": _or(paper.footnote, ""),
        "acknowledgements": _or(paper.acknowledgements, []),
        "notes": _or(paper.notes, []),
        "custom_meta": _or(paper.custom_meta, {}),
        # --- Additional extractions ---
        "elocation_id": getattr(paper, "elocation_id", None) or "",
        "counts": getattr(paper, "counts", None) or {},
        "self_uri": getattr(paper, "self_uri", None) or [],
        "related_articles": getattr(paper, "related_articles", None) or [],
        "conference": getattr(paper, "conference", None) or {},
        "version_history": getattr(paper, "version_history", None) or [],
        # --- Phase 5 extractions ---
        "subtitle": getattr(paper, "subtitle", None) or "",
        "author_notes": getattr(paper, "author_notes", None) or {},
        "appendices": getattr(paper, "appendices", None) or [],
        "glossary": getattr(paper, "glossary", None) or [],
        "translated_titles": getattr(paper, "translated_titles", None) or [],
        "translated_abstracts": getattr(paper, "translated_abstracts", None) or [],
        "abstract_type": getattr(paper, "abstract_type", None) or "",
        "tex_equations": getattr(paper, "tex_equations", None) or [],
        # --- Metadata counts ---
        "word_count": body_word_count + abstract_word_count,
        "body_word_count": body_word_count,
        "body_char_count": body_char_count,
        "abstract_word_count": abstract_word_count,
        "section_count": len(body_info),
        "paragraph_count": len(paragraphs),
        "citation_count": len(paper.citations) if paper.citations else 0,
        "table_count": len(paper.tables) if paper.tables else 0,
        "figure_count": len(paper.figures) if paper.figures else 0,
        # --- Section-level statistics ---
        "section_stats": section_stats,
        # --- Timestamps ---
        "last_updated": now_iso,
        # --- Provenance metadata ---
        "_meta": {
            "pmcgrab_version": pmcgrab.__version__,
            "parse_timestamp": now_iso,
            "source": _source,
            "xml_source_path": _xml_path,
        },
    }

    # Normalise all values once for JSON compatibility
    paper_info = {k: normalize_value(v) for k, v in paper_info.items()}

    if not metadata_only and not paper_info.get("body"):
        return None
    return paper_info


# ---------------------------------------------------------------------------
# Thread-safe timeout helper (replaces signal.alarm which only works in the
# main thread on POSIX and is a no-op on Windows)
# ---------------------------------------------------------------------------

from pmcgrab.infrastructure.settings import NCBI_TIMEOUT as _TIMEOUT_SECONDS


def _run_with_timeout(fn, *args, timeout: int = _TIMEOUT_SECONDS, **kwargs):
    """Run *fn* in a daemon thread with a timeout.

    Returns the function result or raises ``TimeoutException``.
    """
    result_box: list = []
    error_box: list = []

    def _target():
        try:
            result_box.append(fn(*args, **kwargs))
        except Exception as exc:
            error_box.append(exc)

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(timeout=timeout)
    if t.is_alive():
        # Thread is still running -- we treat this as a timeout.
        # The daemon thread will be cleaned up on process exit.
        raise TimeoutException(f"Operation timed out after {timeout}s")
    if error_box:
        raise error_box[0]
    return result_box[0] if result_box else None


# ---------------------------------------------------------------------------
# Single-article processing (network)
# ---------------------------------------------------------------------------


def process_single_pmc(
    pmc_id: str,
    *,
    download: bool = False,
    timeout: int = _TIMEOUT_SECONDS,
    metadata_only: bool = False,
) -> dict[str, str | dict | list] | None:
    """Download and parse a single PMC article into normalized dictionary format.

    Application-layer function that handles the complete processing pipeline
    for a single PMC article: fetching XML, parsing content, extracting
    structured data, and normalizing for JSON serialization. Includes
    thread-safe timeout protection and robust error handling.

    Args:
        pmc_id: String representation of the PMC ID (e.g., "7181753")
        download: If True, cache raw XML locally in data/ directory for reuse.
        timeout: Maximum seconds to wait for network/parsing (default: 60).

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
    """
    try:
        pmc_id_num = int(pmc_id)
        if pmc_id_num <= 0:
            _logger.warning("Invalid PMC ID (must be positive): %s", pmc_id)
            return None
        current_email = next_email()

        try:
            paper = _run_with_timeout(
                build_paper_from_pmc,
                pmc_id_num,
                email=current_email,
                download=download,
                validate=False,
                timeout=timeout,
            )
        except TimeoutException:
            _logger.warning("Timeout processing PMCID %s after %ds", pmc_id, timeout)
            return None

        if paper is None:
            _logger.info("No data returned for PMCID %s", pmc_id)
            return None

        return _extract_paper_dict(
            paper,
            pmc_id_num,
            metadata_only=metadata_only,
            _source="ncbi_entrez",
        )

    except Exception:
        _logger.exception("Error processing PMCID %s", pmc_id)
        return None


# ---------------------------------------------------------------------------
# Single-article processing (local XML file)
# ---------------------------------------------------------------------------


def process_single_local_xml(
    xml_path: str | Path,
) -> dict[str, str | dict | list] | None:
    """Parse a single local JATS XML file into normalized dictionary format.

    This is the local-file counterpart of :func:`process_single_pmc`.
    Instead of downloading XML from NCBI, it reads a pre-downloaded JATS XML
    file from disk.  No network I/O, no timeouts, no email address required.

    Args:
        xml_path: Path to a JATS XML file on disk.

    Returns:
        dict[str, str | dict | list] | None: Normalized article dictionary
            (same structure as :func:`process_single_pmc` output), or None
            if the file cannot be parsed or has no usable body content.

    Examples:
        >>> data = process_single_local_xml("path/to/PMC7181753.xml")
        >>> if data:
        ...     print(f"Title: {data['title']}")
        ...     print(f"Sections: {list(data['body'].keys())}")
    """
    try:
        d = paper_dict_from_local_xml(
            str(xml_path),
            suppress_warnings=True,
            suppress_errors=True,
        )
        if not d:
            _logger.info("No data from local XML: %s", xml_path)
            return None
        paper = Paper(d)
        if paper is None or not paper.has_data:
            _logger.info("Empty paper from local XML: %s", xml_path)
            return None
        pmcid = d.get("PMCID", 0)
        return _extract_paper_dict(
            paper,
            pmcid,
            _source="local_xml",
            _xml_path=str(xml_path),
        )
    except Exception:
        _logger.exception("Error processing local XML: %s", xml_path)
        return None


# ---------------------------------------------------------------------------
# Batch processing -- local XML directory
# ---------------------------------------------------------------------------


def process_local_xml_dir(
    directory: str | Path,
    *,
    pattern: str = "*.xml",
    workers: int | None = None,
) -> dict[str, dict[str, str | dict | list] | None]:
    """Batch-process a directory of local JATS XML files concurrently.

    Scans *directory* for files matching *pattern* and parses each one
    using :func:`process_single_local_xml` in a thread pool.  This is the
    recommended way to process bulk-exported PMC data.

    Args:
        directory: Path to a directory containing JATS XML files.
        pattern: Glob pattern for selecting files (default: ``"*.xml"``).
        workers: Number of concurrent worker threads (default: 16).

    Returns:
        dict[str, dict | None]: Mapping from filename (stem, e.g. "PMC7181753")
            to the parsed article dictionary, or ``None`` if parsing failed.

    Examples:
        >>> results = process_local_xml_dir("./pmc_bulk_xml/")
        >>> successful = {k: v for k, v in results.items() if v is not None}
        >>> print(f"Parsed {len(successful)} / {len(results)} articles")
    """
    directory = Path(directory)
    xml_files = sorted(directory.glob(pattern))
    if workers is None:
        workers = 16

    results: dict[str, dict[str, str | dict | list] | None] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_name = {
            executor.submit(process_single_local_xml, fp): fp.stem for fp in xml_files
        }
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                results[name] = future.result()
            except Exception:
                results[name] = None
    return results


# ---------------------------------------------------------------------------
# Batch processing -- network (returns stats, no user interaction)
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
        batch_size: Alias for *workers* (kept for backward compatibility).

    Returns:
        dict[str, bool]: Mapping from PMC ID to processing success status.
                        True indicates successful processing, False indicates failure.

    Examples:
        >>> ids = ["7181753", "3539614", "5454911"]
        >>> results = process_pmc_ids(ids, workers=8)
        >>> successful = [pid for pid, success in results.items() if success]
        >>> print(f"Successfully processed {len(successful)} articles")

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


# ---------------------------------------------------------------------------
# Async batch processing (optional -- requires no new deps)
# ---------------------------------------------------------------------------


async def async_process_pmc_ids(
    pmc_ids: list[str],
    *,
    max_concurrency: int = 10,
) -> dict[str, dict | None]:
    """Process multiple PMC IDs concurrently using asyncio.

    Wraps the synchronous :func:`process_single_pmc` in an executor so
    that I/O-bound network calls can overlap.  Uses an asyncio Semaphore
    to cap concurrency and respect NCBI rate limits.

    Args:
        pmc_ids: List of PMC ID strings to process.
        max_concurrency: Maximum number of concurrent requests (default: 10).

    Returns:
        dict[str, dict | None]: Mapping from PMC ID to parsed article dict
            (or ``None`` on failure).

    Examples:
        >>> import asyncio
        >>> results = asyncio.run(async_process_pmc_ids(["7181753", "3539614"]))
        >>> for pid, data in results.items():
        ...     print(pid, "OK" if data else "FAIL")
    """
    import asyncio

    sem = asyncio.Semaphore(max_concurrency)
    loop = asyncio.get_running_loop()

    async def _process_one(pid: str) -> tuple[str, dict | None]:
        async with sem:
            result = await loop.run_in_executor(None, process_single_pmc, pid)
            return pid, result

    tasks = [_process_one(pid) for pid in pmc_ids]
    pairs = await asyncio.gather(*tasks, return_exceptions=True)

    results: dict[str, dict | None] = {}
    for item in pairs:
        if isinstance(item, BaseException):
            continue
        pid, data = item
        results[pid] = data
    return results
