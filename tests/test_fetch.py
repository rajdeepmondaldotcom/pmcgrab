"""Tests for pmcgrab.fetch module."""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
import lxml.etree as ET
from urllib.error import HTTPError

from pmcgrab.fetch import (
    get_xml,
    fetch_pmc_xml_string,
    clean_xml_string,
    xml_tree_from_string,
    validate_xml,
)


class TestFetchPmcXmlString:
    """Test fetch_pmc_xml_string function."""

    @patch('pmcgrab.fetch.Entrez.efetch')
    def test_fetch_pmc_xml_string_success(self, mock_efetch):
        """Test successful XML string retrieval from PMC."""
        xml_content = """<?xml version="1.0"?>
        <pmc-articleset><article><title>Test</title></article></pmc-articleset>"""
        
        mock_handle = MagicMock()
        mock_handle.read.return_value = xml_content
        mock_efetch.return_value = mock_handle
        
        result = fetch_pmc_xml_string(12345, "test@example.com")
        
        assert isinstance(result, str)
        assert "Test" in result

    @patch('pmcgrab.fetch.Entrez.efetch')
    @patch('pmcgrab.fetch.os.path.exists')
    def test_fetch_pmc_xml_string_with_cache(self, mock_exists, mock_efetch):
        """Test fetching with caching enabled."""
        xml_content = """<?xml version="1.0"?><pmc-articleset><article><title>Cached</title></article></pmc-articleset>"""
        
        # Mock cache file exists
        mock_exists.return_value = True
        
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = xml_content
            
            result = fetch_pmc_xml_string(12345, "test@example.com", download=True)
            
            assert "Cached" in result
            # Should not call efetch when using cache
            mock_efetch.assert_not_called()


class TestCleanXmlString:
    """Test clean_xml_string function."""

    def test_clean_xml_string_basic(self):
        """Test basic XML string cleaning."""
        dirty_xml = "<root>  Text with   extra spaces  </root>"
        result = clean_xml_string(dirty_xml)
        
        assert isinstance(result, str)
        # Should clean up extra whitespace
        assert "extra spaces" in result

    def test_clean_xml_string_with_html(self):
        """Test XML string cleaning with HTML elements."""
        xml_with_html = "<root><p>Text with <b>bold</b> content</p></root>"
        result = clean_xml_string(xml_with_html)
        
        assert isinstance(result, str)
        assert "bold" in result


class TestXmlTreeFromString:
    """Test xml_tree_from_string function."""

    def test_xml_tree_from_string_valid(self):
        """Test creating XML tree from valid string."""
        xml_string = """<?xml version="1.0"?>
        <pmc-articleset>
            <article>
                <title>Test Article</title>
            </article>
        </pmc-articleset>"""
        
        result = xml_tree_from_string(xml_string)
        
        assert isinstance(result, ET._ElementTree)
        root = result.getroot()
        assert root.tag == "pmc-articleset"

    def test_xml_tree_from_string_invalid(self):
        """Test creating XML tree from invalid string."""
        invalid_xml = "<root><unclosed>content</root>"
        
        with pytest.raises(ET.XMLSyntaxError):
            xml_tree_from_string(invalid_xml)

    def test_xml_tree_from_string_empty(self):
        """Test creating XML tree from empty string."""
        with pytest.raises(ET.XMLSyntaxError):
            xml_tree_from_string("")


class TestValidateXml:
    """Test validate_xml function."""

    def test_validate_xml_valid_tree(self):
        """Test validation with valid XML tree."""
        xml_string = """<?xml version="1.0"?>
        <pmc-articleset>
            <article>
                <title>Valid Article</title>
            </article>
        </pmc-articleset>"""
        
        tree = ET.ElementTree(ET.fromstring(xml_string))
        
        # Should not raise an exception
        result = validate_xml(tree)
        assert isinstance(result, bool)

    def test_validate_xml_minimal_tree(self):
        """Test validation with minimal XML tree."""
        xml_string = "<root></root>"
        tree = ET.ElementTree(ET.fromstring(xml_string))
        
        result = validate_xml(tree)
        assert isinstance(result, bool)


class TestGetXml:
    """Test the main get_xml function."""

    @patch('pmcgrab.fetch.fetch_pmc_xml_string')
    @patch('pmcgrab.fetch.clean_xml_string')
    @patch('pmcgrab.fetch.xml_tree_from_string')
    def test_get_xml_success(self, mock_xml_tree, mock_clean, mock_fetch):
        """Test successful XML retrieval and processing."""
        # Mock the pipeline
        raw_xml = "<pmc-articleset><article><title>Test</title></article></pmc-articleset>"
        cleaned_xml = raw_xml  # Assume no cleaning needed
        mock_tree = MagicMock()
        
        mock_fetch.return_value = raw_xml
        mock_clean.return_value = cleaned_xml
        mock_xml_tree.return_value = mock_tree
        
        result = get_xml(12345, "test@example.com")
        
        assert result == mock_tree
        mock_fetch.assert_called_once_with(12345, "test@example.com", download=False, verbose=False)
        mock_clean.assert_called_once_with(raw_xml)
        mock_xml_tree.assert_called_once_with(cleaned_xml)

    @patch('pmcgrab.fetch.fetch_pmc_xml_string')
    @patch('pmcgrab.fetch.validate_xml')
    def test_get_xml_with_validation(self, mock_validate, mock_fetch):
        """Test get_xml with validation enabled."""
        xml_content = "<pmc-articleset><article><title>Test</title></article></pmc-articleset>"
        mock_fetch.return_value = xml_content
        mock_validate.return_value = True
        
        result = get_xml(12345, "test@example.com", validate=True)
        
        assert isinstance(result, ET._ElementTree)
        mock_validate.assert_called_once()

    @patch('pmcgrab.fetch.fetch_pmc_xml_string')
    def test_get_xml_fetch_failure(self, mock_fetch):
        """Test get_xml when fetch fails."""
        mock_fetch.side_effect = HTTPError(
            url="test", code=404, msg="Not Found", hdrs=None, fp=None
        )
        
        with pytest.raises(HTTPError):
            get_xml(12345, "test@example.com")

    @patch('pmcgrab.fetch.fetch_pmc_xml_string')
    def test_get_xml_with_download_and_verbose(self, mock_fetch):
        """Test get_xml with download and verbose options."""
        xml_content = "<pmc-articleset><article><title>Test</title></article></pmc-articleset>"
        mock_fetch.return_value = xml_content
        
        result = get_xml(12345, "test@example.com", download=True, verbose=True)
        
        assert isinstance(result, ET._ElementTree)
        mock_fetch.assert_called_once_with(12345, "test@example.com", download=True, verbose=True)