"""Unit tests for the article-assembly orchestrator (folder layout + path injection)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

from pmcgrab.application import article_assembly
from pmcgrab.application.article_assembly import (
    AssetFetchPolicy,
    AssetFetchResult,
    inject_local_paths,
    process_single_pmc_with_assets,
    write_article_folder,
)


def _article(
    figures: list[dict[str, Any]] | None = None, supp: list | None = None
) -> dict[str, Any]:
    """Build a minimal V4-shaped article dict for testing path injection."""
    return {
        "schema_version": 4,
        "has_data": True,
        "article": {"identifiers": {"pmcid": "PMC1"}},
        "content": {"sections": [{"title": "Intro"}]},
        "assets": {
            "figures": figures if figures is not None else [],
            "tables": [],
            "references": [],
            "equations": {"mathml": [], "tex": [], "records": []},
            "supplementary_material": supp if supp is not None else [],
        },
        "relations": [],
        "quality": {
            "status": "complete",
            "diagnostics": [],
            "summary": {},
            "coverage": {},
        },
        "provenance": {"pmcgrab_version": "test"},
    }


def _figure(
    fig_id: str,
    primary: str = "",
    alternates: list[str] | None = None,
    graphics: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "id": fig_id,
        "type": "figure",
        "label": "Figure 1",
        "caption": "caption text",
        "caption_blocks": [],
        "link": primary,
        "alternate_links": alternates or [],
        "graphics": graphics
        or (
            [
                {
                    "id": f"{fig_id}_g1",
                    "type": "graphic",
                    "href": primary,
                    "mime_type": "image/jpeg",
                    "content_type": "",
                    "source": {},
                    "local_path": "",
                    "download_status": "not_attempted",
                }
            ]
            if primary
            else []
        ),
        "alt_text": "",
        "long_desc": "",
        "attrib": "",
        "permissions": {},
        "object_ids": [],
        "object_id": "",
        "text_fallback": "",
        "source": {},
        "parse_status": "parsed",
        "local_path": "",
        "download_status": "not_attempted",
        "download_source": "",
    }


def test_inject_local_paths_marks_downloaded_figures() -> None:
    article = _article(
        figures=[
            _figure("fig1", primary="fig1.jpg"),
            _figure("fig2", primary="fig2.jpg"),
        ]
    )
    result = AssetFetchResult(
        image_paths={"fig1.jpg": "images/fig1.jpg", "fig2.jpg": "images/fig2.jpg"},
        sources_tried=["oa_package"],
        bytes_downloaded=12345,
        status="complete",
    )
    out = inject_local_paths(article, result)
    figs = out["assets"]["figures"]
    assert figs[0]["local_path"] == "images/fig1.jpg"
    assert figs[0]["download_status"] == "downloaded"
    assert figs[0]["download_source"] == "oa_package"
    assert figs[0]["graphics"][0]["local_path"] == "images/fig1.jpg"
    assert figs[0]["graphics"][0]["download_status"] == "downloaded"
    assert figs[1]["local_path"] == "images/fig2.jpg"

    diags = out["quality"]["diagnostics"]
    summary_entry = next(d for d in diags if d.get("code") == "asset_fetch_summary")
    assert summary_entry["details"]["image_count"] == 2
    assert summary_entry["details"]["image_downloaded"] == 2
    assert summary_entry["details"]["bytes_downloaded"] == 12345


def test_inject_local_paths_marks_missing_when_not_downloaded() -> None:
    article = _article(figures=[_figure("fig1", primary="fig1.jpg")])
    result = AssetFetchResult(
        image_paths={},
        sources_tried=["oa_package", "bin_fallback"],
        bytes_downloaded=0,
        errors=[{"href": "fig1.jpg", "reason": "404", "code": "bin_not_found"}],
        status="failed",
    )
    out = inject_local_paths(article, result)
    fig = out["assets"]["figures"][0]
    assert fig["local_path"] == ""
    assert fig["download_status"] == "missing"
    assert fig["graphics"][0]["download_status"] == "missing"

    diag = next(
        d
        for d in out["quality"]["diagnostics"]
        if d.get("code") == "asset_fetch_summary"
    )
    assert diag["details"]["image_downloaded"] == 0
    assert diag["details"]["errors"][0]["code"] == "bin_not_found"


def test_inject_local_paths_marks_not_available_when_figure_has_no_href() -> None:
    article = _article(figures=[_figure("fig1", primary="", graphics=[])])
    result = AssetFetchResult(status="empty", sources_tried=["oa_package"])
    out = inject_local_paths(article, result)
    fig = out["assets"]["figures"][0]
    assert fig["download_status"] == "not_available"
    assert fig["local_path"] == ""


def test_inject_local_paths_handles_alternate_graphics() -> None:
    article = _article(
        figures=[
            _figure(
                "fig1",
                primary="fig1.tif",
                alternates=["fig1.jpg"],
                graphics=[
                    {
                        "id": "g1",
                        "type": "graphic",
                        "href": "fig1.tif",
                        "mime_type": "image/tiff",
                        "content_type": "",
                        "source": {},
                        "local_path": "",
                        "download_status": "not_attempted",
                    },
                    {
                        "id": "g2",
                        "type": "graphic",
                        "href": "fig1.jpg",
                        "mime_type": "image/jpeg",
                        "content_type": "",
                        "source": {},
                        "local_path": "",
                        "download_status": "not_attempted",
                    },
                ],
            )
        ]
    )
    # OA bundle only had the jpg.
    result = AssetFetchResult(
        image_paths={"fig1.jpg": "images/fig1.jpg"},
        sources_tried=["oa_package"],
        status="complete",
    )
    out = inject_local_paths(article, result)
    fig = out["assets"]["figures"][0]
    assert fig["local_path"] == "images/fig1.jpg"
    assert fig["download_status"] == "downloaded"
    # tif graphic recorded as missing; jpg graphic as downloaded
    statuses = {g["href"]: g["download_status"] for g in fig["graphics"]}
    assert statuses == {"fig1.tif": "missing", "fig1.jpg": "downloaded"}


def test_inject_local_paths_supplementary_round_trip() -> None:
    supp_record = {
        "id": "supp1",
        "type": "supplementary_material",
        "href": "S1_dataset.xlsx",
        "label": "Dataset S1",
        "caption": "",
        "caption_blocks": [],
        "local_path": "",
        "download_status": "not_attempted",
        "download_source": "",
    }
    article = _article(supp=[supp_record])
    result = AssetFetchResult(
        supplementary_paths={"S1_dataset.xlsx": "supplementary/S1_dataset.xlsx"},
        sources_tried=["oa_package"],
        status="complete",
    )
    out = inject_local_paths(article, result)
    rec = out["assets"]["supplementary_material"][0]
    assert rec["local_path"] == "supplementary/S1_dataset.xlsx"
    assert rec["download_status"] == "downloaded"


def test_inject_local_paths_no_result_is_noop() -> None:
    article = _article(figures=[_figure("fig1", primary="fig1.jpg")])
    out = inject_local_paths(article, None)
    fig = out["assets"]["figures"][0]
    # Defaults preserved.
    assert fig["download_status"] == "not_attempted"


def test_write_article_folder_creates_json(tmp_path: Path) -> None:
    article = _article(figures=[_figure("fig1", primary="fig1.jpg")])
    result = AssetFetchResult(
        image_paths={"fig1.jpg": "images/fig1.jpg"},
        sources_tried=["oa_package"],
        status="complete",
    )
    json_path = write_article_folder(tmp_path, "7181753", article, result)
    assert json_path == tmp_path / "PMC7181753" / "article.json"
    assert json_path.is_file()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["article"]["identifiers"]["pmcid"] == "PMC1"


def test_write_article_folder_with_raw_xml(tmp_path: Path) -> None:
    article = _article()
    result = AssetFetchResult(status="empty")
    write_article_folder(
        tmp_path,
        "7181753",
        article,
        result,
        save_raw_xml=True,
        raw_xml_bytes=b"<article/>",
    )
    raw_path = tmp_path / "PMC7181753" / "raw.xml"
    assert raw_path.is_file()
    assert raw_path.read_bytes() == b"<article/>"


def test_process_single_pmc_with_assets_writes_folder(tmp_path: Path) -> None:
    article = _article(figures=[_figure("fig1", primary="fig1.jpg")])

    with (
        patch.object(article_assembly, "process_single_pmc", return_value=article),
        patch.object(
            article_assembly,
            "download_article_assets",
            return_value=AssetFetchResult(
                image_paths={"fig1.jpg": "images/fig1.jpg"},
                sources_tried=["oa_package"],
                status="complete",
            ),
        ),
    ):
        article_out, fetch_result = process_single_pmc_with_assets(
            "7181753",
            tmp_path,
            policy=AssetFetchPolicy(),
            output_style="full",
        )

    assert article_out is not None and fetch_result is not None
    json_path = tmp_path / "PMC7181753" / "article.json"
    assert json_path.is_file()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["assets"]["figures"][0]["local_path"] == "images/fig1.jpg"
    assert data["assets"]["figures"][0]["download_source"] == "oa_package"
    assert fetch_result.status == "complete"


def test_process_single_pmc_with_assets_skips_fetch_when_disabled(
    tmp_path: Path,
) -> None:
    article = _article(figures=[_figure("fig1", primary="fig1.jpg")])
    with (
        patch.object(article_assembly, "process_single_pmc", return_value=article),
        patch.object(
            article_assembly,
            "download_article_assets",
        ) as mock_download,
    ):
        article_out, fetch_result = process_single_pmc_with_assets(
            "7181753",
            tmp_path,
            policy=AssetFetchPolicy(fetch_images=False, fetch_supplementary=False),
        )
    mock_download.assert_not_called()
    assert article_out is not None
    assert fetch_result is None
    json_path = tmp_path / "PMC7181753" / "article.json"
    assert json_path.is_file()


def test_process_single_pmc_with_assets_returns_none_on_parse_failure(
    tmp_path: Path,
) -> None:
    with patch.object(article_assembly, "process_single_pmc", return_value=None):
        article_out, fetch_result = process_single_pmc_with_assets(
            "7181753",
            tmp_path,
            policy=AssetFetchPolicy(),
        )
    assert article_out is None
    assert fetch_result is None
    # No folder/file should be written.
    assert not (tmp_path / "PMC7181753").exists()
