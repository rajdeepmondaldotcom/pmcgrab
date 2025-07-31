"""Tests for pmcgrab.common utilities."""

import datetime
import pandas as pd
import pytest
import lxml.etree as ET

from pmcgrab.common.html_cleaning import remove_html_tags, strip_html_text_styling
from pmcgrab.common.serialization import clean_doc, normalize_value
from pmcgrab.common.xml_processing import (
    stringify_children,
    split_text_and_refs,
    generate_typed_mhtml_tag,
    remove_mhtml_tags,
)


class TestHtmlCleaning:
    """Test HTML cleaning utilities."""

    def test_remove_html_tags_simple(self):
        """Test removing simple HTML tags."""
        html = "<p>Hello <b>world</b></p>"
        result = remove_html_tags(html)
        assert result == "Hello world"

    def test_remove_html_tags_with_attributes(self):
        """Test removing tags with attributes."""
        html = '<div class="test">Content</div>'
        result = remove_html_tags(html)
        assert result == "Content"

    def test_remove_html_tags_nested(self):
        """Test removing nested tags."""
        html = "<div><p>Nested <span>content</span></p></div>"
        result = remove_html_tags(html)
        assert result == "Nested content"

    def test_remove_html_tags_empty_string(self):
        """Test with empty string."""
        result = remove_html_tags("")
        assert result == ""

    def test_remove_html_tags_no_tags(self):
        """Test with string containing no tags."""
        text = "Plain text with no tags"
        result = remove_html_tags(text)
        assert result == text

    def test_strip_html_text_styling_basic(self):
        """Test stripping basic HTML styling."""
        html = "Text with <i>italic</i> and <b>bold</b>"
        result = strip_html_text_styling(html)
        assert result == "Text with italic and bold"

    def test_strip_html_text_styling_with_replacement(self):
        """Test stripping with custom replacements."""
        html = "List: <li>Item 1</li><li>Item 2</li>"
        result = strip_html_text_styling(html, {"li": "• "})
        assert result == "List: • Item 1• Item 2"

    def test_strip_html_text_styling_complex(self):
        """Test with more complex HTML."""
        html = "<p>Paragraph with <sup>superscript</sup> and <sub>subscript</sub></p>"
        result = strip_html_text_styling(html)
        assert "superscript" in result
        assert "subscript" in result


class TestSerialization:
    """Test serialization utilities."""

    def test_clean_doc_basic(self):
        """Test basic document cleaning."""
        doc = """
        This is a test
        document with extra
        whitespace.
        """
        result = clean_doc(doc)
        assert "\n" not in result
        assert "test document" in result

    def test_clean_doc_empty(self):
        """Test with empty string."""
        result = clean_doc("")
        assert result == ""

    def test_normalize_value_string(self):
        """Test normalizing string values."""
        result = normalize_value("test string")
        assert result == "test string"

    def test_normalize_value_datetime(self):
        """Test normalizing datetime objects."""
        dt = datetime.datetime(2024, 1, 15, 10, 30, 45)
        result = normalize_value(dt)
        assert result == "2024-01-15T10:30:45"

    def test_normalize_value_date(self):
        """Test normalizing date objects."""
        date = datetime.date(2024, 1, 15)
        result = normalize_value(date)
        assert result == "2024-01-15"

    def test_normalize_value_dataframe(self):
        """Test normalizing pandas DataFrame."""
        df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
        result = normalize_value(df)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] == {"col1": 1, "col2": "a"}

    def test_normalize_value_dict(self):
        """Test normalizing dictionary with nested values."""
        data = {
            "date": datetime.date(2024, 1, 15),
            "nested": {"value": "test"}
        }
        result = normalize_value(data)
        assert result["date"] == "2024-01-15"
        assert result["nested"]["value"] == "test"

    def test_normalize_value_list(self):
        """Test normalizing list with mixed types."""
        data = [
            "string",
            datetime.date(2024, 1, 15),
            {"key": "value"}
        ]
        result = normalize_value(data)
        assert result[0] == "string"
        assert result[1] == "2024-01-15"
        assert result[2] == {"key": "value"}

    def test_normalize_value_none(self):
        """Test normalizing None values."""
        result = normalize_value(None)
        assert result is None


class TestXmlProcessing:
    """Test XML processing utilities."""

    def test_stringify_children_simple(self):
        """Test stringifying simple XML children."""
        xml = "<parent>Text <child>content</child> more text</parent>"
        element = ET.fromstring(xml)
        result = stringify_children(element)
        assert "Text" in result
        assert "content" in result
        assert "more text" in result

    def test_stringify_children_empty(self):
        """Test with element having no children."""
        xml = "<parent>Just text</parent>"
        element = ET.fromstring(xml)
        result = stringify_children(element)
        assert result == "Just text"

    def test_split_text_and_refs_no_refs(self):
        """Test splitting text without references."""
        xml = "<p>Simple text without references</p>"
        element = ET.fromstring(xml)
        from pmcgrab.utils import BasicBiMap
        ref_map = BasicBiMap()
        
        result = split_text_and_refs(element, ref_map)
        assert "Simple text" in result

    def test_split_text_and_refs_with_refs(self):
        """Test splitting text with references."""
        xml = '<p>Text with <xref ref-type="bibr" rid="ref1">citation</xref></p>'
        element = ET.fromstring(xml)
        from pmcgrab.utils import BasicBiMap
        ref_map = BasicBiMap()
        
        result = split_text_and_refs(element, ref_map)
        assert "Text with" in result
        # Should handle reference appropriately
        assert isinstance(result, str)

    def test_generate_typed_mhtml_tag(self):
        """Test generating typed MHTML tags."""
        result = generate_typed_mhtml_tag("citation", 1)
        assert "citation" in result
        assert "1" in result

    def test_remove_mhtml_tags(self):
        """Test removing MHTML tags."""
        text = "Text with [CITATION:1] and [TABLE:2] references"
        result = remove_mhtml_tags(text)
        # Should remove the MHTML tags
        assert "[CITATION:1]" not in result
        assert "[TABLE:2]" not in result
        assert "Text with" in result

    def test_remove_mhtml_tags_no_tags(self):
        """Test removing MHTML tags from text without tags."""
        text = "Plain text without MHTML tags"
        result = remove_mhtml_tags(text)
        assert result == text

    def test_remove_mhtml_tags_empty(self):
        """Test removing MHTML tags from empty string."""
        result = remove_mhtml_tags("")
        assert result == ""