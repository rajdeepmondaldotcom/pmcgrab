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
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, TextIO

from tqdm import tqdm

from pmcgrab.application.processing import (
    process_local_xml_dir,
    process_single_local_xml,
    process_single_pmc,
)
from pmcgrab.idconvert import normalize_id, normalize_pmid


def _positive_int(value: str) -> int:
    """Parse a strictly positive integer for worker-count flags."""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _parse_args() -> argparse.Namespace:
    """Parse and validate command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    p = argparse.ArgumentParser(
        prog="pmcgrab",
        description="Batch download & parse PMC articles (from network or local XML)",
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
        help=(
            "Text file with one ID per line. Bare numeric IDs are treated as PMCIDs; "
            "DOIs are converted via NCBI. Use --pmids for PubMed IDs."
        ),
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
        type=_positive_int,
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
    p.add_argument(
        "--schema-version",
        dest="schema_version",
        choices=[2, 3, 4],
        type=int,
        default=4,
        help="Output schema version: 4 (default), 3, or 2 for compatibility",
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
    from pmcgrab import __version__

    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return p.parse_args()


def _schema_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    """Return processing kwargs for non-default schema options."""
    kwargs: dict[str, Any] = {}
    if args.schema_version != 4:
        kwargs["schema_version"] = args.schema_version
    return kwargs


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


def _write_result(
    data: dict, name: str, out_dir: Path, fmt: str, jsonl_fh: TextIO | None = None
) -> None:
    """Write a single result in the chosen format."""
    if fmt == "jsonl" and jsonl_fh is not None:
        jsonl_fh.write(json.dumps(data, ensure_ascii=False, allow_nan=False) + "\n")
    else:
        dest = out_dir / f"{name}.json"
        with dest.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False, allow_nan=False)


def _process_local_directory(
    args: argparse.Namespace, out_dir: Path, jsonl_fh: TextIO | None
) -> dict[str, bool] | None:
    """Process all XML files in a local directory."""
    dir_path = Path(args.from_dir)
    if not dir_path.is_dir():
        print(f"Error: {dir_path} is not a directory", file=sys.stderr)
        return None

    xml_files = sorted(dir_path.glob("*.xml"))
    if not xml_files:
        print(f"No XML files found in {dir_path}", file=sys.stderr)
        return None

    results: dict[str, bool] = {}
    with tqdm(
        total=len(xml_files),
        desc="Processing local XML",
        unit="file",
        disable=args.quiet,
    ) as bar:
        kwargs = _schema_kwargs(args)
        parsed = process_local_xml_dir(dir_path, workers=args.batch_size, **kwargs)
        for name, data in parsed.items():
            success = data is not None
            if success and data is not None:
                _write_result(data, name, out_dir, args.output_format, jsonl_fh)
            results[name] = success
            bar.update(1)
    return results


def _process_local_files(
    args: argparse.Namespace, out_dir: Path, jsonl_fh: TextIO | None
) -> dict[str, bool]:
    """Process explicit local XML files."""
    results: dict[str, bool] = {}
    with tqdm(
        total=len(args.from_files),
        desc="Processing local XML",
        unit="file",
        disable=args.quiet,
    ) as bar:
        for xml_path in args.from_files:
            fp = Path(xml_path)
            kwargs = _schema_kwargs(args)
            data = process_single_local_xml(fp, **kwargs)
            name = fp.stem
            success = data is not None
            if success and data is not None:
                _write_result(data, name, out_dir, args.output_format, jsonl_fh)
            results[name] = success
            bar.update(1)
    return results


def _resolve_network_ids(args: argparse.Namespace) -> list[str]:
    """Resolve CLI network-mode identifiers to normalized PMC IDs."""
    pmc_ids: list[str] = []
    normalizer: Callable[[str], str]

    if args.pmcids:
        normalizer = normalize_id
        raw_ids = args.pmcids
    elif args.pmids:
        normalizer = normalize_pmid
        raw_ids = args.pmids
    elif args.dois:
        normalizer = normalize_id
        raw_ids = args.dois
    elif args.from_id_file:
        return _resolve_ids_from_file(args.from_id_file)
    else:
        return []

    for raw_id in raw_ids:
        try:
            pmc_ids.append(normalizer(raw_id))
        except ValueError as e:
            print(f"Warning: {e}", file=sys.stderr)
    return pmc_ids


def _process_network_ids(
    args: argparse.Namespace,
    pmc_ids: list[str],
    out_dir: Path,
    jsonl_fh: TextIO | None,
) -> dict[str, bool]:
    """Download/process PMC IDs concurrently and write successful outputs."""
    results: dict[str, bool] = {}
    with tqdm(
        total=len(pmc_ids),
        desc="Processing PMC IDs",
        unit="paper",
        disable=args.quiet,
    ) as bar:
        with ThreadPoolExecutor(max_workers=args.batch_size) as executor:
            kwargs = _schema_kwargs(args)
            future_to_pid = {
                executor.submit(process_single_pmc, pid, **kwargs): pid
                for pid in pmc_ids
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
    return results


def _write_summary(results: dict[str, bool], out_dir: Path) -> Path:
    """Write the CLI summary file and return its path."""
    summary_path = out_dir / "summary.json"
    with summary_path.open("w", encoding="utf-8") as jf:
        json.dump(results, jf, indent=2, allow_nan=False)
    return summary_path


def main() -> int:
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

    jsonl_fh = None
    if args.output_format == "jsonl":
        jsonl_fh = (out_dir / "output.jsonl").open("w", encoding="utf-8")

    try:
        if args.from_dir:
            results = _process_local_directory(args, out_dir, jsonl_fh)
            if results is None:
                return 2
        elif args.from_files:
            results = _process_local_files(args, out_dir, jsonl_fh)
        else:
            pmc_ids = _resolve_network_ids(args)
            if not pmc_ids:
                print("No valid PMC IDs to process.", file=sys.stderr)
                return 2
            results = _process_network_ids(args, pmc_ids, out_dir, jsonl_fh)

    finally:
        if jsonl_fh is not None:
            jsonl_fh.close()

    summary_path = _write_summary(results, out_dir)
    total = len(results)
    ok = sum(1 for v in results.values() if v)
    print(f"\nDone: {ok}/{total} succeeded.  Summary written to {summary_path}")
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
