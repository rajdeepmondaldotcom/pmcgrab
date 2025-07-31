"""Tests for pmcgrab.utils module."""

import datetime
import warnings

import lxml.etree as ET
import pandas as pd

from pmcgrab.common.serialization import normalize_value
from pmcgrab.common.xml_processing import (
    generate_typed_mhtml_tag,
    remove_mhtml_tags,
    split_text_and_refs,
    stringify_children,
)
from pmcgrab.domain.value_objects import BasicBiMap


class TestUtilsFunctions:
    """Test utility functions."""

    def test_normalize_value_basic_types(self):
        """Test normalize_value with basic types."""
        assert normalize_value("string") == "string"
        assert normalize_value(42) == 42
        assert normalize_value(3.14) == 3.14
        assert normalize_value(True) is True
        assert normalize_value(None) is None

    def test_normalize_value_datetime(self):
        """Test normalize_value with datetime objects."""
        dt = datetime.datetime(2024, 1, 15, 10, 30, 45)
        result = normalize_value(dt)
        assert result == "2024-01-15T10:30:45"

    def test_normalize_value_date(self):
        """Test normalize_value with date objects."""
        date = datetime.date(2024, 1, 15)
        result = normalize_value(date)
        assert result == "2024-01-15"

    def test_normalize_value_dataframe(self):
        """Test normalize_value with pandas DataFrame."""
        df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
        result = normalize_value(df)

        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0] == {"col1": 1, "col2": "a"}
        assert result[1] == {"col1": 2, "col2": "b"}
        assert result[2] == {"col1": 3, "col2": "c"}

    def test_normalize_value_dict(self):
        """Test normalize_value with dictionary."""
        test_dict = {
            "string": "value",
            "number": 42,
            "date": datetime.date(2024, 1, 15),
            "nested": {"inner": "value"},
        }
        result = normalize_value(test_dict)

        assert result["string"] == "value"
        assert result["number"] == 42
        assert result["date"] == "2024-01-15"
        assert result["nested"]["inner"] == "value"

    def test_normalize_value_list(self):
        """Test normalize_value with list."""
        test_list = ["string", 42, datetime.date(2024, 1, 15), {"key": "value"}]
        result = normalize_value(test_list)

        assert result[0] == "string"
        assert result[1] == 42
        assert result[2] == "2024-01-15"
        assert result[3] == {"key": "value"}

    def test_stringify_children_simple(self):
        """Test stringify_children with simple XML."""
        xml = "<parent>Text <child>content</child> more text</parent>"
        element = ET.fromstring(xml)
        result = stringify_children(element)

        assert "Text" in result
        assert "content" in result
        assert "more text" in result

    def test_stringify_children_nested(self):
        """Test stringify_children with nested XML."""
        xml = "<parent><child1>First</child1><child2>Second <nested>nested</nested></child2></parent>"
        element = ET.fromstring(xml)
        result = stringify_children(element)

        assert "First" in result
        assert "Second" in result
        assert "nested" in result

    def test_stringify_children_empty(self):
        """Test stringify_children with empty element."""
        xml = "<parent></parent>"
        element = ET.fromstring(xml)
        result = stringify_children(element)

        assert result == ""

    def test_split_text_and_refs_no_refs(self):
        """Test split_text_and_refs without references."""
        xml_text = "<p>Simple text without references</p>"
        ref_map = BasicBiMap()

        result = split_text_and_refs(xml_text, ref_map)
        assert "Simple text without references" in result

    def test_split_text_and_refs_with_refs(self):
        """Test split_text_and_refs with references."""
        xml_text = '<p>Text with <xref ref-type="bibr" rid="ref1">citation</xref> reference</p>'
        ref_map = BasicBiMap()

        result = split_text_and_refs(xml_text, ref_map)
        assert "Text with" in result
        assert "reference" in result
        # Should handle the reference appropriately
        assert isinstance(result, str)

    def test_generate_typed_mhtml_tag(self):
        """Test generate_typed_mhtml_tag function."""
        result = generate_typed_mhtml_tag("citation", 1)
        assert "citation" in result.lower()
        assert "1" in result

    def test_generate_typed_mhtml_tag_different_types(self):
        """Test generate_typed_mhtml_tag with different types."""
        citation_tag = generate_typed_mhtml_tag("citation", 1)
        table_tag = generate_typed_mhtml_tag("table", 2)
        figure_tag = generate_typed_mhtml_tag("figure", 3)

        assert citation_tag != table_tag
        assert table_tag != figure_tag
        assert "1" in citation_tag
        assert "2" in table_tag
        assert "3" in figure_tag

    def test_remove_mhtml_tags_basic(self):
        """Test remove_mhtml_tags with basic tags."""
        citation_tag = generate_typed_mhtml_tag("citation", 1)
        table_tag = generate_typed_mhtml_tag("table", 2)
        text = f"Text with {citation_tag} and {table_tag} references"
        result = remove_mhtml_tags(text)

        assert citation_tag not in result
        assert table_tag not in result
        assert "Text with" in result
        assert "references" in result

    def test_remove_mhtml_tags_multiple_same_type(self):
        """Test remove_mhtml_tags with multiple tags of same type."""
        citation1 = generate_typed_mhtml_tag("citation", 1)
        citation2 = generate_typed_mhtml_tag("citation", 2)
        text = f"Multiple {citation1} and {citation2} citations"
        result = remove_mhtml_tags(text)

        assert citation1 not in result
        assert citation2 not in result
        assert "Multiple" in result
        assert "citations" in result

    def test_remove_mhtml_tags_no_tags(self):
        """Test remove_mhtml_tags with no MHTML tags."""
        text = "Plain text without any special tags"
        result = remove_mhtml_tags(text)

        assert result == text

    def test_remove_mhtml_tags_empty_string(self):
        """Test remove_mhtml_tags with empty string."""
        result = remove_mhtml_tags("")
        assert result == ""

    def test_remove_mhtml_tags_mixed_content(self):
        """Test remove_mhtml_tags with mixed content."""
        citation1 = generate_typed_mhtml_tag("citation", 1)
        citation2 = generate_typed_mhtml_tag("citation", 2)
        table1 = generate_typed_mhtml_tag("table", 1)
        figure1 = generate_typed_mhtml_tag("figure", 1)

        text = f"Study {citation1} shows results in {table1} and {figure1} demonstrates {citation2} findings."
        result = remove_mhtml_tags(text)

        # All MHTML tags should be removed
        assert citation1 not in result
        assert citation2 not in result
        assert table1 not in result
        assert figure1 not in result

        # Regular text should remain
        assert "Study" in result
        assert "shows results" in result
        assert "demonstrates" in result
        assert "findings" in result


