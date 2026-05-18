"""PMC article binary asset fetcher.

This module fetches figure (and optionally supplementary) binaries for a PMC
article and writes them into a per-article folder. The primary path uses the
PMC Open Access ``.tar.gz`` package (one HTTPS request per article); the
fallback path fetches each referenced ``xlink:href`` individually from
``https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{id}/bin/{href}``.

The fetcher is tar-slip safe: every extracted member's resolved path is
verified to stay inside the target directory, and symlinks / device files
are skipped. A configurable per-article size ceiling (default 256 MB) aborts
the stream rather than letting an article exhaust the disk.

Public surface:
    AssetFetchPolicy: dataclass describing what to fetch and how
    AssetFetchResult: dataclass describing what was fetched
    fetch_oa_package_assets: pull the OA tar.gz and extract wanted members
    fetch_individual_assets: per-file fallback fetcher
    download_article_assets: top-level helper (primary + fallback)
"""

from __future__ import annotations

import logging
import shutil
import tarfile
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Literal

import requests

from pmcgrab.http_utils import _session
from pmcgrab.infrastructure.settings import (
    PMCGRAB_MAX_ASSET_BYTES,
    PMCGRAB_SSL_VERIFY,
    rate_limit_wait,
)
from pmcgrab.oa_service import tgz_url_for

_logger = logging.getLogger(__name__)

__all__ = [
    "AssetFetchPolicy",
    "AssetFetchResult",
    "download_article_assets",
    "fetch_individual_assets",
    "fetch_oa_package_assets",
]


_BIN_URL_TEMPLATE = "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}/bin/{href}"

Status = Literal["complete", "partial", "empty", "failed"]
DownloadStatus = Literal["downloaded", "missing", "not_attempted", "not_available"]


@dataclass(frozen=True)
class AssetFetchPolicy:
    """Configuration for a single article's asset fetch."""

    fetch_images: bool = True
    fetch_supplementary: bool = False
    include_all_assets: bool = False
    save_raw_xml: bool = False
    max_total_bytes: int = PMCGRAB_MAX_ASSET_BYTES
    per_request_timeout: int = 30
    use_oa_bundle_first: bool = True
    fallback_to_bin: bool = True


@dataclass
class AssetFetchResult:
    """Outcome of an asset fetch for one article.

    ``image_paths`` and ``supplementary_paths`` map the original JATS
    ``xlink:href`` (basename) to a POSIX-style path relative to the article
    folder (e.g. ``"images/pone.0012345.g001.jpg"``).
    """

    image_paths: dict[str, str] = field(default_factory=dict)
    supplementary_paths: dict[str, str] = field(default_factory=dict)
    raw_xml_path: str | None = None
    sources_tried: list[str] = field(default_factory=list)
    bytes_downloaded: int = 0
    errors: list[dict[str, str]] = field(default_factory=list)
    status: Status = "empty"

    def add_error(self, href: str, reason: str, code: str) -> None:
        self.errors.append({"href": href, "reason": reason, "code": code})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _basenames(hrefs: Iterable[str]) -> set[str]:
    """Return the set of POSIX basenames for the given href strings."""
    out: set[str] = set()
    for href in hrefs:
        if not href:
            continue
        out.add(PurePosixPath(href).name)
    return out


def _safe_join(target_dir: Path, member_name: str) -> Path | None:
    """Resolve *member_name* under *target_dir*; return None if it escapes."""
    target_root = target_dir.resolve()
    # Strip leading slashes and normalize separators.
    name = member_name.lstrip("/\\").replace("\\", "/")
    candidate = (target_root / name).resolve()
    try:
        candidate.relative_to(target_root)
    except ValueError:
        return None
    return candidate


