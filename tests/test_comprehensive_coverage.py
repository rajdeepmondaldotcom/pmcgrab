"""Comprehensive tests to achieve 100% coverage for remaining gaps."""

import datetime
import warnings
from unittest.mock import MagicMock, patch

import lxml.etree as ET
import pytest

from pmcgrab.application.paper_builder import build_paper_from_pmc
from pmcgrab.application.parsing import content, contributors, metadata, sections
from pmcgrab.common.html_cleaning import remove_html_tags, strip_html_text_styling
from pmcgrab.common.serialization import normalize_value
from pmcgrab.common.xml_processing import (
    generate_typed_mhtml_tag,
    remove_mhtml_tags,
    stringify_children,
)

# Import modules that need better coverage
from pmcgrab.constants import TimeoutException, timeout_handler
from pmcgrab.domain.value_objects import BasicBiMap
from pmcgrab.domain.value_objects import BasicBiMap as UtilsBiMap
from pmcgrab.domain.value_objects import make_hashable
from pmcgrab.fetch import clean_xml_string, fetch_pmc_xml_string, xml_tree_from_string
from pmcgrab.http_utils import _backoff_sleep, cached_get
from pmcgrab.model import Paper, TextSection, TextTable


class TestConstantsModule:
    """Test constants module functions."""

    def test_timeout_handler(self):
        """Test timeout handler raises TimeoutException."""
        import signal

        with pytest.raises(TimeoutException):
            timeout_handler(signal.SIGALRM, None)


class TestApplicationPaperBuilder:
    """Test application paper builder with edge cases."""

    @patch("pmcgrab.application.paper_builder.paper_dict_from_pmc")
    def test_build_paper_from_pmc_success(self, mock_paper_dict):
        """Test successful paper building."""
        mock_paper_dict.return_value = {
            "PMCID": 12345,
            "Title": "Test Paper",
            "Authors": None,
            "Abstract": None,
            "Body": None,
        }

        paper = build_paper_from_pmc(12345, email="test@example.com")

        assert isinstance(paper, Paper)
        assert paper.pmcid == 12345
        assert paper.title == "Test Paper"

    @patch("pmcgrab.application.paper_builder.paper_dict_from_pmc")
    @patch("pmcgrab.application.paper_builder.time.sleep")
    def test_build_paper_from_pmc_with_retries(self, mock_sleep, mock_paper_dict):
        """Test paper building with HTTP error retries."""
        from urllib.error import HTTPError

        # First two calls fail, third succeeds
        mock_paper_dict.side_effect = [
            HTTPError(url="test", code=500, msg="Server Error", hdrs=None, fp=None),
            HTTPError(url="test", code=500, msg="Server Error", hdrs=None, fp=None),
            {"PMCID": 12345, "Title": "Test Paper"},
        ]

        paper = build_paper_from_pmc(12345, email="test@example.com", attempts=3)

        assert isinstance(paper, Paper)
        assert mock_sleep.call_count == 2  # Sleep called twice for retries

    @patch("pmcgrab.application.paper_builder.paper_dict_from_pmc")
    def test_build_paper_from_pmc_returns_none(self, mock_paper_dict):
        """Test paper building returns None when dict is None."""
        mock_paper_dict.return_value = None

        paper = build_paper_from_pmc(12345, email="test@example.com")

        assert paper is None

    @patch("pmcgrab.application.paper_builder.paper_dict_from_pmc")
    def test_build_paper_from_pmc_empty_dict(self, mock_paper_dict):
        """Test paper building with empty dict."""
        mock_paper_dict.return_value = {}

        paper = build_paper_from_pmc(12345, email="test@example.com")

        # Empty dict is falsy, so function returns None
        assert paper is None


