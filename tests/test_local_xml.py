"""Tests for local XML file processing (bulk mode).

Covers:
    - fetch.parse_local_xml()
    - parser.paper_dict_from_local_xml()
    - application.processing.process_single_local_xml()
    - application.processing.process_local_xml_dir()
    - CLI --from-dir / --from-file flags
"""

import json
import warnings
from pathlib import Path
from unittest.mock import patch

import lxml.etree as ET

from pmcgrab.application.processing import (
    process_local_xml_dir,
    process_single_local_xml,
)
from pmcgrab.fetch import parse_local_xml
from pmcgrab.parser import paper_dict_from_local_xml

# ---------------------------------------------------------------------------
# Sample JATS XML for testing (standalone article, no pmc-articleset wrapper)
# ---------------------------------------------------------------------------

SAMPLE_JATS_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<article article-type="research-article" xml:lang="en">
  <front>
    <journal-meta>
      <journal-id journal-id-type="pmc">testjournal</journal-id>
      <journal-title>Test Journal of Science</journal-title>
      <issn pub-type="epub">9999-0001</issn>
      <publisher>
        <publisher-name>Test Publisher Inc.</publisher-name>
        <publisher-loc>New York</publisher-loc>
      </publisher>
    </journal-meta>
    <article-meta>
      <article-id pub-id-type="pmc">7181753</article-id>
      <article-id pub-id-type="doi">10.1234/test.2024.001</article-id>
      <title-group>
        <article-title>Local XML Test Article</article-title>
      </title-group>
      <contrib-group>
        <contrib contrib-type="author">
          <name><surname>Smith</surname><given-names>Alice</given-names></name>
        </contrib>
        <contrib contrib-type="author">
          <name><surname>Jones</surname><given-names>Bob</given-names></name>
        </contrib>
      </contrib-group>
      <pub-date pub-type="epub">
        <day>10</day><month>06</month><year>2024</year>
      </pub-date>
      <volume>42</volume>
      <issue>3</issue>
      <abstract>
        <p>This is the abstract of the test article about local XML parsing.</p>
      </abstract>
      <kwd-group>
        <kwd>testing</kwd>
        <kwd>local XML</kwd>
      </kwd-group>
      <permissions>
        <copyright-statement>Copyright 2024 Test Publisher</copyright-statement>
        <license license-type="open-access">
          <license-p>CC BY 4.0</license-p>
        </license>
      </permissions>
    </article-meta>
  </front>
  <body>
    <sec>
      <title>Introduction</title>
      <p>This is the introduction paragraph of the test article.</p>
    </sec>
    <sec>
      <title>Methods</title>
      <p>We used a local XML parsing approach for testing purposes.</p>
    </sec>
    <sec>
      <title>Results</title>
      <p>The results show that local XML parsing works correctly.</p>
    </sec>
    <sec>
      <title>Discussion</title>
      <p>Local XML parsing provides a much faster alternative to network fetching.</p>
    </sec>
  </body>
  <back>
    <ref-list>
      <ref id="B1">
        <element-citation publication-type="journal">
          <person-group person-group-type="author">
            <name><surname>Doe</surname><given-names>Jane</given-names></name>
          </person-group>
          <article-title>Referenced article</article-title>
          <source>Other Journal</source>
          <year>2023</year>
        </element-citation>
      </ref>
    </ref-list>
  </back>
</article>
"""

# A second article (minimal) for batch testing
SAMPLE_JATS_XML_2 = """\
<?xml version="1.0" encoding="UTF-8"?>
<article article-type="research-article">
  <front>
    <journal-meta>
      <journal-id journal-id-type="pmc">j2</journal-id>
      <journal-title>Another Journal</journal-title>
    </journal-meta>
    <article-meta>
      <article-id pub-id-type="pmc">1234567</article-id>
      <title-group>
        <article-title>Second Test Article</article-title>
      </title-group>
      <abstract><p>Second abstract.</p></abstract>
    </article-meta>
  </front>
  <body>
    <sec><title>Content</title><p>Some body text here.</p></sec>
  </body>
