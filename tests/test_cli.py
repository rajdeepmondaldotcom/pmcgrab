"""Tests for pmcgrab.cli module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pmcgrab.cli.pmcgrab_cli import _parse_args, main


class TestCliArgParsing:
    """Test CLI argument parsing."""

    def test_parse_args_minimal(self):
        """Test parsing minimal required arguments."""
        with patch("sys.argv", ["pmcgrab_cli", "--ids", "12345", "67890"]):
            args = _parse_args()
            assert args.ids == ["12345", "67890"]
            assert args.out == "./pmc_output"
            assert args.workers == 16

    def test_parse_args_all_options(self):
        """Test parsing all CLI options."""
        with patch(
            "sys.argv",
            [
                "pmcgrab_cli",
                "--ids",
                "12345",
                "67890",
                "99999",
                "--out",
                "/custom/output",
                "--workers",
                "8",
            ],
        ):
            args = _parse_args()
            assert args.ids == ["12345", "67890", "99999"]
            assert args.out == "/custom/output"
            assert args.workers == 8

    def test_parse_args_missing_ids(self):
        """Test that missing --ids raises SystemExit."""
        with patch("sys.argv", ["pmcgrab_cli"]):
            with pytest.raises(SystemExit):
                _parse_args()


class TestCliMain:
    """Test the main CLI function."""

    @patch("pmcgrab.cli.pmcgrab_cli.process_pmc_ids")
    @patch("pmcgrab.cli.pmcgrab_cli._parse_args")
    @patch("pmcgrab.cli.pmcgrab_cli.tqdm")
    def test_main_successful_processing(
        self, mock_tqdm, mock_parse_args, mock_process_pmc_ids
    ):
        """Test successful processing of PMC IDs."""
        # Mock arguments
        mock_args = MagicMock()
        mock_args.ids = ["12345", "67890"]
        mock_args.out = "./test_output"
        mock_args.workers = 4
        mock_parse_args.return_value = mock_args

        # Mock tqdm progress bar
        mock_bar = MagicMock()
        mock_tqdm.return_value = mock_bar

        # Mock successful processing
        mock_process_pmc_ids.return_value = {"12345": True, "67890": True}

        with tempfile.TemporaryDirectory() as temp_dir:
            mock_args.out = temp_dir

            # Run main function
            main()

            # Verify process_pmc_ids was called correctly
            mock_process_pmc_ids.assert_called_once_with(["12345", "67890"], workers=4)

            # Verify progress bar was used
            assert mock_bar.update.call_count == 2
            mock_bar.close.assert_called_once()

            # Verify summary file was created
            summary_path = Path(temp_dir) / "summary.json"
            assert summary_path.exists()

            with open(summary_path) as f:
                summary = json.load(f)
                assert summary == {"12345": True, "67890": True}

    @patch("pmcgrab.cli.pmcgrab_cli.process_pmc_ids")
    @patch("pmcgrab.cli.pmcgrab_cli._parse_args")
    @patch("pmcgrab.cli.pmcgrab_cli.tqdm")
    def test_main_with_failures(self, mock_tqdm, mock_parse_args, mock_process_pmc_ids):
        """Test processing with some failures."""
        # Mock arguments
        mock_args = MagicMock()
        mock_args.ids = ["12345", "67890", "99999"]
        mock_args.out = "./test_output"
        mock_args.workers = 2
        mock_parse_args.return_value = mock_args

        # Mock tqdm progress bar
        mock_bar = MagicMock()
        mock_tqdm.return_value = mock_bar

        # Mock mixed results (some success, some failure)
        mock_process_pmc_ids.return_value = {
            "12345": True,
            "67890": False,
            "99999": True,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            mock_args.out = temp_dir

            # Run main function
            main()

            # Verify summary file contains mixed results
            summary_path = Path(temp_dir) / "summary.json"
            assert summary_path.exists()

            with open(summary_path) as f:
                summary = json.load(f)
                assert summary["12345"] is True
                assert summary["67890"] is False
                assert summary["99999"] is True

    @patch("pmcgrab.cli.pmcgrab_cli.process_pmc_ids")
    @patch("pmcgrab.cli.pmcgrab_cli._parse_args")
    @patch("pmcgrab.cli.pmcgrab_cli.tqdm")
    def test_main_large_batch_chunking(
        self, mock_tqdm, mock_parse_args, mock_process_pmc_ids
    ):
        """Test that large batches are processed in chunks of 100."""
        # Create a list of 250 PMC IDs to test chunking
        pmc_ids = [str(i) for i in range(1, 251)]  # 250 IDs

        mock_args = MagicMock()
        mock_args.ids = pmc_ids
        mock_args.out = "./test_output"
        mock_args.workers = 8
        mock_parse_args.return_value = mock_args

        # Mock tqdm progress bar
        mock_bar = MagicMock()
        mock_tqdm.return_value = mock_bar

        # Mock successful processing for all chunks
        def mock_process_chunk(chunk, workers):
            return dict.fromkeys(chunk, True)

        mock_process_pmc_ids.side_effect = mock_process_chunk

        with tempfile.TemporaryDirectory() as temp_dir:
            mock_args.out = temp_dir

            # Run main function
            main()

            # Should be called 3 times (100 + 100 + 50)
            assert mock_process_pmc_ids.call_count == 3

            # Verify chunk sizes
            call_args_list = mock_process_pmc_ids.call_args_list
            assert len(call_args_list[0][0][0]) == 100  # First chunk
            assert len(call_args_list[1][0][0]) == 100  # Second chunk
            assert len(call_args_list[2][0][0]) == 50  # Third chunk

            # Verify all 250 updates were made to progress bar
            assert mock_bar.update.call_count == 250

    @patch("pmcgrab.cli.pmcgrab_cli._parse_args")
    def test_main_creates_output_directory(self, mock_parse_args):
        """Test that main creates the output directory if it doesn't exist."""
        mock_args = MagicMock()
        mock_args.ids = ["12345"]
        mock_args.workers = 1

        with tempfile.TemporaryDirectory() as temp_dir:
            # Set output to a non-existent subdirectory
            output_dir = Path(temp_dir) / "new_subdir" / "output"
            mock_args.out = str(output_dir)
            mock_parse_args.return_value = mock_args

            with patch("pmcgrab.cli.pmcgrab_cli.process_pmc_ids") as mock_process:
                mock_process.return_value = {"12345": True}
                with patch("pmcgrab.cli.pmcgrab_cli.tqdm"):
                    main()

            # Verify directory was created
            assert output_dir.exists()
            assert output_dir.is_dir()

            # Verify summary file was created in the new directory
            summary_path = output_dir / "summary.json"
            assert summary_path.exists()
