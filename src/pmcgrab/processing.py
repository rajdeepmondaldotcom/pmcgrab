"""Legacy batch processing interface with UI components.

This module provides the original batch processing interface for PMCGrab with
progress bars, console output, and file I/O handling. It's maintained for
backward compatibility with existing scripts and applications.

The functions in this module include user interface elements (tqdm progress bars,
print statements) and handle direct file writing, making them suitable for
interactive use and existing automation scripts. For new applications, consider
using the cleaner application-layer functions in pmcgrab.application.processing.

Key Functions:
    process_single_pmc: Legacy single article processing with UI feedback
    process_pmc_ids_in_batches: Concurrent batch processing with progress tracking
    process_in_batches: Sequential chunk processing with console output
    process_in_batches_with_retry: Batch processing with automatic retry logic

Note:
    This module is deprecated but maintained for backward compatibility.
    New applications should use pmcgrab.application.processing for cleaner
    application-layer functions without UI dependencies.
"""

import contextlib
import gc
import json
import os
import signal
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

# Deprecated – left for backwards compatibility. Delegates to application layer.
from pmcgrab.common.serialization import normalize_value
from pmcgrab.constants import TimeoutException


# Re-export the legacy function with the expected name for backwards compatibility
def process_single_pmc(pmc_id: str) -> dict[str, str | dict | list] | None:
    """Legacy single PMC article processing function.

    Backward-compatible wrapper that delegates to the internal legacy implementation.
    This function is maintained for compatibility with existing scripts and applications
    that rely on the original pmcgrab API.

    Args:
        pmc_id: String representation of the PMC ID (e.g., "7181753")

    Returns:
        Optional[dict[str, Union[str, dict, list]]]: Normalized article dictionary
                                                     or None if processing fails

    Examples:
        >>> result = process_single_pmc("7181753")
        >>> if result:
        ...     print(f"Title: {result['title']}")
        ...     print(f"Body sections: {list(result['body'].keys())}")

    Note:
        For new applications, consider using pmcgrab.application.processing.process_single_pmc
        which provides cleaner separation of concerns without UI dependencies.
    """
    return _legacy_process_single_pmc(pmc_id)