</article>
"""


def _write_xml(directory: Path, filename: str, content: str) -> Path:
    """Helper: write XML string to a file inside *directory*."""
    fp = directory / filename
    fp.write_text(content, encoding="utf-8")
    return fp


# ===================================================================
# Tests for parse_local_xml()
# ===================================================================


class TestParseLocalXml:
    """Tests for pmcgrab.fetch.parse_local_xml."""

    def test_basic_parse(self, tmp_path):
        fp = _write_xml(tmp_path, "PMC7181753.xml", SAMPLE_JATS_XML)
        tree, pmcid = parse_local_xml(fp)
        assert isinstance(tree, ET._ElementTree)
        assert pmcid == 7181753

    def test_extracts_pmcid_from_xml(self, tmp_path):
        fp = _write_xml(tmp_path, "article.xml", SAMPLE_JATS_XML)
        _, pmcid = parse_local_xml(fp)
        assert pmcid == 7181753

    def test_missing_pmcid_returns_none(self, tmp_path):
        xml_no_pmcid = """\
<?xml version="1.0" encoding="UTF-8"?>
<article><front><article-meta>
  <title-group><article-title>No ID</article-title></title-group>
</article-meta></front>
<body><sec><title>S</title><p>text</p></sec></body></article>"""
        fp = _write_xml(tmp_path, "no_id.xml", xml_no_pmcid)
        _, pmcid = parse_local_xml(fp)
        assert pmcid is None

    def test_file_not_found(self):
        import pytest

        with pytest.raises(FileNotFoundError):
            parse_local_xml("/nonexistent/path/file.xml")

    def test_string_path(self, tmp_path):
        fp = _write_xml(tmp_path, "test.xml", SAMPLE_JATS_XML)
        tree, pmcid = parse_local_xml(str(fp))
        assert pmcid == 7181753

    def test_strip_text_styling_false(self, tmp_path):
        fp = _write_xml(tmp_path, "test.xml", SAMPLE_JATS_XML)
        tree, _ = parse_local_xml(fp, strip_text_styling=False)
        assert tree.getroot() is not None

    def test_validate_flag(self, tmp_path):
        """Validation with no DTD should warn but not crash."""
        fp = _write_xml(tmp_path, "test.xml", SAMPLE_JATS_XML)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tree, _ = parse_local_xml(fp, validate=True)
            assert tree.getroot() is not None


# ===================================================================
# Tests for paper_dict_from_local_xml()
# ===================================================================


class TestPaperDictFromLocalXml:
    """Tests for pmcgrab.parser.paper_dict_from_local_xml."""

    def test_basic_parse(self, tmp_path):
        fp = _write_xml(tmp_path, "test.xml", SAMPLE_JATS_XML)
        d = paper_dict_from_local_xml(str(fp))
        assert d["Title"] == "Local XML Test Article"
        assert d["PMCID"] == 7181753

    def test_body_sections(self, tmp_path):
        fp = _write_xml(tmp_path, "test.xml", SAMPLE_JATS_XML)
        d = paper_dict_from_local_xml(str(fp))
        body = d.get("Body", [])
        assert len(body) >= 4
        titles = [s.title for s in body if hasattr(s, "title")]
        assert "Introduction" in titles
        assert "Methods" in titles

    def test_abstract(self, tmp_path):
        fp = _write_xml(tmp_path, "test.xml", SAMPLE_JATS_XML)
        d = paper_dict_from_local_xml(str(fp))
        abstract_sections = d.get("Abstract", [])
        assert len(abstract_sections) > 0

    def test_journal_metadata(self, tmp_path):
        fp = _write_xml(tmp_path, "test.xml", SAMPLE_JATS_XML)
        d = paper_dict_from_local_xml(str(fp))
        assert d["Journal Title"] == "Test Journal of Science"
        assert d["Volume"] == "42"

    def test_suppress_errors(self, tmp_path):
        fp = _write_xml(tmp_path, "bad.xml", "<invalid>not valid JATS</invalid>")
        d = paper_dict_from_local_xml(str(fp), suppress_errors=True)
        # Should not raise, returns empty dict or partial
        assert isinstance(d, dict)

    def test_missing_pmcid_uses_zero(self, tmp_path):
        xml_no_id = """\
<?xml version="1.0" encoding="UTF-8"?>
<article><front><article-meta>
  <title-group><article-title>No PMC ID</article-title></title-group>
