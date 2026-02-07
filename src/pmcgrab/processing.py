"""Legacy batch processing interface with UI components.

This module provides the original batch processing interface for PMCGrab with
progress bars, console output, and file I/O handling. It's maintained for
backward compatibility with existing scripts and applications.

.. deprecated::
    New applications should use :mod:`pmcgrab.application.processing` for
    cleaner application-layer functions without UI dependencies.

Key Functions:
    process_single_pmc: Legacy single article processing with UI feedback
    process_pmc_ids_in_batches: Concurrent batch processing with progress tracking
    process_in_batches: Sequential chunk processing with console output
    process_in_batches_with_retry: Batch processing with automatic retry logic
"""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

# Delegate to the application-layer implementation instead of duplicating code.
from pmcgrab.application.processing import process_single_pmc as _app_process_single


def process_single_pmc(pmc_id: str) -> dict[str, str | dict | list] | None:
    """Legacy single PMC article processing function.

    Backward-compatible wrapper that delegates to the application-layer
    implementation.

    Args:
        pmc_id: String representation of the PMC ID (e.g., "7181753")

    Returns:
        dict | None: Normalized article dictionary, or None on failure.

    Note:
        For new applications, use
        :func:`pmcgrab.application.processing.process_single_pmc` directly.
    """
    return _app_process_single(pmc_id)


def process_pmc_ids_in_batches(
    pmc_ids: list[str],
    base_directory: str | None = None,
    batch_size: int = 16,
):
    """Process multiple PMC IDs concurrently with progress tracking and file output.

    Args:
        pmc_ids: List of PMC ID strings to process concurrently
        base_directory: Target directory for JSON output files. If None, no files written.
        batch_size: Number of concurrent worker threads (default: 16)

    Returns:
        dict[str, bool]: Mapping from PMC ID to processing success status.
    """

    def _wrapper(pmc_id: str):
        info = _app_process_single(pmc_id)
        if base_directory and info:
            file_path = os.path.join(base_directory, f"PMC{pmc_id}.json")
            with open(file_path, "w", encoding="utf-8") as jf:
                json.dump(info, jf, ensure_ascii=False, indent=4, default=str)
        return pmc_id, info is not None

    results: dict[str, bool] = {}
    total_processed = 0
    successful = 0
    failed = 0
    start_time = time.time()
    custom_bar_format = (
        "{l_bar}{bar} | {n_fmt}/{total_fmt} "
        "[elapsed: {elapsed} | remaining: {remaining}] {postfix}"
    )
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
        futures = {executor.submit(_wrapper, pmc_id): pmc_id for pmc_id in pmc_ids}
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

    Args:
        pmc_ids: List or iterable of PMC ID strings to process
        base_directory: Directory path for JSON output files
        chunk_size: Maximum number of PMC IDs per processing chunk (default: 100)
        parallel_workers: Number of concurrent threads per chunk (default: 16)
    """
    total_chunks = (len(pmc_ids) + chunk_size - 1) // chunk_size
    for chunk_index in range(total_chunks):
        chunk = pmc_ids[chunk_index * chunk_size : (chunk_index + 1) * chunk_size]
        print(f"\n=== Processing Batch {chunk_index + 1} of {total_chunks} ===")
        print(f"Working on {len(chunk)} papers. Please wait...")
        process_pmc_ids_in_batches(chunk, base_directory, batch_size=parallel_workers)
        print(f"Batch {chunk_index + 1} complete!")


def _check_output_file(base_directory: str, pmc_id: str) -> bool:
    """Check if an output file exists and has valid body content."""
    file_path = os.path.join(base_directory, f"PMC{pmc_id}.json")
    if not os.path.exists(file_path):
        return False
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        return bool(data.get("body"))
    except Exception:
        return False


def process_in_batches_with_retry(
    pmc_ids, base_directory, chunk_size=100, parallel_workers=16, max_retries=3
):
    """Robust batch processing with automatic failure detection and retry logic.

    Args:
        pmc_ids: List or iterable of PMC ID strings to process
        base_directory: Directory path for JSON output files
        chunk_size: Number of PMC IDs per processing chunk (default: 100)
        parallel_workers: Number of concurrent threads per chunk (default: 16)
        max_retries: Maximum number of retry attempts for failed articles (default: 3)
    """
    print("\n=== Initial Processing ===")
    print(f"Total papers to process: {len(pmc_ids)}")
    process_in_batches(pmc_ids, base_directory, chunk_size, parallel_workers)

    # Identify failures using consistent filename pattern (PMC{id}.json)
    remaining_ids = {
        pmc_id for pmc_id in pmc_ids if not _check_output_file(base_directory, pmc_id)
    }

    if not remaining_ids:
        print(
            "\nCongratulations! All papers were processed successfully "
            "on the initial attempt!"
        )
        return

    for attempt in range(1, max_retries + 1):
        print(f"\n*** Retry Attempt {attempt} of {max_retries} ***")
        print(
            f"Retrying processing for {len(remaining_ids)} paper(s) "
            f"that failed or have missing content..."
        )
        process_in_batches(
            list(remaining_ids), base_directory, chunk_size, parallel_workers
        )

        remaining_ids = {
            pmc_id
            for pmc_id in remaining_ids
            if not _check_output_file(base_directory, pmc_id)
        }
        print(
            f"After retry attempt {attempt}, {len(remaining_ids)} paper(s) "
            f"still failed or have empty content."
        )
        if not remaining_ids:
            print(
                "\nCongratulations! All previously failed papers "
                "have now been successfully processed!"
            )
            return

    if remaining_ids:
        print(
            "\nUnfortunately, the following PMCID(s) could not be "
            "processed after all attempts:"
        )
        for pmc in remaining_ids:
            print(f"  - {pmc}")
    else:
        print("\nCongratulations! All papers have been successfully processed!")
