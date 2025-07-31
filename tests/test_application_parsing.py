"""Tests for pmcgrab.application.parsing modules."""

import datetime

import lxml.etree as ET
import pandas as pd

from pmcgrab.application.parsing import content, contributors, metadata, sections
from pmcgrab.utils import BasicBiMap


class TestContentParsing:
    """Test content parsing functions."""

    def test_gather_permissions(self):
        """Test permissions gathering."""
        xml = """<article>
            <article-meta>
                <permissions>
                    <copyright-statement>Copyright 2024</copyright-statement>
                    <license license-type="open-access">
                        <license-p>This is open access</license-p>
                    </license>
                </permissions>
            </article-meta>
        </article>"""
        root = ET.fromstring(xml)

        result = content.gather_permissions(root)

        assert isinstance(result, dict)
        assert "Copyright Statement" in result
        assert "License Type" in result
        assert "License Text" in result
        assert result["Copyright Statement"] == "Copyright 2024"
        assert result["License Type"] == "open-access"

    def test_gather_permissions_no_permissions(self):
        """Test permissions gathering with no permissions."""
        xml = "<article><article-meta></article-meta></article>"
        root = ET.fromstring(xml)

        result = content.gather_permissions(root)

        assert result is None

    def test_gather_funding(self):
        """Test funding information gathering."""
        xml = """<article>
            <article-meta>
                <funding-group>
                    <award-group>
                        <funding-source>
                            <institution>NIH</institution>
                        </funding-source>
                    </award-group>
                    <award-group>
                        <funding-source>
                            <institution>NSF</institution>
                        </funding-source>
                    </award-group>
                </funding-group>
            </article-meta>
        </article>"""
        root = ET.fromstring(xml)

        result = content.gather_funding(root)

        assert isinstance(result, list)
        assert "NIH" in result
        assert "NSF" in result

    def test_gather_funding_no_funding(self):
        """Test funding gathering with no funding info."""
        xml = "<article><article-meta></article-meta></article>"
        root = ET.fromstring(xml)

        result = content.gather_funding(root)

        assert result is None

    def test_gather_equations(self):
        """Test equation gathering."""
        xml = """<article xmlns:mml="http://www.w3.org/1998/Math/MathML">
            <body>
                <mml:math>
                    <mml:mi>x</mml:mi>
                    <mml:mo>=</mml:mo>
                    <mml:mn>1</mml:mn>
                </mml:math>
            </body>
        </article>"""
        root = ET.fromstring(xml)

        result = content.gather_equations(root)

        assert isinstance(result, list)
        assert len(result) > 0
        # Should contain MathML content
        assert "math" in result[0]

    def test_gather_equations_no_equations(self):
        """Test equation gathering with no equations."""
        xml = "<article><body><p>No equations here</p></body></article>"
        root = ET.fromstring(xml)

        result = content.gather_equations(root)

        assert result is None

    def test_gather_supplementary_material(self):
        """Test supplementary material gathering."""
        xml = """<article xmlns:xlink="http://www.w3.org/1999/xlink">
            <body>
                <supplementary-material id="sup1" xlink:href="supplement.pdf">
                    <label>Supplementary Material</label>
                    <caption><p>Additional data</p></caption>
                </supplementary-material>
            </body>
        </article>"""
        root = ET.fromstring(xml)

        result = content.gather_supplementary_material(root)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["Label"] == "Supplementary Material"
        assert "Additional data" in result[0]["Caption"]
        assert result[0]["Href"] == "supplement.pdf"

    def test_gather_supplementary_material_none(self):
        """Test supplementary material gathering with none present."""
        xml = "<article><body><p>No supplementary material</p></body></article>"
        root = ET.fromstring(xml)

        result = content.gather_supplementary_material(root)

        assert result is None


class TestContributorsParsing:
    """Test contributors parsing functions."""

    def test_gather_authors(self):
        """Test author gathering."""
        xml = """<article>
            <contrib-group>
                <contrib contrib-type="author" equal-contrib="yes">
                    <name>
                        <surname>Doe</surname>
                        <given-names>Jane</given-names>
                    </name>
                    <contrib-id contrib-id-type="orcid">0000-0001-2345-6789</contrib-id>
                    <address><email>jane@example.com</email></address>
                    <xref ref-type="aff" rid="aff1"/>
                </contrib>
                <aff id="aff1">
                    <institution>Test University</institution>
                    <addr-line>Test City</addr-line>
                </aff>
            </contrib-group>
        </article>"""
        root = ET.fromstring(xml)

        result = contributors.gather_authors(root)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]["First_Name"] == "Jane"
        assert result.iloc[0]["Last_Name"] == "Doe"
        assert result.iloc[0]["ORCID"] == "0000-0001-2345-6789"
        assert result.iloc[0]["Email_Address"] == "jane@example.com"
        assert result.iloc[0]["Equal_Contrib"] is True

    def test_gather_authors_no_authors(self):
        """Test author gathering with no authors."""
        xml = "<article><contrib-group></contrib-group></article>"
        root = ET.fromstring(xml)

        result = contributors.gather_authors(root)

        assert result is None

    def test_gather_non_author_contributors(self):
        """Test non-author contributor gathering."""
        xml = """<article>
            <contrib-group>
                <contrib contrib-type="editor">
                    <name>
                        <surname>Smith</surname>
                        <given-names>John</given-names>
                    </name>
                </contrib>
            </contrib-group>
        </article>"""
        root = ET.fromstring(xml)

        result = contributors.gather_non_author_contributors(root)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]["Contributor_Type"] == "Editor"
        assert result.iloc[0]["First_Name"] == "John"
        assert result.iloc[0]["Last_Name"] == "Smith"

    def test_gather_non_author_contributors_none(self):
        """Test non-author contributor gathering with none present."""
        xml = """<article>
            <contrib-group>
                <contrib contrib-type="author">
                    <name><surname>Doe</surname></name>
                </contrib>
            </contrib-group>
        </article>"""
        root = ET.fromstring(xml)

        result = contributors.gather_non_author_contributors(root)

        assert isinstance(result, str)
        assert "No non-author contributors found" in result


