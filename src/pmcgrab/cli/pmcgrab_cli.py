from __future__ import annotations

"""Command-line interface for batch PMC article processing.

This module provides a minimal but complete CLI wrapper around PMCGrab's
batch processing capabilities. It supports downloading and parsing multiple
PMC articles concurrently with configurable worker threads and output
directory specification.

The CLI maintains backward compatibility with legacy flag names while
supporting modern short flag alternatives. It processes articles in
manageable chunks to avoid memory issues with large batches and provides
progress tracking with detailed statistics.

Key Features:
    * Concurrent processing with configurable worker threads
    * Progress tracking with success/failure statistics
    * Chunked processing for memory efficiency
    * JSON output with summary statistics
    * Backward-compatible flag names

Example usage:
    Basic batch processing:
        python -m pmcgrab.cli.pmcgrab_cli --pmcids 7181753 3539614 --output-dir ./results

    With custom worker count:
        python -m pmcgrab.cli.pmcgrab_cli --pmcids 7181753 3539614 --batch-size 20

    Legacy flag compatibility:
        python -m pmcgrab.cli.pmcgrab_cli --ids 7181753 3539614 --out ./data
"""

import argparse
import json
from pathlib import Path

from tqdm import tqdm

from pmcgrab.application.processing import process_pmc_ids, process_single_pmc


def _parse_args() -> argparse.Namespace:
    """Parse and validate command-line arguments with legacy compatibility.

    Configures argument parser with support for both modern and legacy flag
    names to ensure backward compatibility with existing scripts and test suites.
    Provides sensible defaults for batch processing operations.

    Returns:
        argparse.Namespace: Parsed arguments containing:
            - pmcids: List of PMC IDs to process
            - output_dir: Target directory for JSON output files
            - batch_size: Number of concurrent worker threads

    Examples:
        Command line inputs that this function handles:
            --pmcids 7181753 3539614 --output-dir ./results --batch-size 10
            --ids 7181753 3539614 --out ./data --workers 5  # Legacy format

    Note:
        Both modern (--pmcids, --output-dir, --batch-size) and legacy
        (--ids, --out, --workers) flag names are supported for the same
        functionality to maintain backward compatibility.
    """
    p = argparse.ArgumentParser(description="Batch download & parse PMC articles")
    # Support both –pmcids and –ids (legacy)
    p.add_argument(
        "--pmcids",
        "--ids",
        nargs="+",
        dest="pmcids",
        required=True,
        help="List of PMCIDs to process",
    )
    # Output directory
    p.add_argument(
        "--output-dir",
        "--out",
        dest="output_dir",
        default="./pmc_output",
        help="Output directory for JSON files",
    )
    # Batch size / worker threads
    p.add_argument(
        "--batch-size",
        "--workers",
        dest="batch_size",
        type=int,
        default=10,
        help="Number of worker threads",
    )
    return p.parse_args()


def main() -> None:
    """Main CLI entry point for batch PMC article processing.

    Orchestrates the complete batch processing workflow:
    1. Parse command-line arguments
    2. Create output directory structure
    3. Process PMC IDs in manageable chunks with progress tracking
    4. Collect and report processing statistics
    5. Write summary results to JSON file

    The function processes articles in 100-article chunks to manage memory
    usage and provide regular progress updates. Each chunk is processed
    concurrently using the specified number of worker threads.

    Output:
        Creates individual JSON files for each successfully processed article
        in the output directory, plus a summary.json file containing processing
        statistics for all articles.

    Examples:
        This function is typically called via:
            python -m pmcgrab.cli.pmcgrab_cli --pmcids 7181753 3539614

    Note:
        The function assumes that process_pmc_ids() handles the actual file
        writing for individual articles. It focuses on orchestration,
        progress tracking, and summary generation.
    """
    args = _parse_args()
    pmc_ids: list[str] = args.pmcids
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    bar = tqdm(total=len(pmc_ids), desc="Processing PMC IDs", unit="paper")
    for chunk_start in range(0, len(pmc_ids), 100):
        chunk = pmc_ids[chunk_start : chunk_start + 100]
        chunk_results = process_pmc_ids(chunk, batch_size=args.batch_size)
        for pid, success in chunk_results.items():
            if success:
                # Fetch data and write JSON
                article_data = process_single_pmc(pid)
                if article_data is not None:
                    dest = out_dir / f"PMC{pid}.json"
                    with dest.open("w", encoding="utf-8") as fh:
                        json.dump(article_data, fh, indent=2, ensure_ascii=False)
                else:
                    success = False
            results[pid] = success
            bar.update(1)
    bar.close()

    summary_path = out_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as jf:
        json.dump(results, jf, indent=2)
    print(f"Summary written to {summary_path}")


if __name__ == "__main__":
    main()