class TestBasicBiMapInUtils:
    """Test BasicBiMap functionality in utils context."""

    def test_basic_bimap_creation(self):
        """Test creating BasicBiMap."""
        bm = BasicBiMap()
        assert len(bm) == 0
        assert hasattr(bm, "reverse")

    def test_basic_bimap_with_data(self):
        """Test BasicBiMap with initial data."""
        data = {"key1": "value1", "key2": "value2"}
        bm = BasicBiMap(data)

        assert bm["key1"] == "value1"
        assert bm["key2"] == "value2"
        assert bm.reverse["value1"] == "key1"
        assert bm.reverse["value2"] == "key2"

    def test_basic_bimap_assignment(self):
        """Test BasicBiMap assignment."""
        bm = BasicBiMap()
        bm["test_key"] = "test_value"

        assert bm["test_key"] == "test_value"
        assert bm.reverse["test_value"] == "test_key"

    def test_basic_bimap_complex_values(self):
        """Test BasicBiMap with complex values."""
        bm = BasicBiMap()
        complex_value = {"nested": {"data": [1, 2, 3]}}
        bm["complex"] = complex_value

        assert bm["complex"] == complex_value
        # Complex values should be handled in reverse mapping
        assert len(bm.reverse) == 1

    def test_basic_bimap_equality(self):
        """Test BasicBiMap equality."""
        bm1 = BasicBiMap({"a": 1, "b": 2})
        bm2 = BasicBiMap({"a": 1, "b": 2})
        regular_dict = {"a": 1, "b": 2}

        assert bm1 == bm2
        assert bm1 == regular_dict

    def test_basic_bimap_reverse_warning(self):
        """Test BasicBiMap reverse comparison warning."""
        bm1 = BasicBiMap({"a": 1, "b": 2})
        bm2 = BasicBiMap({1: "a", 2: "b"})  # Reversed

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = bm1 == bm2

            # Should issue warning about reverse comparison
            assert len(w) >= 1
            # Should still return True due to reverse comparison logic
            assert result is True