class TestMetadataParsing:
    """Test metadata parsing functions."""

    def test_gather_title(self):
        """Test title gathering."""
        xml = """<article>
            <front>
                <article-meta>
                    <title-group>
                        <article-title>Test Article Title</article-title>
                    </title-group>
                </article-meta>
            </front>
        </article>"""
        root = ET.fromstring(xml)

        result = metadata.gather_title(root)

        assert result == "Test Article Title"

    def test_gather_title_no_title(self):
        """Test title gathering with no title."""
        xml = "<article><front><article-meta></article-meta></front></article>"
        root = ET.fromstring(xml)

        result = metadata.gather_title(root)

        assert result is None

    def test_gather_journal_title(self):
        """Test journal title gathering."""
        xml = """<article>
            <front>
                <journal-meta>
                    <journal-title>Test Journal</journal-title>
                </journal-meta>
            </front>
        </article>"""
        root = ET.fromstring(xml)

        result = metadata.gather_journal_title(root)

        assert result == "Test Journal"

    def test_gather_journal_id(self):
        """Test journal ID gathering."""
        xml = """<article>
            <front>
                <journal-meta>
                    <journal-id journal-id-type="pmc">testjournal</journal-id>
                    <journal-id journal-id-type="issn">1234-5678</journal-id>
                </journal-meta>
            </front>
        </article>"""
        root = ET.fromstring(xml)

        result = metadata.gather_journal_id(root)

        assert isinstance(result, dict)
        assert result["pmc"] == "testjournal"
        assert result["issn"] == "1234-5678"

    def test_gather_published_date(self):
        """Test published date gathering."""
        xml = """<article>
            <front>
                <article-meta>
                    <pub-date pub-type="epub">
                        <year>2024</year>
                        <month>1</month>
                        <day>15</day>
                    </pub-date>
                </article-meta>
            </front>
        </article>"""
        root = ET.fromstring(xml)

        result = metadata.gather_published_date(root)

        assert isinstance(result, dict)
        assert "epub" in result
        assert result["epub"] == datetime.date(2024, 1, 15)

    def test_gather_keywords(self):
        """Test keyword gathering."""
        xml = """<article>
            <front>
                <article-meta>
                    <kwd-group kwd-group-type="author">
                        <kwd>machine learning</kwd>
                        <kwd>artificial intelligence</kwd>
                    </kwd-group>
                </article-meta>
            </front>
        </article>"""
        root = ET.fromstring(xml)

        result = metadata.gather_keywords(root)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert "author" in result[0]
        assert "machine learning" in result[0]["author"]
        assert "artificial intelligence" in result[0]["author"]

    def test_gather_volume_issue(self):
        """Test volume and issue gathering."""
        xml = """<article>
            <front>
                <article-meta>
                    <volume>10</volume>
                    <issue>3</issue>
                </article-meta>
            </front>
        </article>"""
        root = ET.fromstring(xml)

        volume = metadata.gather_volume(root)
        issue = metadata.gather_issue(root)

        assert volume == "10"
        assert issue == "3"


class TestSectionsParsing:
    """Test sections parsing functions."""

    def test_gather_abstract(self):
        """Test abstract gathering."""
        xml = """<article>
            <front>
                <article-meta>
                    <abstract>
                        <p>This is the abstract content.</p>
                    </abstract>
                </article-meta>
            </front>
        </article>"""
        root = ET.fromstring(xml)
        ref_map = BasicBiMap()

        result = sections.gather_abstract(root, ref_map)

        assert isinstance(result, list)
        assert len(result) > 0
        # Should contain paragraph objects
        assert hasattr(result[0], "__str__")

    def test_gather_abstract_no_abstract(self):
        """Test abstract gathering with no abstract."""
        xml = "<article><front><article-meta></article-meta></front></article>"
        root = ET.fromstring(xml)
        ref_map = BasicBiMap()

        result = sections.gather_abstract(root, ref_map)

        assert result is None

    def test_gather_body(self):
        """Test body gathering."""
        xml = """<article>
            <body>
                <sec>
                    <title>Introduction</title>
                    <p>This is the introduction.</p>
                </sec>
                <sec>
                    <title>Methods</title>
                    <p>This is the methods section.</p>
                </sec>
            </body>
        </article>"""
        root = ET.fromstring(xml)
        ref_map = BasicBiMap()

        result = sections.gather_body(root, ref_map)

        assert isinstance(result, list)
        assert len(result) == 2
        # Should contain section objects
        assert hasattr(result[0], "title")
        assert hasattr(result[1], "title")

    def test_gather_body_no_body(self):
        """Test body gathering with no body."""
        xml = "<article><front></front></article>"
        root = ET.fromstring(xml)
        ref_map = BasicBiMap()

        result = sections.gather_body(root, ref_map)

        assert result is None
