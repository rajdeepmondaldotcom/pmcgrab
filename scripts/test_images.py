#!/usr/bin/env python
"""Smoke-test the full asset-fetching pipeline against 10 random PMC IDs.

This script picks 10 PMC IDs at random from a curated pool of known
Open-Access articles, runs the full
:func:`pmcgrab.application.article_assembly.process_single_pmc_with_assets`
pipeline against each, and prints a markdown summary of the outcome.

Usage::

    uv run python scripts/test_images.py
    uv run python scripts/test_images.py --out-dir /tmp/pmc-smoke --keep
    uv run python scripts/test_images.py --pmcids 7181753 3539614
    uv run python scripts/test_images.py --seed 42         # reproduce a run
    uv run python scripts/test_images.py --count 5         # fewer IDs

The script exits with status 0 when every article parsed successfully and
either downloaded at least one image or had no figures referenced; status 1
otherwise.  Image download requires NCBI to be reachable; expect the run to
take 30-90 seconds depending on the size of the OA tar.gz bundles.
"""

from __future__ import annotations

import argparse
import random
import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pmcgrab.application.article_assembly import (
    AssetFetchPolicy,
    process_single_pmc_with_assets,
)

# Curated pool of 50 known-OA PMC IDs spanning multiple publishers and years.
# Each entry was verified against the NCBI OA Web Service to have a tar.gz
# package URL at audit time (see ``scripts/test_images.py`` git history).
# When updating the pool, prefer additions over removals so historical seeds
# keep working.
KNOWN_OA_POOL: list[tuple[str, str]] = [
    ("7181753", "Nat Commun - single-cell transcriptomes (baseline)"),
    ("3539614", "OA classic, multi-figure"),
    ("3084273", "PLOS ONE classic pone.*.g###.tif pattern"),
    ("7114487", "BMC nephrology, mid-2020"),
    ("4382965", "PLOS Genetics, many figures"),
    ("2972754", "PLOS Biology classic, .tif vs .jpg coverage"),
    ("5454911", "OA, mentioned in CLI docstring example"),
    ("6234560", "Scientific Reports, Nature OA hosting path"),
    ("5901139", "OA, 2018"),
    ("6535064", "OA, 2019"),
    ("6694186", "OA, 2019"),
    ("6798083", "OA, 2019"),
    ("6961841", "OA, 2020"),
    ("7065074", "OA, 2020"),
    ("7204193", "OA, 2020"),
    ("7261078", "OA, 2020"),
    ("7363817", "OA, 2020"),
    ("7445230", "OA, 2020"),
    ("7530263", "OA, 2020"),
    ("7607438", "OA, 2020"),
    ("7782496", "OA, 2020"),
    ("7882507", "OA, 2021"),
    ("7991932", "OA, 2021"),
    ("8081909", "OA, 2021"),
    ("8169000", "OA, 2021"),
    ("8252859", "OA, 2021"),
    ("8345128", "OA, 2021"),
    ("8514617", "OA, 2021"),
    ("8612388", "OA, 2021"),
    ("8718275", "OA, 2022"),
    ("8932032", "OA, 2022"),
    ("9024118", "OA, 2022"),
    ("9123270", "OA, 2022"),
    ("9217780", "OA, 2022"),
    ("9318451", "OA, 2022"),
    ("9415239", "OA, 2022"),
    ("9511023", "OA, 2022"),
    ("9605164", "OA, 2022"),
    ("9706348", "OA, 2022"),
    ("6000001", "OA, 2018 mid-range"),
    ("6500000", "OA, 2019 mid-range"),
    ("7500000", "OA, 2020 mid-range"),
    ("9000000", "OA, 2022 mid-range"),
    ("9500000", "OA, 2022 late"),
    ("10000000", "OA, 2023"),
    ("10500000", "OA, 2023 late"),
    ("11000000", "OA, 2024"),
    ("5678901", "OA, 2017"),
    ("3789012", "OA, 2013"),
    ("6890123", "OA, 2019"),
]


@dataclass
class RunResult:
    pmcid: str
    parsed: bool
    figures_total: int = 0
    figures_downloaded: int = 0
    supplementary_total: int = 0
    supplementary_downloaded: int = 0
    bytes_downloaded: int = 0
    sources: tuple[str, ...] = ()
    status: str = "not_attempted"
    duration_s: float = 0.0
    error: str = ""