</article-meta></front>
<body><sec><title>S</title><p>text</p></sec></body></article>"""
        fp = _write_xml(tmp_path, "no_id.xml", xml_no_id)
        d = paper_dict_from_local_xml(str(fp))
        assert d["PMCID"] == 0


# ===================================================================
# Tests for process_single_local_xml()
# ===================================================================


class TestProcessSingleLocalXml:
    """Tests for pmcgrab.application.processing.process_single_local_xml."""

    def test_returns_dict_for_valid_xml(self, tmp_path):
        fp = _write_xml(tmp_path, "PMC7181753.xml", SAMPLE_JATS_XML)
        result = process_single_local_xml(fp)
        assert result is not None
        assert result["title"] == "Local XML Test Article"
        assert result["pmc_id"] == "7181753"
        assert isinstance(result["body"], dict)
        assert len(result["body"]) >= 4

    def test_returns_none_for_empty_xml(self, tmp_path):
        fp = _write_xml(tmp_path, "empty.xml", "<article></article>")
        result = process_single_local_xml(fp)
        assert result is None

    def test_returns_none_for_missing_file(self):
        result = process_single_local_xml("/nonexistent/file.xml")
        assert result is None

    def test_body_keys_are_section_titles(self, tmp_path):
        fp = _write_xml(tmp_path, "test.xml", SAMPLE_JATS_XML)
        result = process_single_local_xml(fp)
        assert result is not None
        assert "Introduction" in result["body"]
        assert "Methods" in result["body"]
        assert "Results" in result["body"]
        assert "Discussion" in result["body"]


# ===================================================================
# Tests for process_local_xml_dir()
# ===================================================================


class TestProcessLocalXmlDir:
    """Tests for pmcgrab.application.processing.process_local_xml_dir."""

    def test_processes_all_xml_files(self, tmp_path):
        _write_xml(tmp_path, "PMC7181753.xml", SAMPLE_JATS_XML)
        _write_xml(tmp_path, "PMC1234567.xml", SAMPLE_JATS_XML_2)

        results = process_local_xml_dir(tmp_path, workers=2)
        assert len(results) == 2
        assert "PMC7181753" in results
        assert "PMC1234567" in results

    def test_returns_none_for_bad_files(self, tmp_path):
        _write_xml(tmp_path, "bad.xml", "<article></article>")
        results = process_local_xml_dir(tmp_path, workers=1)
        assert results.get("bad") is None

    def test_custom_pattern(self, tmp_path):
        _write_xml(tmp_path, "article.jats", SAMPLE_JATS_XML)
        _write_xml(tmp_path, "article.xml", SAMPLE_JATS_XML_2)

        results = process_local_xml_dir(tmp_path, pattern="*.jats", workers=1)
        assert len(results) == 1
        assert "article" in results

    def test_empty_directory(self, tmp_path):
        results = process_local_xml_dir(tmp_path, workers=1)
        assert results == {}

    def test_mixed_valid_and_invalid(self, tmp_path):
        _write_xml(tmp_path, "good.xml", SAMPLE_JATS_XML)
        _write_xml(tmp_path, "empty.xml", "<article></article>")

        results = process_local_xml_dir(tmp_path, workers=2)
        assert results.get("good") is not None
        assert results.get("empty") is None


# ===================================================================
# Tests for CLI --from-dir / --from-file
# ===================================================================


class TestCLILocalFlags:
    """Tests for CLI local XML flags."""

    def test_cli_from_file(self, tmp_path):
        xml_fp = _write_xml(tmp_path, "PMC7181753.xml", SAMPLE_JATS_XML)
        out_dir = tmp_path / "output"

        with patch(
            "sys.argv",
            ["pmcgrab", "--from-file", str(xml_fp), "--output-dir", str(out_dir)],
        ):
            from pmcgrab.cli.pmcgrab_cli import main

            main()

        assert out_dir.exists()
        json_file = out_dir / "PMC7181753.json"
        assert json_file.exists()
        data = json.loads(json_file.read_text(encoding="utf-8"))
        assert data["title"] == "Local XML Test Article"

    def test_cli_from_dir(self, tmp_path):
        xml_dir = tmp_path / "xml_input"
        xml_dir.mkdir()
        _write_xml(xml_dir, "PMC7181753.xml", SAMPLE_JATS_XML)
        _write_xml(xml_dir, "PMC1234567.xml", SAMPLE_JATS_XML_2)
        out_dir = tmp_path / "output"

        with patch(
            "sys.argv",
            ["pmcgrab", "--from-dir", str(xml_dir), "--output-dir", str(out_dir)],
        ):
            from pmcgrab.cli.pmcgrab_cli import main

            main()

        assert out_dir.exists()
        summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
        assert len(summary) == 2

    def test_cli_from_dir_nonexistent(self, tmp_path, capsys):
        with patch(
            "sys.argv",
            [
                "pmcgrab",
                "--from-dir",
                "/nonexistent/dir",
                "--output-dir",
                str(tmp_path),
            ],
        ):
            from pmcgrab.cli.pmcgrab_cli import main

            main()

        captured = capsys.readouterr()
        assert "not a directory" in captured.out