class TestApplicationParsingEdgeCases:
    """Test edge cases in application parsing modules."""

    def test_content_gather_version_history(self):
        """Test version history gathering."""
        xml = """<article>
            <article-meta>
                <article-version version="1.0">
                    <date>
                        <year>2024</year>
                        <month>1</month>
                        <day>15</day>
                    </date>
                </article-version>
                <article-version version="1.1">
                    <date>
                        <year>2024</year>
                        <month>2</month>
                        <day>1</day>
                    </date>
                </article-version>
            </article-meta>
        </article>"""
        root = ET.fromstring(xml)

        result = content.gather_version_history(root)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["Version"] == "1.0"
        assert result[0]["Date"] == "2024-01-15"

    def test_content_gather_ethics_disclosures(self):
        """Test ethics disclosures gathering."""
        xml = """<article>
            <back>
                <fn-group>
                    <fn fn-type="conflict">
                        <p>The authors declare no conflicts of interest.</p>
                    </fn>
                </fn-group>
                <ethics-statement>
                    <p>This study was approved by the ethics committee.</p>
                </ethics-statement>
            </back>
        </article>"""
        root = ET.fromstring(xml)

        result = content.gather_ethics_disclosures(root)

        assert isinstance(result, dict)
        assert "Conflicts of Interest" in result
        assert "Ethics Statement" in result

    def test_contributors_extract_contributor_info_edge_cases(self):
        """Test contributor info extraction with edge cases."""
        xml = """<article>
            <contrib-group>
                <contrib contrib-type="author">
                    <name>
                        <surname>Doe</surname>
                        <given-names>Jane   </given-names>  <!-- Extra spaces -->
                    </name>
                    <address><email>  jane@example.com  </email></address>
                    <xref ref-type="aff" rid="aff1"/>
                    <xref ref-type="aff" rid="aff2"/>  <!-- Multiple affiliations -->
                </contrib>
                <aff id="aff1"><institution>University 1</institution>Department 1</aff>
                <aff id="aff2"><institution>University 2</institution>Department 2</aff>
            </contrib-group>
        </article>"""
        root = ET.fromstring(xml)
        contribs = root.xpath(".//contrib[@contrib-type='author']")

        result = contributors.extract_contributor_info(root, contribs)

        assert len(result) == 1
        assert result[0][1] == "Jane"  # First name trimmed
        assert result[0][3] == "jane@example.com"  # Email trimmed
        assert len(result[0][4]) == 2  # Two affiliations

    def test_metadata_gather_keywords_multiple_groups(self):
        """Test keyword gathering with multiple groups."""
        xml = """<article>
            <front>
                <article-meta>
                    <kwd-group kwd-group-type="author">
                        <kwd>machine learning</kwd>
                        <kwd>AI</kwd>
                    </kwd-group>
                    <kwd-group kwd-group-type="subject">
                        <kwd>computer science</kwd>
                    </kwd-group>
                    <kwd-group>  <!-- No type -->
                        <kwd>general keyword</kwd>
                    </kwd-group>
                    <article-categories>
                        <subj-group subj-group-type="keyword">
                            <subject>category keyword</subject>
                        </subj-group>
                    </article-categories>
                </article-meta>
            </front>
        </article>"""
        root = ET.fromstring(xml)

        result = metadata.gather_keywords(root)

        assert isinstance(result, list)
        assert len(result) >= 3
        # Should contain both grouped and ungrouped keywords
        grouped_keywords = [item for item in result if isinstance(item, dict)]
        ungrouped_keywords = [item for item in result if isinstance(item, str)]
        assert len(grouped_keywords) >= 2
        assert len(ungrouped_keywords) >= 1

    def test_sections_collect_sections_with_warnings(self):
        """Test section collection with unexpected tags."""
        xml = """<abstract>
            <sec>
                <title>Background</title>
                <p>Background paragraph</p>
            </sec>
            <p>Direct paragraph</p>
            <unexpected-tag>Unexpected content</unexpected-tag>
        </abstract>"""
        root = ET.fromstring(xml)
        from pmcgrab.domain.value_objects import BasicBiMap

        ref_map = BasicBiMap()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = sections._collect_sections(root, "abstract", ref_map)

            # Should warn about unexpected tag
            assert len(w) >= 1
            assert any("Unexpected tag" in str(warning.message) for warning in w)

        assert len(result) == 2  # sec and p elements