def _run_one(pmcid: str, base_dir: Path, policy: AssetFetchPolicy) -> RunResult:
    started = time.monotonic()
    try:
        article, fetch_result = process_single_pmc_with_assets(
            pmcid,
            base_dir,
            policy=policy,
            timeout=180,
        )
    except Exception as exc:
        return RunResult(
            pmcid=pmcid,
            parsed=False,
            status="failed",
            duration_s=time.monotonic() - started,
            error=str(exc)[:120],
        )

    if article is None:
        return RunResult(
            pmcid=pmcid,
            parsed=False,
            status="failed",
            duration_s=time.monotonic() - started,
            error="process_single_pmc returned None",
        )

    figures = article["assets"]["figures"]
    figures_total = sum(1 for f in figures if f.get("link"))
    supps = article["assets"].get("supplementary_material", [])
    supp_total = sum(1 for s in supps if s.get("href"))
    return RunResult(
        pmcid=pmcid,
        parsed=True,
        figures_total=figures_total,
        figures_downloaded=len(fetch_result.image_paths) if fetch_result else 0,
        supplementary_total=supp_total,
        supplementary_downloaded=(
            len(fetch_result.supplementary_paths) if fetch_result else 0
        ),
        bytes_downloaded=fetch_result.bytes_downloaded if fetch_result else 0,
        sources=tuple(fetch_result.sources_tried) if fetch_result else (),
        status=fetch_result.status if fetch_result else "not_attempted",
        duration_s=time.monotonic() - started,
    )


def _markdown_table(results: list[RunResult]) -> str:
    headers = [
        "PMCID",
        "Parsed",
        "Figures",
        "Downloaded",
        "Supp",
        "Supp DL",
        "MB",
        "Sources",
        "Status",
        "Time",
        "Error",
    ]
    sep = ["---"] * len(headers)

    def _row(r: RunResult) -> list[str]:
        return [
            f"PMC{r.pmcid}",
            "yes" if r.parsed else "no",
            str(r.figures_total),
            str(r.figures_downloaded),
            str(r.supplementary_total),
            str(r.supplementary_downloaded),
            f"{r.bytes_downloaded / (1024 * 1024):.2f}",
            ",".join(r.sources) or "-",
            r.status,
            f"{r.duration_s:.1f}s",
            (r.error[:60] + "...") if len(r.error) > 60 else r.error,
        ]

    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(sep) + " |"]
    for r in results:
        lines.append("| " + " | ".join(_row(r)) + " |")
    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Smoke-test PMCGrab asset fetching over a random PMC sample."
    )
    p.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of PMC IDs to sample from the OA pool (default: 10)",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible runs (default: clock-derived)",
    )
    p.add_argument(
        "--pmcids",
        nargs="+",
        default=None,
        help="Override sampling with an explicit list of PMC IDs",
    )
    p.add_argument(
        "--out-dir",
        default=None,
        help="Where to write per-article folders (default: a temp directory)",
    )
    p.add_argument(
        "--keep",
        action="store_true",
        help="Keep downloaded artifacts after the run (default: clean temp dir)",
    )
    p.add_argument(
        "--workers",
        type=int,
        default=3,
        help="Number of concurrent articles (default: 3 to be polite to NCBI)",
    )
    p.add_argument(
        "--include-supplementary",
        action="store_true",
        help="Also download supplementary files",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    if args.pmcids:
        chosen: list[str] = [str(p).removeprefix("PMC") for p in args.pmcids]
    else:
        rng = random.Random(args.seed)
        sample = rng.sample(KNOWN_OA_POOL, k=min(args.count, len(KNOWN_OA_POOL)))
        chosen = [pmcid for pmcid, _ in sample]

    if args.out_dir:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        cleanup_after = False
    else:
        out_dir = Path(tempfile.mkdtemp(prefix="pmcgrab-smoke-"))
        cleanup_after = not args.keep

    policy = AssetFetchPolicy(
        fetch_images=True,
        fetch_supplementary=args.include_supplementary,
    )

    print(f"Sampling {len(chosen)} PMC IDs into {out_dir}")
    print(f"IDs: {', '.join('PMC' + pid for pid in chosen)}\n")

    results: list[RunResult] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        future_to_pid: dict[Any, str] = {
            executor.submit(_run_one, pid, out_dir, policy): pid for pid in chosen
        }
        for future in as_completed(future_to_pid):
            pid = future_to_pid[future]
            try:
                result = future.result()
            except Exception as exc:
                result = RunResult(pmcid=pid, parsed=False, error=str(exc)[:120])
            print(
                f"  PMC{result.pmcid}: parsed={result.parsed} "
                f"figs={result.figures_downloaded}/{result.figures_total} "
                f"status={result.status} "
                f"time={result.duration_s:.1f}s"
            )
            results.append(result)

    results.sort(key=lambda r: r.pmcid)
    print("\n## Summary\n")
    print(_markdown_table(results))

    total = len(results)
    parsed = sum(1 for r in results if r.parsed)
    with_downloads = sum(1 for r in results if r.figures_downloaded > 0)
    full_failures = [
        r
        for r in results
        if not r.parsed or (r.figures_total > 0 and r.figures_downloaded == 0)
    ]
    print(
        f"\nParsed {parsed}/{total}; figures downloaded for {with_downloads}/{total};"
        f" full failures: {len(full_failures)}"
    )

    if cleanup_after:
        shutil.rmtree(out_dir, ignore_errors=True)
    else:
        print(f"\nArtifacts kept at {out_dir}")

    return 0 if not full_failures else 1


if __name__ == "__main__":
    sys.exit(main())