def _legacy_process_single_pmc(
    pmc_id: str,
) -> dict[str, str | dict | list] | None:
    """Internal legacy implementation for single PMC article processing.

    Downloads, parses, and normalizes a single PMC article with timeout protection
    and comprehensive error handling. Includes extensive normalization of all
    article metadata and content for JSON serialization compatibility.

    Args:
        pmc_id: String representation of the PMC ID

    Returns:
        Optional[dict[str, Union[str, dict, list]]]: Comprehensive article dictionary
                                                     with normalized values, or None if:
                                                     - Network/parsing errors occur
                                                     - Article has no usable body content
                                                     - Timeout exceeded (60 seconds)

    The returned dictionary includes:
        - pmc_id: Article identifier
        - title: Article title
        - abstract: Plain text abstract
        - body: Dictionary mapping section titles to text content
        - authors: Normalized author information
        - All journal and publication metadata
        - Content metadata (funding, ethics, etc.)

    Note:
        This function includes a 60-second timeout, memory management via garbage
        collection, and handles pandas DataFrame serialization issues. All values
        are normalized for JSON compatibility.
    """
    gc.collect()
    paper_info: dict[str, str | dict | list] = {}
    body_info: dict[str, str] = {}
    p_obj = None
    try:
        pmc_id_num = int(pmc_id)
        from pmcgrab.infrastructure.settings import next_email

        current_email = next_email()
        signal.alarm(60)
        try:
            from pmcgrab.application.paper_builder import build_paper_from_pmc

            p_obj = build_paper_from_pmc(
                pmc_id_num, email=current_email, download=True, validate=False
            )
        except TimeoutException:
            return None
        finally:
            signal.alarm(0)
        if p_obj is None:
            return None
        # Handle body sections safely to avoid pandas DataFrame boolean evaluation issues
        body_sections = p_obj.body
        if body_sections is not None:
            try:
                # Test if we can iterate over it (handles pandas objects)
                iter(body_sections)  # Just test iterability
                sec_counter = 1
                for section in body_sections:
                    try:
                        text = getattr(
                            section, "get_section_text", lambda s=section: str(s)
                        )()
                        title = (
                            section.title
                            if (hasattr(section, "title") and section.title is not None)
                            else f"Section {sec_counter}"
                        )
                        sec_counter += 1
                        body_info[title] = text
                    except Exception:
                        pass
            except (TypeError, ValueError):
                # Skip body processing if it's not iterable
                pass
        paper_info["pmc_id"] = str(pmc_id_num)
        paper_info["abstract"] = (
            p_obj.abstract_as_str() if p_obj.abstract is not None else ""
        )
        paper_info["has_data"] = (
            str(p_obj.has_data) if p_obj.has_data is not None else ""
        )
        paper_info["body"] = body_info if body_info else {}
        paper_info["title"] = p_obj.title if p_obj.title is not None else ""
        paper_info["authors"] = (
            normalize_value(p_obj.authors) if p_obj.authors is not None else ""
        )
        paper_info["non_author_contributors"] = (
            normalize_value(p_obj.non_author_contributors)
            if p_obj.non_author_contributors is not None
            else ""
        )
        paper_info["publisher_name"] = (
            normalize_value(p_obj.publisher_name)
            if p_obj.publisher_name is not None
            else ""
        )
        paper_info["publisher_location"] = (
            normalize_value(p_obj.publisher_location)
            if p_obj.publisher_location is not None
            else ""
        )
        paper_info["article_id"] = (
            normalize_value(p_obj.article_id) if p_obj.article_id is not None else ""
        )
        paper_info["journal_title"] = (
            normalize_value(p_obj.journal_title)
            if p_obj.journal_title is not None
            else ""
        )
        paper_info["journal_id"] = (
            normalize_value(p_obj.journal_id) if p_obj.journal_id is not None else ""
        )
        paper_info["issn"] = (
            normalize_value(p_obj.issn) if p_obj.issn is not None else ""
        )
        paper_info["article_types"] = (
            normalize_value(p_obj.article_types)
            if p_obj.article_types is not None
            else ""
        )
        paper_info["article_categories"] = (
            normalize_value(p_obj.article_categories)
            if p_obj.article_categories is not None
            else ""
        )
        paper_info["published_date"] = (
            normalize_value(p_obj.published_date)
            if p_obj.published_date is not None
            else ""
        )
        paper_info["volume"] = (
            normalize_value(p_obj.volume) if p_obj.volume is not None else ""
        )
        paper_info["issue"] = (
            normalize_value(p_obj.issue) if p_obj.issue is not None else ""
        )
        paper_info["permissions"] = (
            normalize_value(p_obj.permissions) if p_obj.permissions is not None else ""
        )
        paper_info["copyright"] = (
            normalize_value(p_obj.copyright) if p_obj.copyright is not None else ""
        )
        paper_info["license"] = (
            normalize_value(p_obj.license) if p_obj.license is not None else ""
        )
        paper_info["funding"] = (
            normalize_value(p_obj.funding) if p_obj.funding is not None else ""
        )
        paper_info["footnote"] = (
            normalize_value(p_obj.footnote) if p_obj.footnote is not None else ""
        )
        paper_info["acknowledgements"] = (
            normalize_value(p_obj.acknowledgements)
            if p_obj.acknowledgements is not None
            else ""
        )
        paper_info["notes"] = (
            normalize_value(p_obj.notes) if p_obj.notes is not None else ""
        )
        paper_info["custom_meta"] = (
            normalize_value(p_obj.custom_meta) if p_obj.custom_meta is not None else ""
        )
        paper_info["last_updated"] = (
            normalize_value(p_obj.last_updated)
            if hasattr(p_obj, "last_updated")
            else ""
        )
        paper_info = {k: normalize_value(v) for k, v in paper_info.items()}
        if not paper_info or not paper_info.get("body") or paper_info.get("body") == {}:
            return None
        return paper_info
    except Exception:
        return None
    finally:
        with contextlib.suppress(Exception):
            del paper_info, body_info, p_obj
        gc.collect()
    return None


