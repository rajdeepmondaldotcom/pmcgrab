"""Comprehensive CLI tests to achieve 100% coverage of pmcgrab_cli.py."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import pmcgrab
from pmcgrab.cli.pmcgrab_cli import main

# Dummy article data returned by process_single_pmc mock
_DUMMY_ARTICLE = {
    "schema_version": 2,
    "has_data": True,
    "identifiers": {
        "pmc_id": "7114487",
        "pmcid": "PMC7114487",
        "pmid": "",
        "doi": "",
        "publisher_id": "",
        "other": {},
    },
    "title": {"main": "Test Article", "subtitle": "", "translated": []},
    "contributors": {
        "authors": [],
        "non_author_contributors": [],
        "author_notes": {},
    },
    "publication": {
        "journal": {"title": "", "alternate_titles": [], "ids": {}, "issn": {}},
        "publisher": {
            "name": "",
            "alternate_names": [],
            "location": "",
            "alternate_locations": [],
        },
        "classification": {"article_types": [], "article_categories": []},
        "dates": {"published": {}, "history": {}, "version_history": []},
        "issue": {
            "volume": "",
            "issue": "",
            "first_page": "",
            "last_page": "",
            "elocation_id": "",
        },
        "conference": {},
    },
    "content": {
        "abstract_type": "",
        "abstract": [
            {
                "id": "",
                "title": "Abstract",
                "level": 0,
                "blocks": [{"type": "paragraph", "id": "", "text": "Test abstract"}],
                "children": [],
            }
        ],
        "translated_abstracts": [],
        "sections": [
            {
                "id": "",
                "title": "Introduction",
                "level": 1,
                "blocks": [{"type": "paragraph", "id": "", "text": "Some text"}],
                "children": [],
            }
        ],
        "appendices": [],
        "glossary": [],
        "footnotes": "",
        "acknowledgements": [],
        "notes": [],
    },
    "assets": {
        "citations": [],
        "tables": [],
        "figures": [],
        "equations": {"mathml": [], "tex": []},
        "supplementary_material": [],
    },
    "compliance": {
        "permissions": {},
        "copyright": "",
        "license": "",
        "ethics": {},
        "funding": [],
    },
    "metadata": {
        "keywords": [],
        "counts": {},
        "self_uri": [],
        "related_articles": [],
        "custom_meta": {},
    },
    "provenance": {
        "pmcgrab_version": "test",
        "parse_timestamp": "2024-01-01T00:00:00+00:00",
        "source": "test",
        "xml_source_path": "",
    },
}


class TestCLIComplete:
    """Complete coverage tests for CLI module."""

    def test_python_module_help_smoke(self):
        """Test the installed module entrypoint exposes CLI help."""
        result = subprocess.run(
            [sys.executable, "-m", "pmcgrab", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert result.stdout.startswith("usage: pmcgrab ")
        assert "--pmcids" in result.stdout

    def test_python_module_version_smoke(self):
        """Test the installed module entrypoint exposes the package version."""
        result = subprocess.run(
            [sys.executable, "-m", "pmcgrab", "--version"],
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert result.stdout.strip() == f"pmcgrab {pmcgrab.__version__}"

    def test_main_with_valid_args(self):
        """Test main function with valid arguments."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            test_args = [
                "pmcgrab_cli.py",
                "--pmcids",
                "7114487",
                "3084273",
                "--output-dir",
                str(output_dir),
                "--batch-size",
                "2",
            ]

            with patch("sys.argv", test_args):
                with patch(
                    "pmcgrab.cli.pmcgrab_cli.process_single_pmc"
                ) as mock_process:
                    mock_process.return_value = _DUMMY_ARTICLE
                    assert main() == 0
                    assert mock_process.call_count == 2

    def test_main_with_default_batch_size(self):
        """Test main function with default batch size."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            test_args = [
                "pmcgrab_cli.py",
                "--pmcids",
                "7114487",
                "--output-dir",
                str(output_dir),
            ]

            with patch("sys.argv", test_args):
                with patch(
                    "pmcgrab.cli.pmcgrab_cli.process_single_pmc"
                ) as mock_process:
                    mock_process.return_value = _DUMMY_ARTICLE
                    main()
                    mock_process.assert_called_once_with("7114487")

    def test_main_with_single_pmcid(self):
        """Test main function with single PMC ID."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            test_args = [
                "pmcgrab_cli.py",
                "--pmcids",
                "7114487",
                "--output-dir",
                str(output_dir),
                "--batch-size",
                "1",
            ]

            with patch("sys.argv", test_args):
                with patch(
                    "pmcgrab.cli.pmcgrab_cli.process_single_pmc"
                ) as mock_process:
                    mock_process.return_value = _DUMMY_ARTICLE
                    main()
                    mock_process.assert_called_once_with("7114487")

    def test_main_with_multiple_pmcids(self):
        """Test main function with multiple PMC IDs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            test_args = [
                "pmcgrab_cli.py",
                "--pmcids",
                "7114487",
                "3084273",
                "7690653",
                "--output-dir",
                str(output_dir),
                "--batch-size",
                "5",
            ]

            with patch("sys.argv", test_args):
                with patch(
                    "pmcgrab.cli.pmcgrab_cli.process_single_pmc"
                ) as mock_process:
                    # Third one fails
                    mock_process.side_effect = [
                        _DUMMY_ARTICLE,
                        _DUMMY_ARTICLE,
                        None,
                    ]
                    main()
                    assert mock_process.call_count == 3

    def test_main_with_processing_failures(self):
        """Test main function when processing fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            test_args = [
                "pmcgrab_cli.py",
                "--pmcids",
                "9999999",
                "--output-dir",
                str(output_dir),
            ]

            with patch("sys.argv", test_args):
                with patch(
                    "pmcgrab.cli.pmcgrab_cli.process_single_pmc"
                ) as mock_process:
                    mock_process.return_value = None
                    assert main() == 1
                    mock_process.assert_called_once()

    def test_main_with_exception_in_processing(self):
        """Test main function when processing raises exception."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            test_args = [
                "pmcgrab_cli.py",
                "--pmcids",
                "7114487",
                "--output-dir",
                str(output_dir),
            ]

            with patch("sys.argv", test_args):
                with patch(
                    "pmcgrab.cli.pmcgrab_cli.process_single_pmc"
                ) as mock_process:
                    mock_process.side_effect = Exception("Processing failed")
                    assert main() == 1

            summary = json.loads((output_dir / "summary.json").read_text())
            assert summary == {"7114487": False}

    def test_main_argument_parsing_edge_cases(self):
        """Test argument parsing edge cases."""
        with patch("sys.argv", ["pmcgrab_cli.py"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 2

    def test_main_with_invalid_batch_size(self, capsys):
        """Test main function with invalid batch size."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            test_args = [
                "pmcgrab_cli.py",
                "--pmcids",
                "7114487",
                "--output-dir",
                str(output_dir),
                "--batch-size",
                "0",
            ]

            with patch("sys.argv", test_args):
                with pytest.raises(SystemExit) as exc_info:
                    main()
        assert exc_info.value.code == 2
        assert "must be a positive integer" in capsys.readouterr().err

    def test_main_with_negative_batch_size(self, capsys):
        """Test main function with negative batch size."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            test_args = [
                "pmcgrab_cli.py",
                "--pmcids",
                "7114487",
                "--output-dir",
                str(output_dir),
                "--batch-size",
                "-1",
            ]

            with patch("sys.argv", test_args):
                with pytest.raises(SystemExit) as exc_info:
                    main()
        assert exc_info.value.code == 2
        assert "must be a positive integer" in capsys.readouterr().err

    def test_main_with_nested_output_dir(self, tmp_path):
        """Test main function creates a missing nested output directory."""
        output_dir = tmp_path / "missing" / "nested"

        test_args = [
            "pmcgrab_cli.py",
            "--pmcids",
            "7114487",
            "--output-dir",
            str(output_dir),
        ]

        with patch("sys.argv", test_args):
            with patch("pmcgrab.cli.pmcgrab_cli.process_single_pmc") as mock_process:
                mock_process.return_value = _DUMMY_ARTICLE
                main()

        assert (output_dir / "PMC7114487.json").exists()

    def test_main_help_option(self):
        """Test main function with help option."""
        test_args = ["pmcgrab_cli.py", "--help"]

        with patch("sys.argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 0

    def test_main_version_option(self, capsys):
        """Test main function with version option (if available)."""
        test_args = ["pmcgrab_cli.py", "--version"]

        with patch("sys.argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 0
        assert pmcgrab.__version__ in capsys.readouterr().out

    def test_main_verbose_option(self):
        """Test main function with verbose option (if available)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            test_args = [
                "pmcgrab_cli.py",
                "--pmcids",
                "7114487",
                "--output-dir",
                str(output_dir),
                "--verbose",
            ]

            with patch("sys.argv", test_args):
                with patch(
                    "pmcgrab.cli.pmcgrab_cli.process_single_pmc"
                ) as mock_process:
                    mock_process.return_value = _DUMMY_ARTICLE
                    main()

                mock_process.assert_called_once_with("7114487")

    def test_main_with_large_batch_size(self):
        """Test main function with very large batch size."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            test_args = [
                "pmcgrab_cli.py",
                "--pmcids",
                "7114487",
                "3084273",
                "--output-dir",
                str(output_dir),
                "--batch-size",
                "1000",
            ]

            with patch("sys.argv", test_args):
                with patch(
                    "pmcgrab.cli.pmcgrab_cli.process_single_pmc"
                ) as mock_process:
                    mock_process.return_value = _DUMMY_ARTICLE
                    main()
                    assert mock_process.call_count == 2

    def test_main_with_empty_pmcids_list(self):
        """Test main function with empty PMC IDs list."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            test_args = [
                "pmcgrab_cli.py",
                "--pmcids",
                "--output-dir",
                str(output_dir),
            ]

            with patch("sys.argv", test_args):
                with pytest.raises(SystemExit) as exc_info:
                    main()
        assert exc_info.value.code == 2

    def test_main_with_duplicate_pmcids(self):
        """Test main function with duplicate PMC IDs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            test_args = [
                "pmcgrab_cli.py",
                "--pmcids",
                "7114487",
                "7114487",
                "3084273",
                "--output-dir",
                str(output_dir),
            ]

            with patch("sys.argv", test_args):
                with patch(
                    "pmcgrab.cli.pmcgrab_cli.process_single_pmc"
                ) as mock_process:
                    mock_process.return_value = _DUMMY_ARTICLE
                    main()
                    assert mock_process.call_count == 3

    def test_main_argument_parser_creation(self):
        """Test argument parser creation and configuration."""
        with patch("sys.argv", ["pmcgrab_cli.py", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 0

    def test_main_with_mixed_valid_invalid_pmcids(self):
        """Test main function with mix of valid and invalid PMC IDs.

        The CLI now validates IDs before processing, so 'invalid' is
        filtered out during normalize_id. Only valid numeric IDs are
        passed to process_single_pmc.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            test_args = [
                "pmcgrab_cli.py",
                "--pmcids",
                "7114487",
                "PMCinvalid",
                "3084273",
                "--output-dir",
                str(output_dir),
            ]

            with patch("sys.argv", test_args):
                with patch(
                    "pmcgrab.cli.pmcgrab_cli.process_single_pmc"
                ) as mock_process:
                    mock_process.side_effect = [_DUMMY_ARTICLE, _DUMMY_ARTICLE]
                    main()
                    # "invalid" is filtered out during ID normalization,
                    # so only 2 valid IDs are processed
                    assert mock_process.call_count == 2

    def test_main_resolves_pmids_before_processing(self, tmp_path):
        """Test PMID mode converts IDs before processing."""
        output_dir = tmp_path / "out"
        test_args = [
            "pmcgrab_cli.py",
            "--pmids",
            "33087749",
            "--output-dir",
            str(output_dir),
        ]

        with patch("sys.argv", test_args):
            with patch("pmcgrab.cli.pmcgrab_cli.normalize_pmid") as mock_normalize:
                with patch(
                    "pmcgrab.cli.pmcgrab_cli.process_single_pmc"
                ) as mock_process:
                    mock_normalize.return_value = "7181753"
                    mock_process.return_value = _DUMMY_ARTICLE
                    main()

        mock_normalize.assert_called_once_with("33087749")
        mock_process.assert_called_once_with("7181753")

    def test_main_resolves_dois_before_processing(self, tmp_path):
        """Test DOI mode converts IDs before processing."""
        output_dir = tmp_path / "out"
        test_args = [
            "pmcgrab_cli.py",
            "--dois",
            "10.1234/example",
            "--output-dir",
            str(output_dir),
        ]

        with patch("sys.argv", test_args):
            with patch("pmcgrab.cli.pmcgrab_cli.normalize_id") as mock_normalize:
                with patch(
                    "pmcgrab.cli.pmcgrab_cli.process_single_pmc"
                ) as mock_process:
                    mock_normalize.return_value = "7181753"
                    mock_process.return_value = _DUMMY_ARTICLE
                    main()

        mock_normalize.assert_called_once_with("10.1234/example")
        mock_process.assert_called_once_with("7181753")

    def test_main_reads_id_file_comments_and_skips_invalid_ids(self, tmp_path):
        """Test ID-file mode skips comments, blanks, and invalid PMC IDs."""
        ids_file = tmp_path / "ids.txt"
        ids_file.write_text(
            "\n# comment\nPMC7114487\nPMCbad\n3084273\n",
            encoding="utf-8",
        )
        output_dir = tmp_path / "out"
        test_args = [
            "pmcgrab_cli.py",
            "--from-id-file",
            str(ids_file),
            "--output-dir",
            str(output_dir),
        ]

        with patch("sys.argv", test_args):
            with patch("pmcgrab.cli.pmcgrab_cli.process_single_pmc") as mock_process:
                mock_process.return_value = _DUMMY_ARTICLE
                main()

        assert [call.args[0] for call in mock_process.call_args_list] == [
            "7114487",
            "3084273",
        ]

    def test_main_output_directory_handling(self):
        """Test output directory creation and handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "nested" / "output"

            test_args = [
                "pmcgrab_cli.py",
                "--pmcids",
                "7114487",
                "--output-dir",
                str(output_dir),
            ]

            with patch("sys.argv", test_args):
                with patch(
                    "pmcgrab.cli.pmcgrab_cli.process_single_pmc"
                ) as mock_process:
                    mock_process.return_value = _DUMMY_ARTICLE
                    main()

            assert (output_dir / "PMC7114487.json").exists()

    def test_main_returns_error_for_no_valid_ids(self, tmp_path, capsys):
        """Invalid identifiers should fail with a non-zero CLI status."""
        output_dir = tmp_path / "out"
        test_args = [
            "pmcgrab_cli.py",
            "--pmcids",
            "PMCbad",
            "--output-dir",
            str(output_dir),
        ]

        with patch("sys.argv", test_args):
            assert main() == 2

        err = capsys.readouterr().err
        assert "Warning: Invalid PMC ID format" in err
        assert "No valid PMC IDs to process." in err

    def test_main_returns_error_for_missing_local_directory(self, tmp_path, capsys):
        """Missing local XML directories should fail with a non-zero status."""
        output_dir = tmp_path / "out"
        test_args = [
            "pmcgrab_cli.py",
            "--from-dir",
            str(tmp_path / "missing"),
            "--output-dir",
            str(output_dir),
        ]

        with patch("sys.argv", test_args):
            assert main() == 2

        assert "is not a directory" in capsys.readouterr().err

    def test_main_returns_error_for_empty_local_directory(self, tmp_path, capsys):
        """Empty local XML directories should fail with a non-zero status."""
        xml_dir = tmp_path / "xml"
        xml_dir.mkdir()
        output_dir = tmp_path / "out"
        test_args = [
            "pmcgrab_cli.py",
            "--from-dir",
            str(xml_dir),
            "--output-dir",
            str(output_dir),
        ]

        with patch("sys.argv", test_args):
            assert main() == 2

        assert "No XML files found" in capsys.readouterr().err

    def test_main_keyboard_interrupt(self):
        """Test main function handling keyboard interrupt."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            test_args = [
                "pmcgrab_cli.py",
                "--pmcids",
                "7114487",
                "--output-dir",
                str(output_dir),
            ]

            with patch("sys.argv", test_args):
                with patch(
                    "pmcgrab.cli.pmcgrab_cli.process_single_pmc"
                ) as mock_process:
                    mock_process.side_effect = KeyboardInterrupt("User interrupted")

                    with pytest.raises(KeyboardInterrupt):
                        main()

    def test_main_writes_json_and_summary(self):
        """Test that main writes JSON files and summary correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            test_args = [
                "pmcgrab_cli.py",
                "--pmcids",
                "7114487",
                "--output-dir",
                str(output_dir),
            ]

            with patch("sys.argv", test_args):
                with patch(
                    "pmcgrab.cli.pmcgrab_cli.process_single_pmc"
                ) as mock_process:
                    mock_process.return_value = _DUMMY_ARTICLE
                    main()

            # Verify JSON file was written
            json_file = output_dir / "PMC7114487.json"
            assert json_file.exists()
            data = json.loads(json_file.read_text(encoding="utf-8"))
            json.dumps(data, allow_nan=False)
            assert data["schema_version"] == 2
            assert data["title"]["main"] == "Test Article"

            # Verify summary was written
            summary = json.loads(
                (output_dir / "summary.json").read_text(encoding="utf-8")
            )
            assert summary["7114487"] is True

    def test_main_writes_jsonl(self, tmp_path):
        """Test JSONL output writes all successful articles to output.jsonl."""
        output_dir = tmp_path / "out"
        test_args = [
            "pmcgrab_cli.py",
            "--pmcids",
            "7114487",
            "--output-dir",
            str(output_dir),
            "--format",
            "jsonl",
        ]

        with patch("sys.argv", test_args):
            with patch("pmcgrab.cli.pmcgrab_cli.process_single_pmc") as mock_process:
                mock_process.return_value = _DUMMY_ARTICLE
                main()

        rows = (output_dir / "output.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(rows) == 1
        row = json.loads(rows[0])
        json.dumps(row, allow_nan=False)
        assert row["title"]["main"] == "Test Article"

    def test_main_quiet_disables_progress_bar(self, tmp_path):
        """Test quiet mode disables tqdm progress output."""
        output_dir = tmp_path / "out"
        test_args = [
            "pmcgrab_cli.py",
            "--pmcids",
            "7114487",
            "--output-dir",
            str(output_dir),
            "--quiet",
        ]

        with patch("sys.argv", test_args):
            with patch("pmcgrab.cli.pmcgrab_cli.process_single_pmc") as mock_process:
                with patch("pmcgrab.cli.pmcgrab_cli.tqdm") as mock_tqdm:
                    mock_process.return_value = _DUMMY_ARTICLE
                    main()

        assert mock_tqdm.call_args.kwargs["disable"] is True
