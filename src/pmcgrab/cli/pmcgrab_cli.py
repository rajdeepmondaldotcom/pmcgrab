from __future__ import annotations

"""Minimal CLI wrapper around pmcgrab batch processing.

Example usage:

    python -m pmcgrab.cli.pmcgrab_cli --ids 12345 67890 --out ./data
"""

import argparse
import json
import os
from pathlib import Path
from typing import List

from tqdm import tqdm

from pmcgrab.application.processing import process_pmc_ids


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Batch download & parse PMC articles")
    p.add_argument("--ids", nargs="+", help="List of PMCIDs to process", required=True)
    p.add_argument("--out", default="./pmc_output", help="Output directory for JSON files")
    p.add_argument("--workers", type=int, default=16, help="Thread-pool size")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    pmc_ids: List[str] = args.ids
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    bar = tqdm(total=len(pmc_ids), desc="Processing PMC IDs", unit="paper")
    for chunk_start in range(0, len(pmc_ids), 100):
        chunk = pmc_ids[chunk_start : chunk_start + 100]
        chunk_results = process_pmc_ids(chunk, workers=args.workers)
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
