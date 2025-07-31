import contextlib
import gc
import json
import os
import signal
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Union

from tqdm import tqdm

# Deprecated – left for backwards compatibility. Delegates to application layer.
from pmcgrab.application.processing import process_single_pmc
from pmcgrab.constants import TimeoutException
from pmcgrab.common.serialization import normalize_value


def _legacy_process_single_pmc(
    pmc_id: str,
) -> Optional[dict[str, Union[str, dict, list]]]:
    """Download and parse one PMC article.

    Args:
        pmc_id: String representation of the PMCID.

    Returns:
        Dictionary of normalized article metadata, or ``None`` on failure.
    """
    gc.collect()
    paper_info: dict[str, Union[str, dict, list]] = {}
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
    pmc_ids: list[str], base_directory: str, batch_size: int = 16
):
    """Process PMCIDs concurrently and write results to disk.

    Args:
        pmc_ids: List of PMCIDs to process.
        base_directory: Directory to write JSON outputs.
        batch_size: Number of worker threads to spawn.
    """

    def process_single_pmc_wrapper(pmc_id: str):
        info = process_single_pmc(pmc_id)
        if info:
            file_path = os.path.join(base_directory, f"PMC{pmc_id}.json")
            with open(file_path, "w", encoding="utf-8") as jf:
                json.dump(info, jf, ensure_ascii=False, indent=4, default=str)
        return pmc_id, info is not None

    total_processed = 0
    successful = 0
    failed = 0
    start_time = time.time()
    custom_bar_format = "{l_bar}{bar} | {n_fmt}/{total_fmt} [elapsed: {elapsed} | remaining: {remaining}] {postfix}"
    with tqdm(
        total=len(pmc_ids),
        desc="Processing PMC IDs",
        unit="paper",
        bar_format=custom_bar_format,
        dynamic_ncols=True,
    ) as pbar:
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            futures = {
                executor.submit(process_single_pmc_wrapper, pmc_id): pmc_id
                for pmc_id in pmc_ids
            }
            for future in as_completed(futures):
                try:
                    _, success = future.result()
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


def process_in_batches(pmc_ids, base_directory, chunk_size=100, parallel_workers=16):
    """Process PMCIDs in sequential chunks.

    This is a thin wrapper around :func:`process_pmc_ids_in_batches` that breaks
    the ID list into smaller chunks.

    Args:
        pmc_ids: Iterable of PMCIDs to process.
        base_directory: Output directory for JSON files.
        chunk_size: Number of IDs per batch.
        parallel_workers: Number of threads per batch.
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
    """Attempt batch processing with automatic retries.

    Args:
        pmc_ids: Iterable of PMCIDs to process.
        base_directory: Directory to write JSON files into.
        chunk_size: Number of IDs per processing batch.
        parallel_workers: Worker threads used for each batch.
        max_retries: Maximum number of retry rounds.
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
