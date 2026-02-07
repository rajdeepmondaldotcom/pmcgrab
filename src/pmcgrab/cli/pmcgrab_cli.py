from __future__ import annotations

"""Command-line interface for batch PMC article processing.

This module provides a minimal but complete CLI wrapper around PMCGrab's
batch processing capabilities.  It supports:

* **Network mode** (``--pmcids``): downloading and parsing multiple PMC
  articles concurrently from NCBI Entrez.
* **Local file mode** (``--from-file`` / ``--from-dir``): parsing pre-downloaded
  JATS XML files from disk, which is orders of magnitude faster.

Example usage:
    Batch download from NCBI::

        pmcgrab --pmcids 7181753 3539614 --output-dir ./results

    Parse local XML files::

        pmcgrab --from-dir ./pmc_bulk_xml --output-dir ./results
        pmcgrab --from-file article1.xml article2.xml --output-dir ./results
"""

import argparse
import json
from pathlib import Path

from tqdm import tqdm

from pmcgrab.application.processing import (
    process_local_xml_dir,
    process_single_local_xml,
    process_single_pmc,
)


def _parse_args() -> argparse.Namespace:
    """Parse and validate command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    p = argparse.ArgumentParser(
        description="Batch download & parse PMC articles (from network or local XML)"
    )

    # --- Input sources (mutually exclusive) ---
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--pmcids",
        "--ids",
        nargs="+",
        dest="pmcids",
        help="PMC IDs to download and process from NCBI",
    )
    src.add_argument(
        "--from-dir",
        dest="from_dir",
        help="Directory of JATS XML files to process (bulk mode)",
    )
    src.add_argument(
        "--from-file",
        nargs="+",
        dest="from_files",
        help="One or more local JATS XML files to process",
    )

    # --- Output directory ---
    p.add_argument(
        "--output-dir",
        "--out",
        dest="output_dir",
        default="./pmc_output",
        help="Output directory for JSON files (default: ./pmc_output)",
    )

    # --- Worker threads ---
    p.add_argument(
        "--batch-size",
        "--workers",
        dest="batch_size",
        type=int,
        default=10,
        help="Number of worker threads (default: 10)",
    )

    return p.parse_args()


def main() -> None:
    """Main CLI entry point for batch PMC article processing."""
    args = _parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, bool] = {}

    # -----------------------------------------------------------------
    # Local directory mode
    # -----------------------------------------------------------------
    if args.from_dir:
        dir_path = Path(args.from_dir)
        if not dir_path.is_dir():
            print(f"Error: {dir_path} is not a directory")
            return

        xml_files = sorted(dir_path.glob("*.xml"))
        if not xml_files:
            print(f"No XML files found in {dir_path}")
            return

        bar = tqdm(total=len(xml_files), desc="Processing local XML", unit="file")
        parsed = process_local_xml_dir(dir_path, workers=args.batch_size)
        for name, data in parsed.items():
            success = data is not None
            if success and data is not None:
                dest = out_dir / f"{name}.json"
                with dest.open("w", encoding="utf-8") as fh:
                    json.dump(data, fh, indent=2, ensure_ascii=False)
            results[name] = success
            bar.update(1)
        bar.close()

    # -----------------------------------------------------------------
    # Local file(s) mode
    # -----------------------------------------------------------------
    elif args.from_files:
        bar = tqdm(total=len(args.from_files), desc="Processing local XML", unit="file")
        for xml_path in args.from_files:
            fp = Path(xml_path)
            data = process_single_local_xml(fp)
            name = fp.stem
            success = data is not None
            if success and data is not None:
                dest = out_dir / f"{name}.json"
                with dest.open("w", encoding="utf-8") as fh:
                    json.dump(data, fh, indent=2, ensure_ascii=False)
            results[name] = success
            bar.update(1)
        bar.close()

    # -----------------------------------------------------------------
    # Network mode (PMC IDs)
    # -----------------------------------------------------------------
    else:
        pmc_ids: list[str] = args.pmcids
        bar = tqdm(total=len(pmc_ids), desc="Processing PMC IDs", unit="paper")
        for pid in pmc_ids:
            data = process_single_pmc(pid)
            success = data is not None
            if success and data is not None:
                dest = out_dir / f"PMC{pid}.json"
                with dest.open("w", encoding="utf-8") as fh:
                    json.dump(data, fh, indent=2, ensure_ascii=False)
            results[pid] = success
            bar.update(1)
        bar.close()

    # -----------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------
    summary_path = out_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as jf:
        json.dump(results, jf, indent=2)

    total = len(results)
    ok = sum(1 for v in results.values() if v)
    print(f"\nDone: {ok}/{total} succeeded.  Summary written to {summary_path}")


if __name__ == "__main__":
    main()
