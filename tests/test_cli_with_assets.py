"""CLI tests for ``--with-images`` and asset-related flags."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from pmcgrab.application import article_assembly
from pmcgrab.application.article_assembly import AssetFetchResult
from pmcgrab.cli import pmcgrab_cli


def _dummy_article(pmcid: str = "PMC123") -> dict[str, Any]:
    return {
        "schema_version": 4,
        "has_data": True,
        "article": {"identifiers": {"pmcid": pmcid}, "title": {"main": "T"}},
        "content": {"sections": []},
        "assets": {
            "figures": [
                {
                    "id": "fig1",
                    "type": "figure",
                    "label": "Figure 1",
                    "caption": "cap",
                    "caption_blocks": [],
                    "link": "fig1.jpg",
                    "alternate_links": [],
                    "graphics": [
                        {
                            "id": "g1",
                            "type": "graphic",
                            "href": "fig1.jpg",
                            "mime_type": "image/jpeg",
                            "content_type": "",
                            "source": {},
                            "local_path": "",
                            "download_status": "not_attempted",
                        }
                    ],
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
            ],
            "tables": [],
            "references": [],
            "equations": {"mathml": [], "tex": [], "records": []},
            "supplementary_material": [],
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


def _fake_fetch_success(image_basename: str = "fig1.jpg") -> AssetFetchResult:
    return AssetFetchResult(
        image_paths={image_basename: f"images/{image_basename}"},
        sources_tried=["oa_package"],
        bytes_downloaded=42,
        status="complete",
    )


def _invoke_cli(args: list[str], tmp_path: Path) -> int:
    """Invoke pmcgrab_cli.main() with patched argv; return its exit code."""
    full_args = ["pmcgrab", *args, "--output-dir", str(tmp_path / "out"), "--quiet"]
    with patch("sys.argv", full_args):
        return pmcgrab_cli.main()


def test_default_writes_flat_json(tmp_path: Path) -> None:
    """Without --with-images, default is the fast flat-file path."""
    article = _dummy_article("PMC123")
    with (
        patch.object(pmcgrab_cli, "process_single_pmc", return_value=article),
        patch.object(pmcgrab_cli, "process_single_pmc_with_assets") as mock_with_assets,
    ):
        code = _invoke_cli(["--pmcids", "123"], tmp_path)
    assert code == 0
    # Asset path NOT touched.
    mock_with_assets.assert_not_called()
    # Flat single file at out/PMC123.json.
    assert (tmp_path / "out" / "PMC123.json").is_file()
    assert not (tmp_path / "out" / "PMC123").exists()
    summary = json.loads((tmp_path / "out" / "summary.json").read_text())
    # 1.x-compatible shape: bare bool.
    assert summary == {"123": True}


def test_with_images_writes_folder_layout(tmp_path: Path) -> None:
    article = _dummy_article("PMC123")
    fetch_result = _fake_fetch_success()

    def fake_process_with_assets(
        pmc_id: Any, out_dir: Any, *, policy: Any, **kwargs: Any
    ) -> tuple[dict, AssetFetchResult]:
        # Mirror the orchestrator side-effect: write article.json + images/
        article_assembly.write_article_folder(
            Path(out_dir), pmc_id, article, fetch_result
        )
        (Path(out_dir) / "PMC123" / "images").mkdir(parents=True, exist_ok=True)
        (Path(out_dir) / "PMC123" / "images" / "fig1.jpg").write_bytes(b"img")
        return article, fetch_result

    with patch.object(
        pmcgrab_cli,
        "process_single_pmc_with_assets",
        side_effect=fake_process_with_assets,
    ):
        code = _invoke_cli(["--pmcids", "123", "--with-images"], tmp_path)
    assert code == 0

    out_dir = tmp_path / "out"
    assert (out_dir / "PMC123" / "article.json").is_file()
    assert (out_dir / "PMC123" / "images" / "fig1.jpg").is_file()
    summary = json.loads((out_dir / "summary.json").read_text())
    assert summary["123"]["parsed"] is True
    assert summary["123"]["asset_status"] == "complete"
    assert summary["123"]["image_count"] == 1


def test_jsonl_format_writes_aggregate(tmp_path: Path) -> None:
    article = _dummy_article("PMC123")
    with patch.object(pmcgrab_cli, "process_single_pmc", return_value=article):
        code = _invoke_cli(["--pmcids", "123", "--format", "jsonl"], tmp_path)
    assert code == 0
    aggregate = (tmp_path / "out" / "output.jsonl").read_text()
    assert json.loads(aggregate.strip())["article"]["identifiers"]["pmcid"] == "PMC123"


def test_with_images_and_include_supplementary(tmp_path: Path) -> None:
    article = _dummy_article()
    captured: dict[str, Any] = {}

    def fake(
        pmc_id: Any, out_dir: Any, *, policy: Any, **kwargs: Any
    ) -> tuple[dict, None]:
        captured["policy"] = policy
        article_assembly.write_article_folder(Path(out_dir), pmc_id, article, None)
        return article, None

    with patch.object(pmcgrab_cli, "process_single_pmc_with_assets", side_effect=fake):
        _invoke_cli(
            ["--pmcids", "123", "--with-images", "--include-supplementary"],
            tmp_path,
        )
    assert captured["policy"].fetch_supplementary is True


def test_with_images_and_include_raw_xml(tmp_path: Path) -> None:
    article = _dummy_article()
    captured: dict[str, Any] = {}

    def fake(
        pmc_id: Any, out_dir: Any, *, policy: Any, **kwargs: Any
    ) -> tuple[dict, None]:
        captured["policy"] = policy
        article_assembly.write_article_folder(Path(out_dir), pmc_id, article, None)
        return article, None

    with patch.object(pmcgrab_cli, "process_single_pmc_with_assets", side_effect=fake):
        _invoke_cli(["--pmcids", "123", "--with-images", "--include-raw-xml"], tmp_path)
    assert captured["policy"].save_raw_xml is True


def test_with_images_and_include_all_assets(tmp_path: Path) -> None:
    article = _dummy_article()
    captured: dict[str, Any] = {}

    def fake(
        pmc_id: Any, out_dir: Any, *, policy: Any, **kwargs: Any
    ) -> tuple[dict, None]:
        captured["policy"] = policy
        article_assembly.write_article_folder(Path(out_dir), pmc_id, article, None)
        return article, None

    with patch.object(pmcgrab_cli, "process_single_pmc_with_assets", side_effect=fake):
        _invoke_cli(
            ["--pmcids", "123", "--with-images", "--include-all-assets"], tmp_path
        )
    assert captured["policy"].fetch_supplementary is True
    assert captured["policy"].include_all_assets is True


def test_max_asset_bytes_zero_rejected(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        _invoke_cli(["--pmcids", "123", "--max-asset-bytes", "0"], tmp_path)


def test_with_images_passes_max_asset_bytes(tmp_path: Path) -> None:
    article = _dummy_article()
    captured: dict[str, Any] = {}

    def fake(
        pmc_id: Any, out_dir: Any, *, policy: Any, **kwargs: Any
    ) -> tuple[dict, None]:
        captured["policy"] = policy
        article_assembly.write_article_folder(Path(out_dir), pmc_id, article, None)
        return article, None

    with patch.object(pmcgrab_cli, "process_single_pmc_with_assets", side_effect=fake):
        _invoke_cli(
            ["--pmcids", "123", "--with-images", "--max-asset-bytes", "1024"],
            tmp_path,
        )
    assert captured["policy"].max_total_bytes == 1024


def test_local_xml_default_writes_flat(tmp_path: Path) -> None:
    """Local-XML default mode writes the flat single-file layout."""
    xml_path = tmp_path / "MyArticle.xml"
    xml_path.write_text(
        """<?xml version="1.0"?>
