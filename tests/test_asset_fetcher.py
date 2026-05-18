"""Unit tests for the OA tar.gz + bin/ asset fetcher."""

from __future__ import annotations

import io
import tarfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

from pmcgrab.infrastructure import asset_fetcher
from pmcgrab.infrastructure.asset_fetcher import (
    AssetFetchPolicy,
    download_article_assets,
    fetch_individual_assets,
    fetch_oa_package_assets,
)


def _make_tar_bytes(members: list[tuple[str, bytes]]) -> bytes:
    """Build an in-memory ``.tar.gz`` blob from (name, payload) tuples."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, payload in members:
            info = tarfile.TarInfo(name=name)
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
    return buf.getvalue()


def _make_tar_symlink_bytes() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        info = tarfile.TarInfo(name="bad_symlink")
        info.type = tarfile.SYMTYPE
        info.linkname = "/etc/passwd"
        tar.addfile(info)
    return buf.getvalue()


class _FakeResponse:
    """Minimal stand-in for requests.Response.

    Wraps a bytes payload so the tar.gz fetcher can stream it via
    ``resp.raw`` (a ``BytesIO``). Supports ``raise_for_status``,
    ``iter_content``, ``close``, and the ``raw.decode_content`` attribute.
    """

    def __init__(self, content: bytes, status_code: int = 200) -> None:
        self.status_code = status_code
        self.content = content
        self.raw = io.BytesIO(content)
        # Attach the attribute the fetcher writes to.
        self.raw.decode_content = False  # type: ignore[attr-defined]

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            err = requests.HTTPError(f"HTTP {self.status_code}")
            raise err

    def iter_content(self, chunk_size: int = 65536):
        # iter_content is used by fetch_individual_assets, not the tar path.
        data = self.content
        for i in range(0, len(data), chunk_size):
            yield data[i : i + chunk_size]

    def close(self) -> None:
        return None


@pytest.fixture(autouse=True)
def _disable_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(asset_fetcher, "rate_limit_wait", lambda: None)
    # Stub sleep so retries are instant if anything ever calls it.
    monkeypatch.setattr(time, "sleep", lambda *a, **kw: None)


def test_fetch_oa_package_extracts_wanted_images(tmp_path: Path) -> None:
    tar_bytes = _make_tar_bytes(
        [
            ("PMC1/fig1.jpg", b"jpeg1"),
            ("PMC1/fig2.jpg", b"jpeg2"),
            ("PMC1/other.txt", b"unrelated"),
        ]
    )
    with (
        patch.object(
            asset_fetcher, "tgz_url_for", return_value="https://example/p.tar.gz"
        ),
        patch.object(
            asset_fetcher._build_session(), "get", return_value=_FakeResponse(tar_bytes)
        ),
    ):
        result = fetch_oa_package_assets(
            "1",
            tmp_path,
            wanted_basenames={"fig1.jpg", "fig2.jpg"},
            policy=AssetFetchPolicy(),
        )
    assert result.status == "complete"
    assert result.image_paths == {
        "fig1.jpg": "images/fig1.jpg",
        "fig2.jpg": "images/fig2.jpg",
    }
    assert (tmp_path / "images" / "fig1.jpg").read_bytes() == b"jpeg1"
    assert (tmp_path / "images" / "fig2.jpg").read_bytes() == b"jpeg2"
    # Unwanted file ignored.
    assert not (tmp_path / "other.txt").exists()


def test_fetch_oa_package_handles_no_tgz(tmp_path: Path) -> None:
    with patch.object(asset_fetcher, "tgz_url_for", return_value=None):
        result = fetch_oa_package_assets(
            "1",
            tmp_path,
            wanted_basenames={"fig1.jpg"},
            policy=AssetFetchPolicy(),
        )
    assert result.status == "failed"
    assert result.errors[0]["code"] == "oa_not_available"


def test_fetch_oa_package_handles_http_error(tmp_path: Path) -> None:
    with (
        patch.object(
            asset_fetcher, "tgz_url_for", return_value="https://example/p.tar.gz"
        ),
        patch.object(
            asset_fetcher._build_session(),
            "get",
            side_effect=requests.RequestException("boom"),
        ),
    ):
        result = fetch_oa_package_assets(
            "1",
            tmp_path,
            wanted_basenames={"fig1.jpg"},
            policy=AssetFetchPolicy(),
        )
    assert result.status == "failed"
    assert result.errors[0]["code"] == "oa_tgz_http_error"


def test_fetch_oa_package_rejects_symlink(tmp_path: Path) -> None:
    tar_bytes = _make_tar_symlink_bytes()
    with (
        patch.object(
            asset_fetcher, "tgz_url_for", return_value="https://example/p.tar.gz"
        ),
        patch.object(
            asset_fetcher._build_session(), "get", return_value=_FakeResponse(tar_bytes)
        ),
    ):
        result = fetch_oa_package_assets(
            "1",
            tmp_path,
            wanted_basenames={"bad_symlink"},
            policy=AssetFetchPolicy(),
        )
    # No file was extracted (skipped), and an error was recorded.
    assert result.image_paths == {}
    codes = [err["code"] for err in result.errors]
    assert "tar_unsafe_member" in codes


def test_fetch_oa_package_aborts_on_size_ceiling(tmp_path: Path) -> None:
    # Two images, each 1 KB; ceiling at 512 bytes.
    big = b"x" * 1024
    tar_bytes = _make_tar_bytes(
        [
            ("PMC1/big1.jpg", big),
            ("PMC1/big2.jpg", big),
        ]
    )
    with (
        patch.object(
            asset_fetcher, "tgz_url_for", return_value="https://example/p.tar.gz"
        ),
        patch.object(
            asset_fetcher._build_session(), "get", return_value=_FakeResponse(tar_bytes)
        ),
    ):
        result = fetch_oa_package_assets(
            "1",
            tmp_path,
            wanted_basenames={"big1.jpg", "big2.jpg"},
            policy=AssetFetchPolicy(max_total_bytes=512),
        )
    assert result.status == "failed"
    codes = [err["code"] for err in result.errors]
    assert "asset_size_limit" in codes
    # Both partials should be removed.
    assert not (tmp_path / "images" / "big1.jpg").exists()
    assert not (tmp_path / "images" / "big2.jpg").exists()


def test_fetch_oa_package_saves_raw_xml(tmp_path: Path) -> None:
    tar_bytes = _make_tar_bytes(
        [
            ("PMC1/PMC1.nxml", b"<article/>"),
            ("PMC1/fig1.jpg", b"jpeg"),
        ]
    )
    with (
        patch.object(
            asset_fetcher, "tgz_url_for", return_value="https://example/p.tar.gz"
        ),
        patch.object(
            asset_fetcher._build_session(), "get", return_value=_FakeResponse(tar_bytes)
        ),
    ):
        result = fetch_oa_package_assets(
            "1",
            tmp_path,
            wanted_basenames={"fig1.jpg"},
            policy=AssetFetchPolicy(save_raw_xml=True),
        )
    assert result.raw_xml_path == "raw.xml"
    assert (tmp_path / "raw.xml").read_bytes() == b"<article/>"


def test_fetch_individual_assets_writes_files(tmp_path: Path) -> None:
    rate_calls = MagicMock()
    with patch.object(asset_fetcher, "rate_limit_wait", rate_calls):
        with patch.object(
            asset_fetcher._build_session(),
            "get",
            side_effect=lambda url, **kw: _FakeResponse(
                b"jpeg-bytes-for-" + url.split("/")[-1].encode()
            ),
        ):
            result = fetch_individual_assets(
                "PMC123",
                ["fig1.jpg", "fig2.jpg"],
                tmp_path,
                policy=AssetFetchPolicy(),
            )
    assert result.status == "complete"
    assert result.image_paths == {
        "fig1.jpg": "images/fig1.jpg",
        "fig2.jpg": "images/fig2.jpg",
    }
    assert rate_calls.call_count == 2
    assert (tmp_path / "images" / "fig1.jpg").exists()


def test_fetch_individual_assets_skips_already_on_disk(tmp_path: Path) -> None:
    (tmp_path / "images").mkdir()
    (tmp_path / "images" / "fig1.jpg").write_bytes(b"already-here")
    called: list[str] = []

    def _side(url: str, **kw: Any) -> _FakeResponse:
        called.append(url)
        return _FakeResponse(b"new-bytes")

    with patch.object(asset_fetcher._build_session(), "get", side_effect=_side):
        result = fetch_individual_assets(
            "PMC123",
            ["fig1.jpg"],
            tmp_path,
            policy=AssetFetchPolicy(),
        )
    assert called == []
    assert result.image_paths == {"fig1.jpg": "images/fig1.jpg"}
    # Existing bytes preserved.
    assert (tmp_path / "images" / "fig1.jpg").read_bytes() == b"already-here"


def test_fetch_individual_assets_handles_404(tmp_path: Path) -> None:
    def _side(url: str, **kw: Any) -> _FakeResponse:
        if "fig1.jpg" in url:
            return _FakeResponse(b"good")
        return _FakeResponse(b"", status_code=404)

    with patch.object(asset_fetcher._build_session(), "get", side_effect=_side):
        result = fetch_individual_assets(
            "PMC123",
            ["fig1.jpg", "fig2.jpg"],
            tmp_path,
            policy=AssetFetchPolicy(),
        )
    assert "fig1.jpg" in result.image_paths
    assert "fig2.jpg" not in result.image_paths
    codes = [err["code"] for err in result.errors]
    assert "bin_not_found" in codes
    assert result.status == "partial"


def test_download_article_assets_falls_back_to_bin(tmp_path: Path) -> None:
    figure_records = [
        {
            "id": "fig1",
            "link": "fig1.jpg",
            "alternate_links": [],
            "graphics": [{"href": "fig1.jpg"}],
        }
    ]
    # OA bundle finds nothing.
    with (
        patch.object(asset_fetcher, "tgz_url_for", return_value=None),
        patch.object(
            asset_fetcher._build_session(),
            "get",
            side_effect=lambda url, **kw: _FakeResponse(b"bin-bytes"),
        ),
    ):
        result = download_article_assets(
            "123",
            figure_records,
            [],
            tmp_path,
            policy=AssetFetchPolicy(),
        )
    assert "oa_package" in result.sources_tried
    assert "bin_fallback" in result.sources_tried
    assert result.image_paths == {"fig1.jpg": "images/fig1.jpg"}
    assert (tmp_path / "images" / "fig1.jpg").read_bytes() == b"bin-bytes"


def test_download_article_assets_nothing_to_do_when_no_figures(tmp_path: Path) -> None:
    result = download_article_assets(
        "123",
        [],
        [],
        tmp_path,
        policy=AssetFetchPolicy(),
    )
    assert result.status == "empty"
    assert result.image_paths == {}
    # No images/ subdir was left behind.
    assert not (tmp_path / "images").exists()


def test_download_article_assets_disabled_returns_empty(tmp_path: Path) -> None:
    figure_records = [{"id": "fig1", "link": "fig1.jpg", "graphics": []}]
    result = download_article_assets(
        "123",
        figure_records,
        [],
        tmp_path,
        policy=AssetFetchPolicy(fetch_images=False, fetch_supplementary=False),
    )
    assert result.status == "empty"
    assert result.image_paths == {}
