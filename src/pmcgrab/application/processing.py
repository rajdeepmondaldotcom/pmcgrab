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
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, TypeVar

_logger = logging.getLogger(__name__)

from pmcgrab.application.paper_builder import build_paper_from_pmc
from pmcgrab.common.paper_output import ArticleOutput, paper_to_output_dict
from pmcgrab.constants import TimeoutException
from pmcgrab.idconvert import normalize_id
from pmcgrab.infrastructure.settings import next_email
from pmcgrab.model import Paper
from pmcgrab.parser import paper_dict_from_local_xml

__all__: list[str] = [
    "process_local_xml_dir",
    "process_pmc_ids",
    "process_single_local_xml",
    "process_single_pmc",
]


# ``process_single_pmc_with_assets`` and ``AssetFetchPolicy`` live in
# :mod:`pmcgrab.application.article_assembly`, which depends on this module.
# Importing them here at module top would create a circular import, so we
# expose them lazily through ``__getattr__`` instead. Callers wanting the
# orchestrator should import it directly from
# :mod:`pmcgrab.application.article_assembly` or via the top-level
# :mod:`pmcgrab` package.
def __getattr__(name: str) -> Any:
    if name == "process_single_pmc_with_assets":
        from pmcgrab.application.article_assembly import process_single_pmc_with_assets

        return process_single_pmc_with_assets
    if name == "AssetFetchPolicy":
        from pmcgrab.application.article_assembly import AssetFetchPolicy

        return AssetFetchPolicy
    raise AttributeError(name)


def _extract_paper_dict(
    paper: Paper,
    pmc_id: str | int,
    *,
    metadata_only: bool = False,
    _source: str = "ncbi_entrez",
    _xml_path: str | None = None,
    schema_version: int | None = None,
    output_style: str | None = None,
) -> ArticleOutput | None:
    """Extract a normalized dictionary from a Paper object.

    The schema itself lives in :mod:`pmcgrab.common.paper_output` so object and
    application interfaces do not drift.
    """
    return paper_to_output_dict(
        paper,
        pmc_id=pmc_id,
        include_processing_fields=True,
        source=_source,
        xml_path=_xml_path,
        require_body=not metadata_only,
        schema_version=schema_version,
        output_style=output_style,
    )


def _validate_output_options(
    output_style: str | None, schema_version: int | None
) -> None:
    if output_style not in (None, "paper", "full"):
        raise ValueError("output_style must be 'paper' or 'full'")
    if output_style == "paper" and schema_version not in (None, 4):
        raise ValueError("schema_version is only supported with output_style='full'")


# ---------------------------------------------------------------------------
# Thread-safe timeout helper (replaces signal.alarm which only works in the
# main thread on POSIX and is a no-op on Windows)
# ---------------------------------------------------------------------------

from pmcgrab.infrastructure.settings import NCBI_TIMEOUT as _TIMEOUT_SECONDS

_T = TypeVar("_T")


def _run_with_timeout(
    fn: Callable[..., _T],
    *args: Any,
    timeout: int = _TIMEOUT_SECONDS,
    **kwargs: Any,
) -> _T | None:
    """Run *fn* in a daemon thread with a timeout.

    Returns the function result or raises ``TimeoutException``.
    """
    result_box: list[_T] = []
    error_box: list[Exception] = []

    def _target() -> None:
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
    pmc_id: str | int,
    *,
    download: bool = False,
    timeout: int = _TIMEOUT_SECONDS,
    metadata_only: bool = False,
    schema_version: int | None = None,
    output_style: str | None = None,
) -> ArticleOutput | None:
    """Download and parse a single PMC article into normalized dictionary format.

    Application-layer function that handles the complete processing pipeline
    for a single PMC article: fetching XML, parsing content, extracting
    structured data, and normalizing for JSON serialization. Includes
    thread-safe timeout protection and robust error handling.

    Args:
        pmc_id: PMC ID as int or string, with or without the ``PMC`` prefix.
        download: If True, cache raw XML locally in data/ directory for reuse.
        timeout: Maximum seconds to wait for network/parsing (default: 60).
        metadata_only: If True, allow metadata-only output without body sections.
        schema_version: Full-output schema version. Passing a schema version
            without ``output_style`` selects the full output for compatibility.
        output_style: ``"paper"`` for clean paper JSON (default), or
            ``"full"`` for V2/V3/V4 metadata-rich output.

    Returns:
        Normalized article dictionary. The default clean paper output includes
        ``identifiers``, ``paper`` (title, abstract, body), and ``assets``
        (images and tables). Pass ``output_style="full"`` for the metadata-rich
        V4/V3/V2 contracts.
        Returns None if processing fails or article has no usable content.

    Examples:
        >>> article_data = process_single_pmc("7181753")
        >>> if article_data:
        ...     print(f"Title: {article_data['paper']['title']}")
        ...     sections = article_data["paper"]["body"]
        ...     print(f"Sections: {[section['title'] for section in sections]}")
    """
    _validate_output_options(output_style, schema_version)
    try:
        normalized_pmc_id = (
            str(pmc_id) if isinstance(pmc_id, int) else normalize_id(str(pmc_id))
        )
        pmc_id_num = int(normalized_pmc_id)
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
                suppress_warnings=True,
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
            schema_version=schema_version,
            output_style=output_style,
        )

    except Exception:
        _logger.exception("Error processing PMCID %s", pmc_id)
        return None