class TestCommonUtilitiesEdgeCases:
    """Test edge cases in common utilities."""

    def test_html_cleaning_edge_cases(self):
        """Test HTML cleaning with edge cases."""
        # Test with malformed HTML
        malformed_html = "<p>Unclosed paragraph <b>bold text"
        result = remove_html_tags(malformed_html, ["<p>", "<b>"], {})
        assert "bold text" in result

        # Test with nested same tags
        nested_html = "<b><b>Double bold</b></b>"
        result = remove_html_tags(nested_html, ["<b>"], {})
        assert "Double bold" in result

        # Test with self-closing tags
        self_closing = "Text <br/> with <hr/> breaks"
        result = remove_html_tags(self_closing, ["<br/>", "<hr/>"], {})
        assert "Text" in result and "breaks" in result

    def test_html_text_styling_complex_replacements(self):
        """Test HTML text styling with complex replacements."""
        html = """<p>Text with <sup>superscript</sup> and <sub>subscript</sub></p>
                  <ul><li>Item 1</li><li>Item 2</li></ul>"""

        # strip_html_text_styling from utils only takes text and verbose parameters
        result = strip_html_text_styling(html)
        assert "superscript" in result
        assert "subscript" in result
        assert "Item 1" in result

    def test_serialization_edge_cases(self):
        """Test serialization with edge cases."""
        # Test with nested datetime objects
        nested_data = {
            "dates": {
                "created": datetime.datetime(2024, 1, 15, 10, 30),
                "modified": datetime.date(2024, 2, 1),
            },
            "data": [
                {"timestamp": datetime.datetime(2024, 1, 16, 14, 45)},
                {"date_only": datetime.date(2024, 1, 17)},
            ],
        }

        result = normalize_value(nested_data)

        assert result["dates"]["created"] == "2024-01-15T10:30:00"
        assert result["dates"]["modified"] == "2024-02-01"
        assert result["data"][0]["timestamp"] == "2024-01-16T14:45:00"
        assert result["data"][1]["date_only"] == "2024-01-17"

    def test_xml_processing_edge_cases(self):
        """Test XML processing with edge cases."""
        # Test stringify_children with mixed content
        xml = """<parent>
            Text before
            <child>Child text</child>
            Text between
            <another>Another child</another>
            Text after
        </parent>"""
        element = ET.fromstring(xml)

        result = stringify_children(element)
        assert "Text before" in result
        assert "Child text" in result
        assert "Text between" in result
        assert "Another child" in result
        assert "Text after" in result

    def test_mhtml_tag_generation_and_removal(self):
        """Test MHTML tag generation and removal."""
        # Test different tag types
        citation_tag = generate_typed_mhtml_tag("citation", 1)
        table_tag = generate_typed_mhtml_tag("table", 2)
        figure_tag = generate_typed_mhtml_tag("figure", 3)

        assert citation_tag != table_tag
        assert table_tag != figure_tag

        # Test removal
        text_with_tags = f"Text with {citation_tag} and {table_tag} and {figure_tag}."
        clean_text = remove_mhtml_tags(text_with_tags)

        assert citation_tag not in clean_text
        assert table_tag not in clean_text
        assert figure_tag not in clean_text
        assert "Text with" in clean_text


