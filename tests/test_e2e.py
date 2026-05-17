"""End-to-end tests for installed-style PMCGrab workflows."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import pmcgrab
from pmcgrab.application.processing import process_single_pmc

LOCAL_E2E_JATS_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<article article-type="research-article" xml:lang="en">
  <front>
    <journal-meta>
      <journal-title>PMCGrab E2E Journal</journal-title>
      <publisher><publisher-name>PMCGrab Tests</publisher-name></publisher>
    </journal-meta>
    <article-meta>
      <article-id pub-id-type="pmc">7181753</article-id>
      <article-id pub-id-type="doi">10.1234/pmcgrab.e2e</article-id>
      <title-group>
        <article-title>PMCGrab Local E2E Article</article-title>
      </title-group>
      <contrib-group>
        <contrib contrib-type="author">
          <name><surname>Mondal</surname><given-names>Rajdeep</given-names></name>
        </contrib>
      </contrib-group>
      <abstract>
        <p>This abstract proves the local XML path works end to end.</p>
      </abstract>
    </article-meta>
  </front>
  <body>
    <sec>
      <title>Introduction</title>
      <p>Raw JATS XML is useful source material, not a finished context format.</p>
    </sec>
    <sec>
      <title>Methods</title>
      <p>The CLI parses a real XML file and writes normalized JSON output.</p>
    </sec>
    <sec>
      <title>Results</title>
      <p>The output keeps identifiers, title metadata, and section boundaries.</p>
    </sec>
  </body>
</article>
"""


@pytest.mark.e2e
def test_cli_local_xml_e2e_writes_json_and_summary(tmp_path: Path) -> None:
    """Run the package CLI over a real local XML file and inspect the output."""
    xml_path = tmp_path / "PMC7181753.xml"
    output_dir = tmp_path / "out"
    xml_path.write_text(LOCAL_E2E_JATS_XML, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pmcgrab",
            "--from-file",
            str(xml_path),
            "--output-dir",
            str(output_dir),
            "--quiet",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Done: 1/1 succeeded" in result.stdout

    output_path = output_dir / "PMC7181753.json"
    summary_path = output_dir / "summary.json"
    assert output_path.is_file()
    assert summary_path.is_file()

    raw_output = output_path.read_text(encoding="utf-8")
    data = json.loads(raw_output)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert "NaN" not in raw_output
    assert summary == {"PMC7181753": True}
    assert data["schema_version"] == 2
    assert data["has_data"] is True
    assert data["identifiers"]["pmcid"] == "PMC7181753"
    assert data["identifiers"]["doi"] == "10.1234/pmcgrab.e2e"
    assert data["title"]["main"] == "PMCGrab Local E2E Article"
    assert data["provenance"]["source"] == "local_xml"
    assert data["provenance"]["pmcgrab_version"] == pmcgrab.__version__
    assert [section["title"] for section in data["content"]["sections"]] == [
        "Introduction",
        "Methods",
        "Results",
    ]


@pytest.mark.e2e
@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("PMCGRAB_RUN_LIVE_E2E") != "1",
    reason="set PMCGRAB_RUN_LIVE_E2E=1 to make a live NCBI request",
)
def test_live_ncbi_process_single_pmc_e2e() -> None:
    """Smoke-test the real NCBI fetch and parse path for release confidence."""
    data = process_single_pmc("7181753", timeout=90)

    assert data is not None
    assert data["schema_version"] == 2
    assert data["has_data"] is True
    assert data["identifiers"]["pmcid"] == "PMC7181753"
    assert data["title"]["main"].startswith("Single-cell transcriptomes")
    assert data["provenance"]["source"] == "ncbi_entrez"
    assert data["provenance"]["pmcgrab_version"] == pmcgrab.__version__
    assert len(data["content"]["sections"]) >= 1
