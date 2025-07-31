"""Tests for pmcgrab.domain.value_objects module."""

import warnings

from pmcgrab.constants import ReversedBiMapComparisonWarning
from pmcgrab.domain.value_objects import BasicBiMap, make_hashable


class TestMakeHashable:
    """Test the make_hashable function."""

    def test_make_hashable_dict(self):
        """Test make_hashable with dict input."""
        test_dict = {"b": 2, "a": 1}
        result = make_hashable(test_dict)
        expected = (("a", 1), ("b", 2))
        assert result == expected

    def test_make_hashable_list(self):
        """Test make_hashable with list input."""
        test_list = [3, 1, 2]
        result = make_hashable(test_list)
        expected = (3, 1, 2)
        assert result == expected

    def test_make_hashable_nested(self):
        """Test make_hashable with nested structures."""
        test_nested = {"a": [1, 2], "b": {"c": 3}}
        result = make_hashable(test_nested)
        expected = (("a", (1, 2)), ("b", (("c", 3),)))
        assert result == expected

    def test_make_hashable_primitive(self):
        """Test make_hashable with primitive types."""
        assert make_hashable(42) == 42
        assert make_hashable("hello") == "hello"
        assert make_hashable(None) is None


class TestBasicBiMap:
    """Test the BasicBiMap class."""

    def test_basic_bimap_creation(self):
        """Test BasicBiMap creation."""
        bm = BasicBiMap()
        assert len(bm) == 0
        assert len(bm.reverse) == 0

    def test_basic_bimap_initialization_with_data(self):
        """Test BasicBiMap initialization with data."""
        data = {"a": 1, "b": 2}
        bm = BasicBiMap(data)
        assert bm["a"] == 1
        assert bm["b"] == 2
        assert bm.reverse[1] == "a"
        assert bm.reverse[2] == "b"

    def test_basic_bimap_setitem(self):
        """Test BasicBiMap __setitem__ method."""
        bm = BasicBiMap()
        bm["key"] = "value"
        assert bm["key"] == "value"
        assert bm.reverse["value"] == "key"

    def test_basic_bimap_setitem_complex_value(self):
        """Test BasicBiMap with complex values."""
        bm = BasicBiMap()
        bm["key"] = {"nested": "dict"}
        assert bm["key"] == {"nested": "dict"}
        # Complex values are made hashable for reverse lookup
        hashable_value = make_hashable({"nested": "dict"})
        assert bm.reverse[hashable_value] == "key"

    def test_basic_bimap_equality(self):
        """Test BasicBiMap equality comparison."""
        bm1 = BasicBiMap({"a": 1, "b": 2})
        bm2 = BasicBiMap({"a": 1, "b": 2})
        regular_dict = {"a": 1, "b": 2}

        assert bm1 == bm2
        assert bm1 == regular_dict

    def test_basic_bimap_inequality(self):
        """Test BasicBiMap inequality."""
        bm1 = BasicBiMap({"a": 1})
        bm2 = BasicBiMap({"a": 2})

        assert bm1 != bm2
        assert bm1 != "not a dict"

    def test_basic_bimap_reverse_comparison_warning(self):
        """Test BasicBiMap reverse comparison warning."""
        bm1 = BasicBiMap({"a": 1, "b": 2})
        bm2 = BasicBiMap({1: "a", 2: "b"})  # Reversed mapping

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = bm1 == bm2

            # Should warn about reversed comparison
            assert len(w) == 1
            assert issubclass(w[0].category, ReversedBiMapComparisonWarning)
            assert result is True

    def test_basic_bimap_dict_methods(self):
        """Test that BasicBiMap inherits dict methods."""
        bm = BasicBiMap({"a": 1, "b": 2, "c": 3})

        # Test keys, values, items
        assert set(bm.keys()) == {"a", "b", "c"}
        assert set(bm.values()) == {1, 2, 3}
        assert set(bm.items()) == {("a", 1), ("b", 2), ("c", 3)}

        # Test get method
        assert bm.get("a") == 1
        assert bm.get("d", "default") == "default"

        # Test len
        assert len(bm) == 3

    def test_basic_bimap_update_reverse_on_modification(self):
        """Test that reverse map updates when forward map is modified."""
        bm = BasicBiMap()
        bm["first"] = "value1"
        bm["second"] = "value2"

        # Update existing key
        bm["first"] = "updated_value"

        assert bm["first"] == "updated_value"
        assert bm.reverse["updated_value"] == "first"
        # Old reverse mapping should be replaced
        assert "value1" not in bm.reverse

    def test_basic_bimap_with_duplicate_values(self):
        """Test BasicBiMap behavior with duplicate values."""
        bm = BasicBiMap()
        bm["key1"] = "same_value"
        bm["key2"] = "same_value"  # This will overwrite reverse mapping

        assert bm["key1"] == "same_value"
        assert bm["key2"] == "same_value"
        # Reverse map will point to the last key that had this value
        assert bm.reverse["same_value"] == "key2"