class TestDomainValueObjectsEdgeCases:
    """Test domain value objects with edge cases."""

    def test_make_hashable_deeply_nested(self):
        """Test make_hashable with deeply nested structures."""
        deeply_nested = {
            "level1": {
                "level2": {
                    "level3": [
                        {"level4": {"level5": "deep_value"}},
                        [1, 2, {"nested_list_dict": "value"}],
                    ]
                }
            }
        }

        result = make_hashable(deeply_nested)
        assert isinstance(result, tuple)
        # Should be hashable
        hash(result)  # This should not raise an exception

    def test_basic_bimap_edge_cases(self):
        """Test BasicBiMap with edge cases."""
        bm = BasicBiMap()

        # Test with complex values that need hashing
        complex_value = {"nested": [1, 2, {"deep": "value"}]}
        bm["complex"] = complex_value

        assert bm["complex"] == complex_value
        # Should be able to find in reverse map
        hashable_key = make_hashable(complex_value)
        assert bm.reverse[hashable_key] == "complex"

        # Test overwriting values
        bm["key1"] = "value1"
        bm["key2"] = "value1"  # Same value, different key

        # Reverse should point to the last key with this value
        assert bm.reverse["value1"] == "key2"

        # Test updating existing key
        bm["key1"] = "new_value"
        assert bm["key1"] == "new_value"
        assert bm.reverse["new_value"] == "key1"


class TestFetchModuleEdgeCases:
    """Test fetch module with edge cases."""

    @patch("pmcgrab.fetch.Entrez.efetch")
    def test_fetch_pmc_xml_string_with_retries(self, mock_efetch):
        """Test fetch with retry logic."""
        from urllib.error import HTTPError

        # First call fails, second succeeds
        mock_context1 = MagicMock()
        mock_context1.__enter__.return_value.read.side_effect = HTTPError(
            url="test", code=500, msg="Error", hdrs=None, fp=None
        )

        mock_context2 = MagicMock()
        mock_context2.__enter__.return_value.read.return_value = (
            b"<pmc-articleset><article><title>Test</title></article></pmc-articleset>"
        )

        mock_efetch.side_effect = [mock_context1, mock_context2]

        with patch("pmcgrab.fetch.time.sleep"):
            result = fetch_pmc_xml_string(12345, "test@example.com")

        assert "Test" in result
        assert mock_efetch.call_count == 2

    def test_clean_xml_string_edge_cases(self):
        """Test XML string cleaning with edge cases."""
        # Test with HTML entities
        xml_with_entities = "<root>&amp; &lt; &gt; &quot; &#39;</root>"
        result = clean_xml_string(xml_with_entities)
        assert isinstance(result, str)

        # Test with CDATA sections
        xml_with_cdata = "<root><![CDATA[Some <b>bold</b> text]]></root>"
        result = clean_xml_string(xml_with_cdata)
        assert isinstance(result, str)

    def test_xml_tree_from_string_edge_cases(self):
        """Test XML tree creation with edge cases."""
        # Test with processing instructions
        xml_with_pi = """<?xml version="1.0"?>
        <?xml-stylesheet type="text/xsl" href="style.xsl"?>
        <root>Content</root>"""

        tree = xml_tree_from_string(xml_with_pi)
        assert isinstance(tree, ET._ElementTree)

        # Test with comments
        xml_with_comments = """<?xml version="1.0"?>
        <!-- This is a comment -->
        <root>
            <!-- Another comment -->
            <child>Content</child>
        </root>"""

        tree = xml_tree_from_string(xml_with_comments)
        assert isinstance(tree, ET._ElementTree)


class TestHttpUtilsEdgeCases:
    """Test HTTP utils with edge cases."""

    @patch("time.sleep")
    def test_backoff_sleep_edge_cases(self, mock_sleep):
        """Test backoff sleep with edge cases."""
        # Test with negative retry (should handle gracefully)
        _backoff_sleep(-1)
        mock_sleep.assert_called_with(0.5)  # Should default to minimum

        mock_sleep.reset_mock()

        # Test with very large retry (should cap at 32)
        _backoff_sleep(20)
        mock_sleep.assert_called_with(32)

    @patch("requests.get")
    def test_cached_get_edge_cases(self, mock_get):
        """Test cached GET with edge cases."""
        # Test with various parameter types
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Test with None params
        result = cached_get("http://example.com", params=None)
        assert result == mock_response

        # Test with empty params
        result = cached_get("http://example.com", params={})
        assert result == mock_response


