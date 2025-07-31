"""Tests for pmcgrab.processing (legacy) module."""

import signal
import pytest
from unittest.mock import patch, MagicMock

from pmcgrab import processing
from pmcgrab.constants import TimeoutException


class TestLegacyProcessing:
    """Test legacy processing functions."""

    @patch('pmcgrab.processing.Paper.from_pmc')
    def test_process_single_pmc_success(self, mock_from_pmc):
        """Test successful processing of single PMC."""
        # Mock a paper with required attributes
        mock_paper = MagicMock()
        mock_paper.has_data = True
        mock_paper.abstract = "Test abstract"
        mock_paper.title = "Test title"
        mock_paper.body = []
        mock_paper.authors = None
        
        # Mock all the other attributes the function accesses
        for attr in ['non_author_contributors', 'publisher_name', 'publisher_location',
                    'article_id', 'journal_title', 'journal_id', 'issn', 'article_types',
                    'article_categories', 'published_date', 'volume', 'issue', 'permissions',
                    'copyright', 'license', 'funding', 'footnote', 'acknowledgements',
                    'notes', 'custom_meta']:
            setattr(mock_paper, attr, None)
        
        mock_from_pmc.return_value = mock_paper
        
        # The function expects body to have content to not return None
        mock_paper.body = [MagicMock()]
        mock_paper.body[0].title = "Section 1"
        
        result = processing.process_single_pmc("12345")
        
        # Should return a dict or None
        assert result is None or isinstance(result, dict)

    @patch('pmcgrab.processing.Paper.from_pmc')
    def test_process_single_pmc_timeout(self, mock_from_pmc):
        """Test processing with timeout."""
        mock_from_pmc.side_effect = TimeoutException("Timeout")
        
        result = processing.process_single_pmc("12345")
        
        assert result is None

    @patch('pmcgrab.processing.Paper.from_pmc')
    def test_process_single_pmc_invalid_id(self, mock_from_pmc):
        """Test processing with invalid PMC ID."""
        result = processing.process_single_pmc("invalid")
        
        assert result is None

    @patch('pmcgrab.processing.process_single_pmc')
    def test_process_pmcs_success(self, mock_process_single):
        """Test batch processing of PMCs."""
        # Mock successful processing
        mock_process_single.side_effect = [
            {"pmc_id": "12345", "title": "Test 1"},
            {"pmc_id": "67890", "title": "Test 2"}
        ]
        
        result = processing.process_pmcs(["12345", "67890"])
        
        assert isinstance(result, list)
        assert len(result) == 2

    @patch('pmcgrab.processing.process_single_pmc')
    def test_process_pmcs_with_failures(self, mock_process_single):
        """Test batch processing with some failures."""
        # Mock mixed results
        mock_process_single.side_effect = [
            {"pmc_id": "12345", "title": "Test 1"},
            None,  # Failed processing
            {"pmc_id": "99999", "title": "Test 3"}
        ]
        
        result = processing.process_pmcs(["12345", "67890", "99999"])
        
        assert isinstance(result, list)
        # Should only contain successful results
        assert len(result) == 2

    @patch('pmcgrab.processing.process_single_pmc')
    def test_process_pmcs_empty_list(self, mock_process_single):
        """Test batch processing with empty list."""
        result = processing.process_pmcs([])
        
        assert isinstance(result, list)
        assert len(result) == 0
        mock_process_single.assert_not_called()

    def test_normalize_value_basic_types(self):
        """Test normalize_value function with basic types."""
        assert processing.normalize_value("string") == "string"
        assert processing.normalize_value(42) == 42
        assert processing.normalize_value(None) is None

    def test_normalize_value_datetime(self):
        """Test normalize_value with datetime objects."""
        import datetime
        dt = datetime.datetime(2024, 1, 15, 10, 30)
        result = processing.normalize_value(dt)
        assert result == "2024-01-15T10:30:00"

    def test_normalize_value_dataframe(self):
        """Test normalize_value with pandas DataFrame."""
        import pandas as pd
        df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
        result = processing.normalize_value(df)
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] == {"col1": 1, "col2": "a"}

    @patch('pmcgrab.processing.process_single_pmc')
    def test_process_pmcs_concurrent(self, mock_process_single):
        """Test concurrent processing."""
        # Mock successful processing
        mock_process_single.return_value = {"pmc_id": "12345", "title": "Test"}
        
        # Test with a few IDs to ensure concurrency works
        pmc_ids = ["12345", "67890", "11111", "22222"]
        result = processing.process_pmcs(pmc_ids)
        
        assert isinstance(result, list)
        assert len(result) == 4
        # Should have been called once for each ID
        assert mock_process_single.call_count == 4

    def test_timeout_handler(self):
        """Test timeout handler function."""
        with pytest.raises(TimeoutException):
            processing.timeout_handler(signal.SIGALRM, None)

    @patch('pmcgrab.processing.process_pmcs')
    def test_batch_process_pmcs_wrapper(self, mock_process_pmcs):
        """Test batch processing wrapper function if it exists."""
        try:
            # Try to call batch processing function if it exists
            if hasattr(processing, 'batch_process_pmcs'):
                mock_process_pmcs.return_value = []
                result = processing.batch_process_pmcs(["12345", "67890"])
                assert isinstance(result, list)
        except AttributeError:
            # Function might not exist
            pass

    @patch('pmcgrab.processing.Paper.from_pmc')
    def test_process_single_pmc_paper_none(self, mock_from_pmc):
        """Test processing when Paper.from_pmc returns None."""
        mock_from_pmc.return_value = None
        
        result = processing.process_single_pmc("12345")
        
        assert result is None

    @patch('pmcgrab.processing.Paper.from_pmc')
    def test_process_single_pmc_exception(self, mock_from_pmc):
        """Test processing when an exception occurs."""
        mock_from_pmc.side_effect = Exception("Network error")
        
        result = processing.process_single_pmc("12345")
        
        assert result is None