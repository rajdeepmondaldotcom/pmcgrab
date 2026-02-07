from __future__ import annotations

"""Command-line interface for batch PMC article processing.

This module provides a minimal but complete CLI wrapper around PMCGrab's
batch processing capabilities.  It supports:

* **Network mode** (``--pmcids``): downloading and parsing multiple PMC
  articles concurrently from NCBI Entrez.
* **PMID mode** (``--pmids``): auto-convert PubMed IDs to PMC IDs.
* **DOI mode** (``--dois``): auto-convert DOIs to PMC IDs.
* **ID file mode** (``--from-id-file``): read IDs from a text file.
* **Local file mode** (``--from-file`` / ``--from-dir``): parsing pre-downloaded
  JATS XML files from disk, which is orders of magnitude faster.

Example usage:
    Batch download from NCBI::

        pmcgrab --pmcids 7181753 3539614 --output-dir ./results
        pmcgrab --pmcids PMC7181753 pmc3539614  # flexible ID formats

    Convert PMIDs first::

        pmcgrab --pmids 33087749 34567890 --output-dir ./results

    Convert DOIs first::

        pmcgrab --dois 10.1038/s41586-020-2832-5 --output-dir ./results

    Read IDs from a file::

        pmcgrab --from-id-file ids.txt --output-dir ./results

    Parse local XML files::

        pmcgrab --from-dir ./pmc_bulk_xml --output-dir ./results
        pmcgrab --from-file article1.xml article2.xml --output-dir ./results
"""

import argparse
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tqdm import tqdm

from pmcgrab.application.processing import (
    process_local_xml_dir,
    process_single_local_xml,
    process_single_pmc,
)
from pmcgrab.idconvert import normalize_id, normalize_pmid


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
        help="PMC IDs to download and process (accepts PMC7181753, pmc7181753, 7181753)",
    )
    src.add_argument(
        "--pmids",
        nargs="+",
        dest="pmids",
        help="PubMed IDs to auto-convert to PMC IDs and process",
    )
    src.add_argument(
        "--dois",
        nargs="+",
        dest="dois",
        help="DOIs to auto-convert to PMC IDs and process",
    )
    src.add_argument(
        "--from-id-file",
        dest="from_id_file",
        help="Text file with one ID per line (PMCIDs, PMIDs, or DOIs)",
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

    # --- Output format ---
    p.add_argument(
        "--format",
        dest="output_format",
        choices=["json", "jsonl"],
        default="json",
        help="Output format: json (one file per article) or jsonl (all in one file)",
    )

    # --- Verbosity ---
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose/debug logging",
    )
    p.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress progress bars (useful for piped output)",
    )

    return p.parse_args()


def _resolve_ids_from_file(filepath: str) -> list[str]:
    """Read IDs from a text file and normalize them to PMCIDs."""
    path = Path(filepath)
    if not path.is_file():
        print(f"Error: {path} is not a file", file=sys.stderr)
        return []
    raw_ids = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            raw_ids.append(line)
    resolved = []
    for raw_id in raw_ids:
        try:
            resolved.append(normalize_id(raw_id))
        except ValueError as e:
            print(f"Warning: {e}", file=sys.stderr)
    return resolved


def _write_result(data: dict, name: str, out_dir: Path, fmt: str, jsonl_fh=None):
    """Write a single result in the chosen format."""
    if fmt == "jsonl" and jsonl_fh is not None:
        jsonl_fh.write(json.dumps(data, ensure_ascii=False) + "\n")
    else:
        dest = out_dir / f"{name}.json"
        with dest.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)


def main() -> None:
    """Main CLI entry point for batch PMC article processing."""
    args = _parse_args()

    # --- Configure logging ---
    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG, format="%(name)s %(levelname)s: %(message)s"
        )
    else:
        logging.basicConfig(level=logging.WARNING)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, bool] = {}
    disable_bar = args.quiet
    jsonl_fh = None
    if args.output_format == "jsonl":
        jsonl_fh = (out_dir / "output.jsonl").open("w", encoding="utf-8")

    try:
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

            bar = tqdm(
                total=len(xml_files),
                desc="Processing local XML",
                unit="file",
                disable=disable_bar,
            )
            parsed = process_local_xml_dir(dir_path, workers=args.batch_size)
            for name, data in parsed.items():
                success = data is not None
                if success and data is not None:
                    _write_result(data, name, out_dir, args.output_format, jsonl_fh)
                results[name] = success
                bar.update(1)
            bar.close()

        # -----------------------------------------------------------------
        # Local file(s) mode
        # -----------------------------------------------------------------
        elif args.from_files:
            bar = tqdm(
                total=len(args.from_files),
                desc="Processing local XML",
                unit="file",
                disable=disable_bar,
            )
            for xml_path in args.from_files:
                fp = Path(xml_path)
                data = process_single_local_xml(fp)
                name = fp.stem
                success = data is not None
                if success and data is not None:
                    _write_result(data, name, out_dir, args.output_format, jsonl_fh)
                results[name] = success
                bar.update(1)
            bar.close()

        # -----------------------------------------------------------------
        # Network mode -- resolve IDs and process concurrently
        # -----------------------------------------------------------------
        else:
            # Resolve IDs from various sources
            pmc_ids: list[str] = []

            if args.pmcids:
                for raw_id in args.pmcids:
                    try:
                        pmc_ids.append(normalize_id(raw_id))
                    except ValueError as e:
                        print(f"Warning: {e}", file=sys.stderr)

            elif args.pmids:
                for pmid in args.pmids:
                    try:
                        pmc_ids.append(normalize_pmid(pmid))
                    except ValueError as e:
                        print(f"Warning: {e}", file=sys.stderr)

            elif args.dois:
                for doi in args.dois:
                    try:
                        pmc_ids.append(normalize_id(doi))
                    except ValueError as e:
                        print(f"Warning: {e}", file=sys.stderr)

            elif args.from_id_file:
                pmc_ids = _resolve_ids_from_file(args.from_id_file)

            if not pmc_ids:
                print("No valid PMC IDs to process.", file=sys.stderr)
                return

            # Process concurrently using ThreadPoolExecutor
            bar = tqdm(
                total=len(pmc_ids),
                desc="Processing PMC IDs",
                unit="paper",
                disable=disable_bar,
            )
            with ThreadPoolExecutor(max_workers=args.batch_size) as executor:
                future_to_pid = {
                    executor.submit(process_single_pmc, pid): pid for pid in pmc_ids
                }
                for future in as_completed(future_to_pid):
                    pid = future_to_pid[future]
                    try:
                        data = future.result()
                    except Exception:
                        data = None
                    success = data is not None
                    if success and data is not None:
                        _write_result(
                            data, f"PMC{pid}", out_dir, args.output_format, jsonl_fh
                        )
                    results[pid] = success
                    bar.update(1)
            bar.close()

    finally:
        if jsonl_fh is not None:
            jsonl_fh.close()

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