def _classify_member(href_basenames: set[str], member: tarfile.TarInfo) -> str:
    """Return where a tar member should be written under the article folder.

    Returns ``"images"`` if the member's basename matches a referenced figure,
    ``"supplementary"`` if it looks like a supplementary asset, ``"raw_xml"``
    if it's the JATS file, or ``""`` if it should be skipped.
    """
    base = PurePosixPath(member.name).name.lower()
    if not base:
        return ""
    if base.endswith(".nxml") or base.endswith(".xml"):
        return "raw_xml"
    # Image extensions covered by JATS graphics in practice
    image_exts = (
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".tif",
        ".tiff",
        ".bmp",
        ".svg",
        ".webp",
    )
    if any(base.endswith(ext) for ext in image_exts):
        return "images"
    # Match by basename against known figure hrefs as a more reliable signal
    if base in {b.lower() for b in href_basenames}:
        return "images"
    return "supplementary"


def _build_session() -> requests.Session:
    """Return the shared pmcgrab session for asset downloads.

    The session is module-level in ``http_utils`` so connection pooling and
    SSL settings are shared with NCBI requests.
    """
    return _session


# ---------------------------------------------------------------------------
# Primary path: OA tar.gz bundle
# ---------------------------------------------------------------------------


def fetch_oa_package_assets(
    pmcid: int | str,
    target_dir: Path,
    *,
    wanted_basenames: set[str],
    policy: AssetFetchPolicy,
    supplementary_basenames: set[str] | None = None,
) -> AssetFetchResult:
    """Stream the OA ``.tar.gz`` package and extract wanted members.

    *wanted_basenames* is the set of figure ``xlink:href`` basenames that
    should be saved to ``target_dir/images/``. *supplementary_basenames*
    is the analogous set for supplementary materials; pass ``None`` to skip
    supplementary extraction entirely (independent of ``policy.fetch_supplementary``
    so the caller can decide what to include).

    On success the tar stream is closed before the function returns. On
    failure (no OA bundle, network error, size ceiling) the function returns
    a result with ``status="failed"`` and records the cause in ``errors``.
    """
    result = AssetFetchResult(sources_tried=["oa_package"])
    rate_limit_wait()
    try:
        tgz_url = tgz_url_for(pmcid)
    except Exception as exc:
        _logger.warning("OA lookup failed for PMC%s: %s", pmcid, exc)
        result.add_error("", str(exc), "oa_lookup_failed")
        result.status = "failed"
        return result

    if not tgz_url:
        result.add_error("", "no OA tar.gz link", "oa_not_available")
        result.status = "failed"
        return result

    supp_set = supplementary_basenames or set()
    save_raw_xml = policy.save_raw_xml
    include_all = policy.include_all_assets
    target_dir.mkdir(parents=True, exist_ok=True)

    session = _build_session()
    rate_limit_wait()
    try:
        resp = session.get(
            tgz_url,
            stream=True,
            timeout=policy.per_request_timeout,
            verify=PMCGRAB_SSL_VERIFY,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        _logger.warning("OA tar.gz fetch failed for PMC%s: %s", pmcid, exc)
        result.add_error(tgz_url, str(exc), "oa_tgz_http_error")
        result.status = "failed"
        return result

    image_dir = target_dir / "images"
    supp_dir = target_dir / "supplementary"
    extracted_paths: list[Path] = []
    bytes_seen = 0

    try:
        # decode_content lets us pass the raw stream to tarfile without
        # having to manage gzip framing manually.
        resp.raw.decode_content = True
        with tarfile.open(fileobj=resp.raw, mode="r|gz") as tar:
            for member in tar:
                if not member.isreg():
                    if member.issym() or member.islnk():
                        result.add_error(
                            member.name,
                            "symlink/hardlink rejected",
                            "tar_unsafe_member",
                        )
                    continue
                base = PurePosixPath(member.name).name
                if not base:
                    continue
                category = _classify_member(wanted_basenames, member)
                want = False
                dest_dir: Path | None = None
                if category == "images" and (include_all or base in wanted_basenames):
                    want = True
                    dest_dir = image_dir
                elif category == "supplementary" and (include_all or base in supp_set):
                    want = True
                    dest_dir = supp_dir
                elif category == "raw_xml" and save_raw_xml:
                    want = True
                    dest_dir = target_dir
                if not want or dest_dir is None:
                    continue
                bytes_seen += member.size
                if bytes_seen > policy.max_total_bytes:
                    result.add_error(
                        member.name,
                        f"size ceiling exceeded ({bytes_seen} > {policy.max_total_bytes})",
                        "asset_size_limit",
                    )
                    raise _SizeCeilingExceeded()
                dest_dir.mkdir(parents=True, exist_ok=True)
                # Save under the basename, not the full member path.
                if category == "raw_xml":
                    dest_path = dest_dir / "raw.xml"
                else:
                    dest_path = dest_dir / base
                # tar-slip check: the *resolved* destination must stay inside
                # the *resolved* target_dir. Use the unresolved dest_path for
                # the recorded relative path so callers see paths consistent
                # with target_dir even when /tmp is a symlink to /private/tmp.
                relative_str = dest_path.relative_to(target_dir).as_posix()
                safe = _safe_join(target_dir, relative_str)
                if safe is None:
                    result.add_error(
                        member.name, "tar-slip rejected", "tar_unsafe_path"
                    )
                    continue
                extracted = tar.extractfile(member)
                if extracted is None:
                    result.add_error(
                        member.name, "tar entry not extractable", "tar_empty_member"
                    )
                    continue
                with open(safe, "wb") as fh:
                    shutil.copyfileobj(extracted, fh)
                extracted_paths.append(safe)
                if category == "images":
                    result.image_paths[base] = relative_str
                elif category == "supplementary":
                    result.supplementary_paths[base] = relative_str
                elif category == "raw_xml":
                    result.raw_xml_path = relative_str
        result.bytes_downloaded = bytes_seen
        result.status = (
            "complete"
            if result.image_paths or result.supplementary_paths or result.raw_xml_path
            else "empty"
        )
        return result
    except _SizeCeilingExceeded:
        for path in extracted_paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        result.bytes_downloaded = bytes_seen
        result.status = "failed"
        return result
    except (tarfile.TarError, OSError) as exc:
        _logger.warning("OA tar.gz extraction failed for PMC%s: %s", pmcid, exc)
        result.add_error(tgz_url, str(exc), "oa_tgz_extract_error")
        result.bytes_downloaded = bytes_seen
        result.status = "failed"
        return result
    finally:
        try:
            resp.close()
        except Exception:
            pass


class _SizeCeilingExceeded(Exception):
    """Internal marker to abort tar extraction mid-stream."""


# ---------------------------------------------------------------------------
# Fallback path: per-file /bin/{href}
# ---------------------------------------------------------------------------


def fetch_individual_assets(
    pmcid: int | str,
    hrefs: Iterable[str],
    target_dir: Path,
    *,
    policy: AssetFetchPolicy,
    subdir: str = "images",
) -> AssetFetchResult:
    """Fetch each ``href`` from the PMC ``/bin/`` URL pattern.

    Each request is gated by ``rate_limit_wait()``. Files already on disk are
    not re-fetched (idempotent). A 404 on one href doesn't stop the loop.
    """
    result = AssetFetchResult(sources_tried=["bin_fallback"])
    normalized_pmcid = str(pmcid)
    if normalized_pmcid.upper().startswith("PMC"):
        normalized_pmcid = normalized_pmcid[3:]
    dest_dir = target_dir / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    session = _build_session()
    seen: set[str] = set()
    bytes_seen = 0
    for href in hrefs:
        if not href or href in seen:
            continue
        seen.add(href)
        base = PurePosixPath(href).name
        if not base:
            continue
        dest_path = dest_dir / base
        rel = dest_path.relative_to(target_dir).as_posix()
        if dest_path.exists() and dest_path.stat().st_size > 0:
            # Idempotent: trust whatever's already on disk.
            if subdir == "images":
                result.image_paths[base] = rel
            else:
                result.supplementary_paths[base] = rel
            continue
        url = _BIN_URL_TEMPLATE.format(pmcid=normalized_pmcid, href=href)
        try:
            rate_limit_wait()
            resp = session.get(
                url,
                stream=True,
                timeout=policy.per_request_timeout,
                verify=PMCGRAB_SSL_VERIFY,
            )
            if resp.status_code == 404:
                result.add_error(href, "404 Not Found", "bin_not_found")
                resp.close()
                continue
            resp.raise_for_status()
            written = 0
            with open(dest_path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    fh.write(chunk)
                    written += len(chunk)
                    bytes_seen += len(chunk)
                    if bytes_seen > policy.max_total_bytes:
                        break
            resp.close()
            if bytes_seen > policy.max_total_bytes:
                result.add_error(
                    href,
                    f"size ceiling exceeded ({bytes_seen} > {policy.max_total_bytes})",
                    "asset_size_limit",
                )
                # Drop the partial we just wrote.
                try:
                    dest_path.unlink(missing_ok=True)
                except OSError:
                    pass
                break
            if subdir == "images":
                result.image_paths[base] = rel
            else:
                result.supplementary_paths[base] = rel
        except requests.RequestException as exc:
            result.add_error(href, str(exc), "bin_http_error")
        except OSError as exc:
            result.add_error(href, str(exc), "bin_write_error")
    result.bytes_downloaded = bytes_seen
    if result.image_paths or result.supplementary_paths:
        result.status = "partial" if result.errors else "complete"
    else:
        result.status = "failed" if seen else "empty"
    return result


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def _collect_figure_hrefs(
    figure_records: list[dict[str, Any]],
) -> tuple[list[str], dict[str, list[str]]]:
    """Return the ordered list of unique figure hrefs and the per-figure map.

    The per-figure map keys are figure IDs and values are the hrefs the
    orchestrator should attribute to that figure (primary + alternates +
    every graphic entry's href).
    """
    seen: set[str] = set()
    ordered: list[str] = []
    per_figure: dict[str, list[str]] = {}
    for fig in figure_records:
        fig_id = str(fig.get("id") or "")
        hrefs: list[str] = []
        primary = fig.get("link") or ""
        if isinstance(primary, str) and primary:
            hrefs.append(primary)
        for alt in fig.get("alternate_links", []) or []:
            if isinstance(alt, str) and alt:
                hrefs.append(alt)
        for graphic in fig.get("graphics", []) or []:
            if isinstance(graphic, dict):
                graphic_href = graphic.get("href") or ""
                if isinstance(graphic_href, str) and graphic_href:
                    hrefs.append(graphic_href)
        # Dedupe within a figure while preserving order.
        unique_per_figure: list[str] = []
        seen_local: set[str] = set()
        for h in hrefs:
            if h not in seen_local:
                seen_local.add(h)
                unique_per_figure.append(h)
        per_figure[fig_id] = unique_per_figure
        for h in unique_per_figure:
            if h not in seen:
                seen.add(h)
                ordered.append(h)
    return ordered, per_figure


def _collect_supp_hrefs(
    supplementary_records: list[dict[str, Any]],
) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for record in supplementary_records:
        href = record.get("href") if isinstance(record, dict) else None
        if isinstance(href, str) and href and href not in seen:
            seen.add(href)
            out.append(href)
    return out


def download_article_assets(
    pmcid: int | str,
    figure_records: list[dict[str, Any]],
    supplementary_records: list[dict[str, Any]],
    target_dir: Path,
    *,
    policy: AssetFetchPolicy = AssetFetchPolicy(),
) -> AssetFetchResult:
    """Top-level helper that combines OA primary and bin/ fallback.

    Pipeline:
        1. Collect unique figure hrefs (primary + alternate + each graphic).
        2. Try the OA tar.gz bundle (skipped if ``policy.use_oa_bundle_first``
           is ``False``). Extracts matching figure + optional supplementary
           members in one stream.
        3. For any href the primary didn't cover, fall back to
           ``/pmc/articles/PMC{id}/bin/{href}`` per file (skipped if
           ``policy.fallback_to_bin`` is ``False``).
        4. Merge results and return.

    The returned :class:`AssetFetchResult` carries a flat ``image_paths`` map
    keyed by ``xlink:href`` basename; the orchestrator uses this to inject
    ``local_path`` values into the article JSON.
    """
    if not policy.fetch_images and not policy.fetch_supplementary:
        # Nothing to do; return an empty success so callers can record
        # download_status="not_attempted".
        return AssetFetchResult(status="empty")

    target_dir.mkdir(parents=True, exist_ok=True)

    figure_hrefs, _per_figure = _collect_figure_hrefs(
        figure_records if policy.fetch_images else []
    )
    supp_hrefs = _collect_supp_hrefs(
        supplementary_records if policy.fetch_supplementary else []
    )
    figure_basenames = _basenames(figure_hrefs)
    supp_basenames = _basenames(supp_hrefs)

    final = AssetFetchResult()

    if policy.use_oa_bundle_first and (
        figure_hrefs or supp_hrefs or policy.save_raw_xml
    ):
        oa = fetch_oa_package_assets(
            pmcid,
            target_dir,
            wanted_basenames=figure_basenames,
            policy=policy,
            supplementary_basenames=(
                supp_basenames if policy.fetch_supplementary else None
            ),
        )
        final.sources_tried.extend(oa.sources_tried)
        final.image_paths.update(oa.image_paths)
        final.supplementary_paths.update(oa.supplementary_paths)
        if oa.raw_xml_path:
            final.raw_xml_path = oa.raw_xml_path
        final.bytes_downloaded += oa.bytes_downloaded
        final.errors.extend(oa.errors)

    if policy.fallback_to_bin:
        missing_images = [
            h for h in figure_hrefs if PurePosixPath(h).name not in final.image_paths
        ]
        if missing_images:
            bin_images = fetch_individual_assets(
                pmcid,
                missing_images,
                target_dir,
                policy=policy,
                subdir="images",
            )
            final.sources_tried.extend(
                s for s in bin_images.sources_tried if s not in final.sources_tried
            )
            final.image_paths.update(bin_images.image_paths)
            final.bytes_downloaded += bin_images.bytes_downloaded
            final.errors.extend(bin_images.errors)
        if policy.fetch_supplementary:
            missing_supp = [
                h
                for h in supp_hrefs
                if PurePosixPath(h).name not in final.supplementary_paths
            ]
            if missing_supp:
                bin_supp = fetch_individual_assets(
                    pmcid,
                    missing_supp,
                    target_dir,
                    policy=policy,
                    subdir="supplementary",
                )
                final.sources_tried.extend(
                    s for s in bin_supp.sources_tried if s not in final.sources_tried
                )
                final.supplementary_paths.update(bin_supp.supplementary_paths)
                final.bytes_downloaded += bin_supp.bytes_downloaded
                final.errors.extend(bin_supp.errors)

    # Compute overall status.
    wanted_total = len(figure_basenames) + (
        len(supp_basenames) if policy.fetch_supplementary else 0
    )
    got_total = len(final.image_paths) + (
        len(final.supplementary_paths) if policy.fetch_supplementary else 0
    )
    if wanted_total == 0:
        final.status = "empty"
    elif got_total == 0:
        final.status = "failed"
    elif got_total == wanted_total:
        final.status = "complete"
    else:
        final.status = "partial"

    # Tidy up empty subdirs so users don't see stray folders.
    for subdir in ("images", "supplementary"):
        p = target_dir / subdir
        if p.exists() and not any(p.iterdir()):
            try:
                p.rmdir()
            except OSError:
                pass

    _logger.info(
        "PMC%s assets: %s/%s wanted, status=%s, bytes=%s",
        pmcid,
        got_total,
        wanted_total,
        final.status,
        final.bytes_downloaded,
    )

    return final


def _format_summary(result: AssetFetchResult) -> str:
    """Render a one-line summary string for logging."""
    return (
        f"status={result.status} "
        f"images={len(result.image_paths)} "
        f"supplementary={len(result.supplementary_paths)} "
        f"bytes={result.bytes_downloaded} "
        f"sources={','.join(result.sources_tried) or 'none'} "
        f"errors={len(result.errors)}"
    )
