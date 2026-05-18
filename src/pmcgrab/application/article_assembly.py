"""High-level orchestrator: fetch a PMC article, download its assets, write the folder.

This module wraps :func:`pmcgrab.application.processing.process_single_pmc` with
binary-asset downloading and the per-article folder output layout introduced
in pmcgrab 2.0:

    {out_dir}/
        PMC{id}/
            article.json
            images/...        # only when images were downloaded
            supplementary/... # only when supplementary fetching is enabled
            raw.xml           # only when save_raw_xml is enabled

Existing callers of :func:`process_single_pmc` are unaffected; this module
is opt-in via :func:`process_single_pmc_with_assets` and the CLI's default
``--format json`` path.

Public surface:
    process_single_pmc_with_assets: fetch + assets + write folder
    write_article_folder: persist article.json (and raw.xml) to disk
    inject_local_paths: mutate the V4 dict to add local_path/download_status
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pmcgrab.application.processing import process_single_pmc
from pmcgrab.common.paper_output import ArticleOutput
from pmcgrab.idconvert import normalize_id
from pmcgrab.infrastructure.asset_fetcher import (
    AssetFetchPolicy,
    AssetFetchResult,
    download_article_assets,
)
from pmcgrab.infrastructure.settings import NCBI_TIMEOUT

_logger = logging.getLogger(__name__)

__all__ = [
    "AssetFetchPolicy",
    "AssetFetchResult",
    "inject_local_paths",
    "process_single_pmc_with_assets",
    "write_article_folder",
]


def _article_folder_name(pmc_id: str | int) -> str:
    """Return ``"PMC{digits}"`` regardless of input form."""
    text = str(pmc_id).strip()
    if text.upper().startswith("PMC"):
        return "PMC" + text[3:]
    return f"PMC{text}"


def _figure_records(article: ArticleOutput) -> list[dict[str, Any]]:
    assets = article.get("assets") if isinstance(article, dict) else None
    if not isinstance(assets, dict):
        return []
    figures = assets.get("figures")
    return figures if isinstance(figures, list) else []


def _supplementary_records(article: ArticleOutput) -> list[dict[str, Any]]:
    assets = article.get("assets") if isinstance(article, dict) else None
    if not isinstance(assets, dict):
        return []
    records = assets.get("supplementary_material")
    return records if isinstance(records, list) else []


def inject_local_paths(
    article: ArticleOutput, fetch_result: AssetFetchResult | None
) -> ArticleOutput:
    """Inject ``local_path`` / ``download_status`` / ``download_source`` fields.

    Walks ``article['assets']['figures']`` and each entry's ``graphics`` list,
    plus ``article['assets']['supplementary_material']``. Records whose
    ``link`` / ``href`` basename appears in ``fetch_result.image_paths`` (or
    ``supplementary_paths``) are stamped as downloaded; records with no usable
    href become ``not_available``; everything else becomes ``missing``.

    A singleton info entry with code ``asset_fetch_summary`` is appended to
    ``article['quality']['diagnostics']`` describing what was attempted.
    """
    if fetch_result is None:
        # Caller did not run the fetcher (e.g. --no-images). Default fields are
        # already in place from the JATS extractor; nothing further to do.
        return article

    image_basenames = dict(fetch_result.image_paths)
    supp_basenames = dict(fetch_result.supplementary_paths)
    image_fetched_count = 0
    image_total = 0
    supp_fetched_count = 0
    supp_total = 0
    image_source_resolution = (
        "oa_package"
        if "oa_package" in fetch_result.sources_tried
        else ("bin_fallback" if "bin_fallback" in fetch_result.sources_tried else "")
    )

    for figure in _figure_records(article):
        primary = figure.get("link") or ""
        alternates = figure.get("alternate_links") or []
        graphics = figure.get("graphics") or []
        # Per-graphic stamping (preserve insertion order).
        any_downloaded = False
        for graphic in graphics:
            if not isinstance(graphic, dict):
                continue
            g_href = graphic.get("href") or ""
            if not isinstance(g_href, str) or not g_href:
                graphic["local_path"] = ""
                graphic["download_status"] = "not_available"
                continue
            base = Path(g_href).name
            if base in image_basenames:
                graphic["local_path"] = image_basenames[base]
                graphic["download_status"] = "downloaded"
                any_downloaded = True
            else:
                graphic["local_path"] = ""
                graphic["download_status"] = "missing"
        # Figure-level fields.
        candidates: list[str] = []
        if isinstance(primary, str) and primary:
            candidates.append(primary)
        for alt in alternates:
            if isinstance(alt, str) and alt:
                candidates.append(alt)
        for graphic in graphics:
            if isinstance(graphic, dict):
                g_href = graphic.get("href") or ""
                if isinstance(g_href, str) and g_href:
                    candidates.append(g_href)
        chosen: str | None = None
        for cand in candidates:
            base = Path(cand).name
            if base in image_basenames:
                chosen = image_basenames[base]
                break
        if chosen is not None:
            figure["local_path"] = chosen
            figure["download_status"] = "downloaded"
            figure["download_source"] = image_source_resolution
            image_fetched_count += 1
        elif not candidates:
            figure["local_path"] = ""
            figure["download_status"] = "not_available"
            figure["download_source"] = ""
        elif any_downloaded:
            # Some graphic in the alternatives downloaded; figure-level fields
            # already covered by the first matching candidate above.
            figure["local_path"] = ""
            figure["download_status"] = "missing"
            figure["download_source"] = ""
        else:
            figure["local_path"] = ""
            figure["download_status"] = "missing"
            figure["download_source"] = ""
        if candidates:
            image_total += 1

    for record in _supplementary_records(article):
        href = record.get("href") or ""
        if not isinstance(href, str) or not href:
            record.setdefault("local_path", "")
            record["download_status"] = "not_available"
            record.setdefault("download_source", "")
            continue
        supp_total += 1
        base = Path(href).name
        if base in supp_basenames:
            record["local_path"] = supp_basenames[base]
            record["download_status"] = "downloaded"
            record["download_source"] = image_source_resolution
            supp_fetched_count += 1
        else:
            record["local_path"] = ""
            record["download_status"] = "missing"
            record["download_source"] = ""

    quality = article.get("quality")
    if isinstance(quality, dict):
        diagnostics = quality.get("diagnostics")
        if not isinstance(diagnostics, list):
            diagnostics = []
            quality["diagnostics"] = diagnostics
        message_parts = [
            f"Downloaded {image_fetched_count}/{image_total} figures",
        ]
        if supp_total:
            message_parts.append(f"{supp_fetched_count}/{supp_total} supplementary")
        diagnostics.append(
            {
                "severity": "info",
                "code": "asset_fetch_summary",
                "message": ", ".join(message_parts),
                "details": {
                    "status": fetch_result.status,
                    "sources_tried": list(fetch_result.sources_tried),
                    "bytes_downloaded": fetch_result.bytes_downloaded,
                    "image_count": image_total,
                    "image_downloaded": image_fetched_count,
                    "supplementary_count": supp_total,
                    "supplementary_downloaded": supp_fetched_count,
                    "errors": list(fetch_result.errors),
                },
            }
        )
    return article


def write_article_folder(
    out_dir: Path,
    pmc_id: str | int,
    article: ArticleOutput,
    fetch_result: AssetFetchResult | None,
    *,
    save_raw_xml: bool = False,
    raw_xml_bytes: bytes | None = None,
) -> Path:
    """Persist ``article.json`` (and optionally ``raw.xml``) under ``out_dir/PMC{id}/``.

    Image and supplementary files are written as a side-effect of the asset
    fetcher earlier in the pipeline; this function only handles the JSON and
    the optional raw XML.

    Returns the path to ``article.json``.
    """
    folder = Path(out_dir) / _article_folder_name(pmc_id)
    folder.mkdir(parents=True, exist_ok=True)
    json_path = folder / "article.json"
    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(article, fh, indent=2, ensure_ascii=False, allow_nan=False)
    if save_raw_xml and raw_xml_bytes is not None:
        # Only write raw.xml when the OA tar.gz did not already produce one.
        existing = fetch_result.raw_xml_path if fetch_result else None
        if not existing:
            (folder / "raw.xml").write_bytes(raw_xml_bytes)
    return json_path


def process_single_pmc_with_assets(
    pmc_id: str | int,
    out_dir: str | Path,
    *,
    policy: AssetFetchPolicy | None = None,
    download: bool = False,
    timeout: int = NCBI_TIMEOUT,
    metadata_only: bool = False,
) -> tuple[ArticleOutput | None, AssetFetchResult | None]:
    """Fetch a single PMC article, download its figure binaries, write the folder.

    Args:
        pmc_id: PMC ID with or without the ``PMC`` prefix.
        out_dir: Output root. The article folder is created at
            ``out_dir/PMC{id}/`` and ``article.json`` is written inside.
        policy: How to fetch assets. Defaults to ``AssetFetchPolicy()`` which
            downloads figure images (no supplementary, no raw XML).
        download: Forwarded to :func:`process_single_pmc` (caches raw XML in
            the ``data/`` directory for reuse). Unrelated to ``--include-raw-xml``.
        timeout: Network/parse timeout in seconds. Defaults to ``NCBI_TIMEOUT``.
        metadata_only: If ``True``, allow metadata-only output without body
            sections (passed through to :func:`process_single_pmc`).

    Returns:
        A tuple ``(article_dict_or_none, fetch_result_or_none)``.
        ``article_dict`` is ``None`` when parsing failed. ``fetch_result`` is
        ``None`` when image fetching was disabled (``policy.fetch_images=False``
        and ``policy.fetch_supplementary=False``); otherwise it carries the
        outcome of the asset fetch.

    Side effects:
        Writes ``out_dir/PMC{id}/article.json`` on parse success. Writes
        image / supplementary / raw.xml files according to ``policy``.
    """
    if policy is None:
        policy = AssetFetchPolicy()
    article = process_single_pmc(
        pmc_id,
        download=download,
        timeout=timeout,
        metadata_only=metadata_only,
        schema_version=4,
    )
    if article is None:
        return None, None

    # The PMC ID used downstream (for OA lookup, bin/ URLs) must be the
    # numeric one. The orchestrator's out_dir uses PMC{id} as the folder name.
    try:
        normalized = (
            str(pmc_id) if isinstance(pmc_id, int) else normalize_id(str(pmc_id))
        )
        pmc_id_num = int(normalized)
    except (TypeError, ValueError):
        _logger.warning("Could not normalize PMC ID %r", pmc_id)
        pmc_id_num = pmc_id  # type: ignore[assignment]

    target_dir = Path(out_dir) / _article_folder_name(pmc_id_num)
    target_dir.mkdir(parents=True, exist_ok=True)

    fetch_result: AssetFetchResult | None = None
    if policy.fetch_images or policy.fetch_supplementary or policy.save_raw_xml:
        try:
            fetch_result = download_article_assets(
                pmc_id_num,
                _figure_records(article),
                _supplementary_records(article),
                target_dir,
                policy=policy,
            )
        except Exception as exc:
            _logger.warning("Asset fetch raised for PMC%s: %s", pmc_id_num, exc)
            fetch_result = AssetFetchResult(status="failed")
            fetch_result.add_error("", str(exc), "asset_fetch_exception")

    if fetch_result is not None:
        inject_local_paths(article, fetch_result)

    write_article_folder(target_dir.parent, pmc_id_num, article, fetch_result)
    return article, fetch_result