def process_pmc_ids_in_batches(
    pmc_ids: list[str],
    base_directory: str | None = None,
    batch_size: int = 16,
):
    """Process multiple PMC IDs concurrently with progress tracking and file output.

    Legacy batch processing function that provides concurrent article processing
    with real-time progress tracking via tqdm progress bars and automatic JSON
    file writing. Includes detailed statistics on success rates and processing times.

    Args:
        pmc_ids: List of PMC ID strings to process concurrently
        base_directory: Target directory for JSON output files. If None, no files written.
                       Files are named as "PMC{id}.json" (e.g., "PMC7181753.json")
        batch_size: Number of concurrent worker threads (default: 16)

    Returns:
        dict[str, bool]: Mapping from PMC ID to processing success status
                        (True for success, False for failure)

    Features:
        * Real-time progress bar with success/failure statistics
        * Concurrent processing with configurable worker threads
        * Automatic JSON file writing with UTF-8 encoding
        * Memory management and error isolation per article
        * Detailed timing statistics and success rate tracking

    Examples:
        >>> # Process with file output and progress tracking
        >>> ids = ["7181753", "3539614", "5454911"]
        >>> results = process_pmc_ids_in_batches(ids, "./output", batch_size=8)
        >>> successful = sum(results.values())
        >>> print(f"Successfully processed {successful}/{len(ids)} articles")
        >>>
        >>> # Process without file output (testing/validation)
        >>> results = process_pmc_ids_in_batches(ids, base_directory=None)

    Note:
        This function includes user interface elements (progress bars) and file I/O.
        For headless applications, consider using pmcgrab.application.processing.process_pmc_ids
        which provides the same functionality without UI dependencies.
    """

    def process_single_pmc_wrapper(pmc_id: str):
        info = _legacy_process_single_pmc(pmc_id)
        if base_directory and info:
            file_path = os.path.join(base_directory, f"PMC{pmc_id}.json")
            with open(file_path, "w", encoding="utf-8") as jf:
                json.dump(info, jf, ensure_ascii=False, indent=4, default=str)
        return pmc_id, info is not None

    results: dict[str, dict[str, str | dict | list] | None] = {}
    total_processed = 0
    successful = 0
    failed = 0
    start_time = time.time()
    custom_bar_format = "{l_bar}{bar} | {n_fmt}/{total_fmt} [elapsed: {elapsed} | remaining: {remaining}] {postfix}"
    with (
        tqdm(
            total=len(pmc_ids),
            desc="Processing PMC IDs",
            unit="paper",
            bar_format=custom_bar_format,
            dynamic_ncols=True,
        ) as pbar,
        ThreadPoolExecutor(max_workers=batch_size) as executor,
    ):
        futures = {
            executor.submit(process_single_pmc_wrapper, pmc_id): pmc_id
            for pmc_id in pmc_ids
        }
        for future in as_completed(futures):
            try:
                pmcid, success = future.result()
                results[pmcid] = success
                if success:
                    successful += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
            total_processed += 1
            elapsed = time.time() - start_time
            avg_time = elapsed / total_processed if total_processed else 0
            pbar.set_postfix(
                {
                    "Success": f"{successful}",
                    "Failed": f"{failed}",
                    "Success Rate": f"{(successful / total_processed) * 100:.1f}%",
                    "Avg Time": f"{avg_time:.2f}s",
                }
            )
            pbar.update(1)

    return results


def process_in_batches(pmc_ids, base_directory, chunk_size=100, parallel_workers=16):
    """Process large PMC ID collections in manageable sequential chunks.

    High-level batch processing function that divides large PMC ID collections
    into smaller chunks for memory-efficient processing. Each chunk is processed
    concurrently with detailed console feedback and progress tracking.

    This approach prevents memory exhaustion with very large datasets while
    maintaining the benefits of concurrent processing within each chunk.

    Args:
        pmc_ids: List or iterable of PMC ID strings to process
        base_directory: Directory path for JSON output files
        chunk_size: Maximum number of PMC IDs per processing chunk (default: 100)
        parallel_workers: Number of concurrent threads per chunk (default: 16)

    Output:
        Prints detailed progress information to console including:
        * Batch progress (e.g., "Processing Batch 1 of 5")
        * Article counts per batch
        * Completion notifications

    Examples:
        >>> # Process 500 articles in chunks of 50 with 8 workers each
        >>> pmc_ids = [str(i) for i in range(7181753, 7182253)]
        >>> process_in_batches(pmc_ids, "./output", chunk_size=50, parallel_workers=8)
        # Output:
        # === Processing Batch 1 of 10 ===
        # Working on 50 papers. Please wait...
        # Batch 1 complete!
        # ...

    Note:
        This function is designed for interactive use with console output.
        Each chunk is processed independently, providing natural breakpoints
        for very large datasets. Files are written as "PMC{id}.json" in the
        specified directory.
    """
    total_chunks = (len(pmc_ids) + chunk_size - 1) // chunk_size
    for chunk_index in range(total_chunks):
        chunk = pmc_ids[chunk_index * chunk_size : (chunk_index + 1) * chunk_size]
        print(f"\n=== Processing Batch {chunk_index + 1} of {total_chunks} ===")
        print(f"Working on {len(chunk)} papers. Please wait...")
        process_pmc_ids_in_batches(chunk, base_directory, batch_size=parallel_workers)
        print(f"Batch {chunk_index + 1} complete!")


