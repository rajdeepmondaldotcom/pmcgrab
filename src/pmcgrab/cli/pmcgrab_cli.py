from __future__ import annotations

"""Minimal CLI wrapper around pmcgrab batch processing.

Example usage:

    python -m pmcgrab.cli.pmcgrab_cli --ids 12345 67890 --out ./data
"""

import argparse
import json
from pathlib import Path

from tqdm import tqdm

from pmcgrab.application.processing import process_pmc_ids


def _parse_args() -> argparse.Namespace:
    """Return parsed command-line arguments.

    The CLI keeps backward-compatibility with both the **new** (short) flag names
    and the legacy ones expected by the comprehensive test-suite.
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
                # assuming process_single_pmc already wrote the file via higher-level call
                pass
            results[pid] = success
            bar.update(1)
    bar.close()

    summary_path = out_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as jf:
        json.dump(results, jf, indent=2)
    print(f"Summary written to {summary_path}")


if __name__ == "__main__":
    main()