class TestModelEdgeCases:
    """Test model classes with edge cases."""

    def test_paper_abstract_as_str_edge_cases(self):
        """Test Paper abstract_as_str with edge cases."""
        # Test with None abstract
        paper = Paper({"PMCID": 123, "Abstract": None})
        assert paper.abstract_as_str() == ""

        # Test with empty abstract list
        paper = Paper({"PMCID": 123, "Abstract": []})
        assert paper.abstract_as_str() == ""

        # Test with abstract containing sections
        class MockSection:
            def __init__(self, text):
                self.text = text

            def __str__(self):
                return self.text

        mock_sections = [MockSection("Section 1"), MockSection("Section 2")]

        paper = Paper({"PMCID": 123, "Abstract": mock_sections})
        result = paper.abstract_as_str()
        assert "Section 1" in result
        assert "Section 2" in result

    def test_text_section_edge_cases(self):
        """Test TextSection with edge cases."""
        # Test with multiple titles (should warn)
        xml = """<sec>
            <title>First Title</title>
            <title>Second Title</title>
            <p>Content</p>
        </sec>"""
        element = ET.fromstring(xml)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            section = TextSection(element)

            # Should warn about multiple titles
            assert len(w) >= 1
            assert any("Multiple titles" in str(warning.message) for warning in w)

        assert section.title == "First Title"  # Should use first title

    def test_text_table_edge_cases(self):
        """Test TextTable with edge cases."""
        # Test with table that can't be parsed by pandas
        xml = """<table-wrap>
            <label>Unparseable Table</label>
            <caption><p>This table has no actual table data</p></caption>
            <table-wrap-foot>
                <p>Footer text</p>
            </table-wrap-foot>
        </table-wrap>"""
        element = ET.fromstring(xml)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            table = TextTable(element)

            # Should warn about parsing failure
            assert len(w) >= 1
            assert any("Table parsing failed" in str(warning.message) for warning in w)

        assert table.df is None
        assert "could not be parsed" in str(table)


class TestInfrastructureEdgeCases:
    """Test infrastructure with edge cases."""

    @patch.dict(
        "os.environ", {"PMCGRAB_EMAILS": "test1@example.com, test2@example.com, "}
    )
    def test_next_email_with_env_var(self):
        """Test email cycling with environment variable."""
        # Need to reload the module to pick up env var
        import importlib

        from pmcgrab.infrastructure import settings

        importlib.reload(settings)

        email1 = settings.next_email()
        email2 = settings.next_email()
        email3 = settings.next_email()  # Should cycle back

        assert email1 in ["test1@example.com", "test2@example.com"]
        assert email2 in ["test1@example.com", "test2@example.com"]
        assert email1 != email2
        assert email3 == email1  # Should cycle

    @patch.dict("os.environ", {"PMCGRAB_EMAILS": "   ,  ,  "})  # Empty/whitespace only
    def test_next_email_with_invalid_env_var(self):
        """Test email cycling with invalid environment variable."""
        import importlib

        from pmcgrab.infrastructure import settings

        importlib.reload(settings)

        # Should fall back to default emails
        email = settings.next_email()
        assert "@" in email  # Should be a valid email format


class TestUtilsModuleEdgeCases:
    """Test utils module with comprehensive edge cases."""

    def test_basic_bimap_utils_edge_cases(self):
        """Test BasicBiMap from utils module."""
        # Test the utils version of BasicBiMap
        bm = UtilsBiMap()

        # Test with various data types
        bm[1] = "one"
        bm["two"] = 2
        bm[3.14] = "pi"

        assert bm[1] == "one"
        assert bm["two"] == 2
        assert bm[3.14] == "pi"

        # Test reverse lookups
        assert bm.reverse["one"] == 1
        assert bm.reverse[2] == "two"
        assert bm.reverse["pi"] == 3.14