def process_in_batches_with_retry(
    pmc_ids, base_directory, chunk_size=100, parallel_workers=16, max_retries=3
):
    """Robust batch processing with automatic failure detection and retry logic.

    Advanced batch processing function that ensures maximum success rates by
    automatically detecting failed or incomplete processing attempts and
    retrying them. Validates output files for both existence and content
    quality (non-empty body sections).

    The function performs comprehensive failure detection by checking:
    * File existence in the output directory
    * Valid JSON structure in output files
    * Non-empty body content in parsed articles

    Args:
        pmc_ids: List or iterable of PMC ID strings to process
        base_directory: Directory path for JSON output files
        chunk_size: Number of PMC IDs per processing chunk (default: 100)
        parallel_workers: Number of concurrent threads per chunk (default: 16)
        max_retries: Maximum number of retry attempts for failed articles (default: 3)

    Processing Flow:
        1. Initial batch processing of all PMC IDs
        2. Validation of output files and content quality
        3. Identification of failed/incomplete articles
        4. Retry processing for failed articles (up to max_retries attempts)
        5. Final reporting of any permanently failed articles

    Console Output:
        Provides detailed progress reporting including:
        * Initial processing statistics
        * Retry attempt progress with remaining failure counts
        * Final success/failure summary
        * List of any permanently failed PMC IDs

    Examples:
        >>> # Process with retry for maximum reliability
        >>> pmc_ids = ["7181753", "3539614", "5454911", "invalid_id"]
        >>> process_in_batches_with_retry(
        ...     pmc_ids, "./output",
        ...     chunk_size=50,
        ...     parallel_workers=8,
        ...     max_retries=5
        ... )
        # Output:
        # === Initial Processing ===
        # Total papers to process: 4
        # ...
        # *** Retry Attempt 1 of 5 ***
        # Retrying processing for 1 paper(s) that failed...
        # ...

    Note:
        This function is ideal for large-scale processing where maximum
        success rates are important. It automatically handles transient
        network failures, timeout issues, and parsing errors through
        intelligent retry logic.
    """
    print("\n=== Initial Processing ===")
    print(f"Total papers to process: {len(pmc_ids)}")
    process_in_batches(pmc_ids, base_directory, chunk_size, parallel_workers)

    remaining_ids = set()
    for pmc_id in pmc_ids:
        file_path = os.path.join(base_directory, f"PMC{pmc_id}.json")
        if not os.path.exists(file_path):
            remaining_ids.add(pmc_id)
        else:
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
                if not data.get("body") or data.get("body") == {}:
                    remaining_ids.add(pmc_id)
            except Exception:
                remaining_ids.add(pmc_id)

    if not remaining_ids:
        print(
            "\nCongratulations! All papers were processed successfully on the initial attempt!"
        )
        return

    for attempt in range(1, max_retries + 1):
        print(f"\n*** Retry Attempt {attempt} of {max_retries} ***")
        print(
            f"Retrying processing for {len(remaining_ids)} paper(s) that failed or have missing content..."
        )
        process_in_batches(
            list(remaining_ids), base_directory, chunk_size, parallel_workers
        )

        new_remaining = set()
        for pmc_id in remaining_ids:
            file_path = os.path.join(base_directory, f"{pmc_id}.json")
            if not os.path.exists(file_path):
                new_remaining.add(pmc_id)
            else:
                try:
                    with open(file_path, encoding="utf-8") as f:
                        data = json.load(f)
                    if not data.get("body") or data.get("body") == {}:
                        new_remaining.add(pmc_id)
                except Exception:
                    new_remaining.add(pmc_id)
        print(
            f"After retry attempt {attempt}, {len(new_remaining)} paper(s) still failed or have empty content."
        )
        remaining_ids = new_remaining
        if not remaining_ids:
            print(
                "\nCongratulations! All previously failed papers have now been successfully processed!"
            )
            return

    if remaining_ids:
        print(
            "\nUnfortunately, the following PMCID(s) could not be processed after all attempts:"
        )
        for pmc in remaining_ids:
            print(f"  - {pmc}")
    else:
        print("\nCongratulations! All papers have been successfully processed!")