# ---------------------------------------------------------------------------
# Single-article processing (local XML file)
# ---------------------------------------------------------------------------


def process_single_local_xml(
    xml_path: str | Path,
    *,
    schema_version: int | None = None,
    output_style: str | None = None,
) -> ArticleOutput | None:
    """Parse a single local JATS XML file into normalized dictionary format.

    This is the local-file counterpart of :func:`process_single_pmc`.
    Instead of downloading XML from NCBI, it reads a pre-downloaded JATS XML
    file from disk.  No network I/O, no timeouts, no email address required.

    Args:
        xml_path: Path to a JATS XML file on disk.
        schema_version: Full-output schema version. Passing a schema version
            without ``output_style`` selects the full output for compatibility.
        output_style: ``"paper"`` for clean paper JSON (default), or
            ``"full"`` for V2/V3/V4 metadata-rich output.

    Returns:
        Normalized article dictionary, or None if the file cannot be parsed or
        has no usable body content.

    Examples:
        >>> data = process_single_local_xml("path/to/PMC7181753.xml")
        >>> if data:
        ...     print(f"Title: {data['paper']['title']}")
        ...     print(f"Sections: {len(data['paper']['body'])}")
    """
    _validate_output_options(output_style, schema_version)
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
        raw_pmcid = d.get("PMCID", 0)
        pmcid = raw_pmcid if isinstance(raw_pmcid, (str, int)) else 0
        return _extract_paper_dict(
            paper,
            pmcid,
            _source="local_xml",
            _xml_path=str(xml_path),
            schema_version=schema_version,
            output_style=output_style,
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
    schema_version: int | None = None,
    output_style: str | None = None,
) -> dict[str, ArticleOutput | None]:
    """Batch-process a directory of local JATS XML files concurrently.

    Scans *directory* for files matching *pattern* and parses each one
    using :func:`process_single_local_xml` in a thread pool.  This is the
    recommended way to process bulk-exported PMC data.

    Args:
        directory: Path to a directory containing JATS XML files.
        pattern: Glob pattern for selecting files (default: ``"*.xml"``).
        workers: Number of concurrent worker threads (default: 16).
        schema_version: Full-output schema version. Passing a schema version
            without ``output_style`` selects the full output for compatibility.
        output_style: ``"paper"`` for clean paper JSON (default), or
            ``"full"`` for V2/V3/V4 metadata-rich output.

    Returns:
        dict[str, dict | None]: Mapping from filename (stem, e.g. "PMC7181753")
            to the parsed article dictionary, or ``None`` if parsing failed.

    Examples:
        >>> results = process_local_xml_dir("./pmc_bulk_xml/")
        >>> successful = {k: v for k, v in results.items() if v is not None}
        >>> print(f"Parsed {len(successful)} / {len(results)} articles")
    """
    _validate_output_options(output_style, schema_version)
    directory = Path(directory)
    xml_files = sorted(directory.glob(pattern))
    if workers is None:
        workers = 16

    results: dict[str, ArticleOutput | None] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_name = {
            executor.submit(
                process_single_local_xml,
                fp,
                schema_version=schema_version,
                output_style=output_style,
            ): fp.stem
            for fp in xml_files
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
) -> dict[str, ArticleOutput | None]:
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

    async def _process_one(pid: str) -> tuple[str, ArticleOutput | None]:
        async with sem:
            result = await loop.run_in_executor(None, process_single_pmc, pid)
            return pid, result

    tasks = [_process_one(pid) for pid in pmc_ids]
    pairs = await asyncio.gather(*tasks, return_exceptions=True)

    results: dict[str, ArticleOutput | None] = {}
    for item in pairs:
        if isinstance(item, BaseException):
            continue
        pid, data = item
        results[pid] = data
    return results
