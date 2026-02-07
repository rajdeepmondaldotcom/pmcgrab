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

import contextlib
import gc
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

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


def _extract_paper_dict(
    paper: Paper, pmc_id: str | int
) -> dict[str, str | dict | list] | None:
    """Extract a normalized dictionary from a Paper object.

    Centralised helper so that both ``process_single_pmc`` and
    ``process_single_local_xml`` share the same extraction logic
    without duplicating code.
    """
    body_info: dict[str, str] = {}
    body_sections = paper.body
    if body_sections is not None:
        try:
            iter(body_sections)
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

    paper_info: dict[str, str | dict | list] = {
        "pmc_id": str(pmc_id),
        "abstract": paper.abstract_as_str() if paper.abstract else "",
        "has_data": str(paper.has_data),
        "body": body_info or {},
        "title": paper.title or "",
        "authors": paper.authors if paper.authors is not None else "",
        "non_author_contributors": (
            paper.non_author_contributors
            if paper.non_author_contributors is not None
            else ""
        ),
        "publisher_name": (
            paper.publisher_name if paper.publisher_name is not None else ""
        ),
        "publisher_location": (
            paper.publisher_location if paper.publisher_location is not None else ""
        ),
        "article_id": paper.article_id if paper.article_id is not None else "",
        "journal_title": paper.journal_title if paper.journal_title is not None else "",
        "journal_id": paper.journal_id if paper.journal_id is not None else "",
        "issn": paper.issn if paper.issn is not None else "",
        "article_types": paper.article_types if paper.article_types is not None else "",
        "article_categories": (
            paper.article_categories if paper.article_categories is not None else ""
        ),
        "published_date": (
            paper.published_date if paper.published_date is not None else ""
        ),
        "volume": paper.volume if paper.volume is not None else "",
        "issue": paper.issue if paper.issue is not None else "",
        "permissions": paper.permissions if paper.permissions is not None else "",
        "copyright": paper.copyright if paper.copyright is not None else "",
        "license": paper.license if paper.license is not None else "",
        "funding": paper.funding if paper.funding is not None else "",
        "footnote": paper.footnote if paper.footnote is not None else "",
        "acknowledgements": (
            paper.acknowledgements if paper.acknowledgements is not None else ""
        ),
        "notes": paper.notes if paper.notes is not None else "",
        "custom_meta": paper.custom_meta if paper.custom_meta is not None else "",
        "last_updated": getattr(paper, "last_updated", ""),
    }

    # Normalise all values once for JSON compatibility
    paper_info = {k: normalize_value(v) for k, v in paper_info.items()}

    if not paper_info.get("body"):
        return None
    return paper_info


# ---------------------------------------------------------------------------
# Thread-safe timeout helper (replaces signal.alarm which only works in the
# main thread on POSIX and is a no-op on Windows)
# ---------------------------------------------------------------------------

_TIMEOUT_SECONDS = 60


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
    paper = None
    try:
        pmc_id_num = int(pmc_id)
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
            return None

        if paper is None:
            return None

        return _extract_paper_dict(paper, pmc_id_num)

    except Exception:
        return None
    finally:
        with contextlib.suppress(Exception):
            del paper
        gc.collect()


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
            return None
        paper = Paper(d)
        if paper is None or not paper.has_data:
            return None
        pmcid = d.get("PMCID", 0)
        return _extract_paper_dict(paper, pmcid)
    except Exception:
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
