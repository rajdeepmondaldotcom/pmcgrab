"""Tests for pmcgrab.figure module."""

import lxml.etree as ET

from pmcgrab.figure import TextFigure


class TestTextFigure:
    """Test TextFigure class."""

    def test_text_figure_creation_basic(self):
        """Test basic TextFigure creation."""
        xml = """<fig id="fig1">
            <label>Figure 1</label>
            <caption><p>Test figure caption</p></caption>
        </fig>"""
        element = ET.fromstring(xml)

        figure = TextFigure(element)

        assert figure.fig_dict["Label"] == "Figure 1"
        assert "Test figure caption" in figure.fig_dict["Caption"]

    def test_text_figure_without_label(self):
        """Test TextFigure without label."""
        xml = """<fig id="fig1">
            <caption><p>Caption without label</p></caption>
        </fig>"""
        element = ET.fromstring(xml)

        figure = TextFigure(element)

        assert figure.fig_dict["Label"] is None
        assert "Caption without label" in figure.fig_dict["Caption"]

    def test_text_figure_without_caption(self):
        """Test TextFigure without caption."""
        xml = """<fig id="fig1">
            <label>Figure 1</label>
        </fig>"""
        element = ET.fromstring(xml)

        figure = TextFigure(element)

        assert figure.fig_dict["Label"] == "Figure 1"
        assert figure.fig_dict["Caption"] is None

    def test_text_figure_without_id(self):
        """Test TextFigure without ID."""
        xml = """<fig>
            <label>Figure 1</label>
            <caption><p>Test caption</p></caption>
        </fig>"""
        element = ET.fromstring(xml)

        figure = TextFigure(element)

        # TextFigure doesn't store figure ID separately, just test it was created
        assert isinstance(figure, TextFigure)

    def test_text_figure_with_graphic(self):
        """Test TextFigure with graphic element."""
        xml = """<fig id="fig1" xmlns:xlink="http://www.w3.org/1999/xlink">
            <label>Figure 1</label>
            <caption><p>Figure with graphic</p></caption>
            <graphic xlink:href="figure1.jpg"/>
        </fig>"""
        element = ET.fromstring(xml)

        figure = TextFigure(element)

        assert figure.fig_dict["Label"] == "Figure 1"
        assert "Figure with graphic" in figure.fig_dict["Caption"]
        assert figure.fig_dict["Link"] == "figure1.jpg"

    def test_text_figure_complex_caption(self):
        """Test TextFigure with complex caption."""
        xml = """<fig id="fig1">
            <label>Figure 1</label>
            <caption>
                <title>Complex Caption</title>
                <p>First paragraph of caption.</p>
                <p>Second paragraph with <italic>italic</italic> text.</p>
            </caption>
        </fig>"""
        element = ET.fromstring(xml)

        figure = TextFigure(element)

        assert figure.fig_dict["Label"] == "Figure 1"
        assert "Complex Caption" in figure.fig_dict["Caption"]
        assert "First paragraph" in figure.fig_dict["Caption"]
        assert "Second paragraph" in figure.fig_dict["Caption"]

    def test_text_figure_fig_dict_property(self):
        """Test fig_dict property."""
        xml = """<fig id="fig1">
            <label>Figure 1</label>
            <caption><p>Test caption</p></caption>
        </fig>"""
        element = ET.fromstring(xml)

        figure = TextFigure(element)
        fig_dict = figure.fig_dict

        assert isinstance(fig_dict, dict)
        assert fig_dict["Label"] == "Figure 1"
        assert "Test caption" in fig_dict["Caption"]
        # TextFigure doesn't store figure ID in fig_dict

    def test_text_figure_fig_dict_empty_values(self):
        """Test fig_dict property with empty values."""
        xml = """<fig></fig>"""
        element = ET.fromstring(xml)

        figure = TextFigure(element)
        fig_dict = figure.fig_dict

        assert isinstance(fig_dict, dict)
        assert fig_dict["Label"] is None
        assert fig_dict["Caption"] is None
        assert fig_dict["Link"] is None

    def test_text_figure_string_representation(self):
        """Test string representation of TextFigure."""
        xml = """<fig id="fig1">
            <label>Figure 1</label>
            <caption><p>Test figure for string representation</p></caption>
        </fig>"""
        element = ET.fromstring(xml)

        figure = TextFigure(element)
        str_repr = str(figure)

        assert isinstance(str_repr, str)
        assert "Figure 1" in str_repr
        assert "Test figure for string representation" in str_repr

    def test_text_figure_minimal(self):
        """Test TextFigure with minimal XML."""
        xml = """<fig></fig>"""
        element = ET.fromstring(xml)

        figure = TextFigure(element)

        assert figure.fig_dict["Label"] is None
        assert figure.fig_dict["Caption"] is None
        assert figure.fig_dict["Link"] is None

        # Should still be able to create fig_dict
        fig_dict = figure.fig_dict
        assert isinstance(fig_dict, dict)

    def test_text_figure_with_nested_elements(self):
        """Test TextFigure with nested elements in caption."""
        xml = """<fig id="fig1">
            <label>Figure 1</label>
            <caption>
                <p>Caption with <bold>bold</bold> and <italic>italic</italic> text.</p>
                <p>Also includes <xref ref-type="bibr" rid="ref1">reference</xref>.</p>
            </caption>
        </fig>"""
        element = ET.fromstring(xml)

        figure = TextFigure(element)

        assert figure.fig_dict["Label"] == "Figure 1"
        # Caption should contain the text content, possibly with formatting removed
        assert "bold" in figure.fig_dict["Caption"]
        assert "italic" in figure.fig_dict["Caption"]
        assert "reference" in figure.fig_dict["Caption"]