<article>
  <front>
    <journal-meta><journal-title>J</journal-title>
      <publisher><publisher-name>P</publisher-name></publisher>
    </journal-meta>
    <article-meta>
      <article-id pub-id-type="pmc">555</article-id>
      <title-group><article-title>Local Title</article-title></title-group>
      <abstract><p>Abstract.</p></abstract>
    </article-meta>
  </front>
  <body><sec><title>Intro</title><p>x</p></sec></body>
</article>""",
        encoding="utf-8",
    )
    code = _invoke_cli(["--from-file", str(xml_path)], tmp_path)
    assert code == 0
    assert (tmp_path / "out" / "MyArticle.json").is_file()
    assert not (tmp_path / "out" / "MyArticle").exists()


def test_local_xml_with_images_uses_folder(tmp_path: Path) -> None:
    """Local-XML mode with --with-images still uses the folder layout
    (no actual image fetching — local mode is offline)."""
    xml_path = tmp_path / "MyArticle.xml"
    xml_path.write_text(
        """<?xml version="1.0"?>
<article>
  <front>
    <journal-meta><journal-title>J</journal-title>
      <publisher><publisher-name>P</publisher-name></publisher>
    </journal-meta>
    <article-meta>
      <article-id pub-id-type="pmc">555</article-id>
      <title-group><article-title>Local Title</article-title></title-group>
      <abstract><p>x</p></abstract>
    </article-meta>
  </front>
  <body><sec><title>Intro</title><p>x</p></sec></body>
</article>""",
        encoding="utf-8",
    )
    code = _invoke_cli(["--from-file", str(xml_path), "--with-images"], tmp_path)
    assert code == 0
    # Folder layout uses stem of the XML filename.
    assert (tmp_path / "out" / "PMCMyArticle" / "article.json").is_file()


def test_dangling_image_flags_warn(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Using --include-* without --with-images emits a one-shot warning."""
    pmcgrab_cli._DANGLING_IMAGE_FLAG_WARNING_EMITTED = False
    article = _dummy_article()
    with patch.object(pmcgrab_cli, "process_single_pmc", return_value=article):
        _invoke_cli(["--pmcids", "123", "--include-supplementary"], tmp_path)
    captured = capsys.readouterr()
    assert "only take effect with --with-images" in captured.err


def test_local_xml_with_image_extra_flags_warn(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pmcgrab_cli._LOCAL_IMAGE_FLAG_WARNING_EMITTED = False
    pmcgrab_cli._DANGLING_IMAGE_FLAG_WARNING_EMITTED = False
    xml_path = tmp_path / "art.xml"
    xml_path.write_text(
        """<?xml version="1.0"?>
<article>
  <front>
    <journal-meta><journal-title>J</journal-title>
      <publisher><publisher-name>P</publisher-name></publisher>
    </journal-meta>
    <article-meta>
      <title-group><article-title>T</article-title></title-group>
      <abstract><p>x</p></abstract>
    </article-meta>
  </front>
  <body><sec><title>x</title><p>y</p></sec></body>
</article>""",
        encoding="utf-8",
    )
    _invoke_cli(
        ["--from-file", str(xml_path), "--with-images", "--include-supplementary"],
        tmp_path,
    )
    captured = capsys.readouterr()
    assert "image-fetching flags are ignored" in captured.err
