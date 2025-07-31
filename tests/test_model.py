"""Tests for pmcgrab.model module."""

import lxml.etree as ET
import pandas as pd
import pytest

from pmcgrab.model import Paper, TextSection, TextParagraph, TextTable, TextFigure
from pmcgrab.utils import BasicBiMap


class TestPaper:
    """Test the Paper class."""

    def test_paper_initialization(self):
        """Test Paper object creation."""
        paper = Paper(pmcid=12345)
        assert paper.pmcid == 12345
        assert paper.title is None
        assert paper.authors is None
        assert paper.abstract is None
        assert paper.body is None

    def test_paper_from_pmc_with_mock(self, monkeypatch):
        """Test Paper.from_pmc with mocked dependencies."""
        def mock_paper_dict_from_pmc(*args, **kwargs):
            return {
                "PMCID": 12345,
                "Title": "Test Title",
                "Authors": pd.DataFrame([{"First_Name": "John", "Last_Name": "Doe"}]),
                "Abstract": [],
                "Body": [],
                "Journal Title": "Test Journal",
                "Published Date": {"epub": "2024-01-01"},
                "Volume": "1",
                "Issue": "1",
            }
        
        from pmcgrab import parser
        monkeypatch.setattr(parser, "paper_dict_from_pmc", mock_paper_dict_from_pmc)
        
        paper = Paper.from_pmc(12345, "test@example.com")
        assert paper.pmcid == 12345
        assert paper.title == "Test Title"
        assert paper.journal_title == "Test Journal"

    def test_paper_has_data_property(self):
        """Test the has_data property."""
        paper = Paper(pmcid=12345)
        assert not paper.has_data  # No data initially
        
        paper.title = "Test Title"
        assert paper.has_data  # Has title now


class TestTextSection:
    """Test the TextSection class."""

    def test_text_section_creation(self):
        """Test TextSection creation from XML."""
        xml = """<sec>
            <title>Introduction</title>
            <p>This is a paragraph.</p>
        </sec>"""
        element = ET.fromstring(xml)
        ref_map = BasicBiMap()
        
        section = TextSection(element, ref_map=ref_map)
        assert section.title == "Introduction"
        assert len(section.content) > 0

    def test_text_section_without_title(self):
        """Test TextSection without title."""
        xml = """<sec>
            <p>This is a paragraph without title.</p>
        </sec>"""
        element = ET.fromstring(xml)
        ref_map = BasicBiMap()
        
        section = TextSection(element, ref_map=ref_map)
        assert section.title is None

    def test_text_section_str_representation(self):
        """Test string representation of TextSection."""
        xml = """<sec>
            <title>Test</title>
            <p>Content</p>
        </sec>"""
        element = ET.fromstring(xml)
        ref_map = BasicBiMap()
        
        section = TextSection(element, ref_map=ref_map)
        str_repr = str(section)
        assert "Test" in str_repr
        assert "Content" in str_repr


class TestTextParagraph:
    """Test the TextParagraph class."""

    def test_text_paragraph_creation(self):
        """Test TextParagraph creation."""
        xml = """<p>This is a simple paragraph.</p>"""
        element = ET.fromstring(xml)
        ref_map = BasicBiMap()
        
        paragraph = TextParagraph(element, ref_map=ref_map)
        assert "simple paragraph" in str(paragraph)

    def test_text_paragraph_with_references(self):
        """Test TextParagraph with citation references."""
        xml = """<p>This has a <xref ref-type="bibr" rid="ref1">citation</xref>.</p>"""
        element = ET.fromstring(xml)
        ref_map = BasicBiMap()
        
        paragraph = TextParagraph(element, ref_map=ref_map)
        # Should handle the reference gracefully
        assert isinstance(str(paragraph), str)


class TestTextTable:
    """Test the TextTable class."""

    def test_text_table_creation(self):
        """Test TextTable creation."""
        xml = """<table-wrap id="table1">
            <label>Table 1</label>
            <caption><p>Test table caption</p></caption>
            <table>
                <thead>
                    <tr><th>Header 1</th><th>Header 2</th></tr>
                </thead>
                <tbody>
                    <tr><td>Data 1</td><td>Data 2</td></tr>
                </tbody>
            </table>
        </table-wrap>"""
        element = ET.fromstring(xml)
        
        table = TextTable(element)
        assert table.label == "Table 1"
        assert "Test table caption" in table.caption
        assert isinstance(table.df, pd.DataFrame)

    def test_text_table_without_caption(self):
        """Test TextTable without caption."""
        xml = """<table-wrap id="table1">
            <table>
                <tbody>
                    <tr><td>Data</td></tr>
                </tbody>
            </table>
        </table-wrap>"""
        element = ET.fromstring(xml)
        
        table = TextTable(element)
        assert table.caption == ""


class TestTextFigure:
    """Test the TextFigure class."""

    def test_text_figure_creation(self):
        """Test TextFigure creation."""
        xml = """<fig id="fig1">
            <label>Figure 1</label>
            <caption><p>Test figure caption</p></caption>
            <graphic xlink:href="figure1.jpg" xmlns:xlink="http://www.w3.org/1999/xlink"/>
        </fig>"""
        element = ET.fromstring(xml)
        
        figure = TextFigure(element)
        assert figure.label == "Figure 1"
        assert "Test figure caption" in figure.caption

    def test_text_figure_fig_dict_property(self):
        """Test fig_dict property."""
        xml = """<fig id="fig1">
            <label>Figure 1</label>
            <caption><p>Caption text</p></caption>
        </fig>"""
        element = ET.fromstring(xml)
        
        figure = TextFigure(element)
        fig_dict = figure.fig_dict
        assert isinstance(fig_dict, dict)
        assert fig_dict["Label"] == "Figure 1"
        assert "Caption text" in fig_dict["Caption"]

    def test_text_figure_without_label(self):
        """Test TextFigure without label."""
        xml = """<fig id="fig1">
            <caption><p>Caption only</p></caption>
        </fig>"""
        element = ET.fromstring(xml)
        
        figure = TextFigure(element)
        assert figure.label == ""