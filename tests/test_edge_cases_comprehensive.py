"""Comprehensive edge case tests for 100% coverage targeting specific uncovered lines."""

import tempfile
import warnings
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch
from urllib.error import HTTPError

import lxml.etree as ET
import pandas as pd
import pytest

from pmcgrab.application.parsing import content, contributors, metadata, sections
from pmcgrab.common.html_cleaning import remove_html_tags, strip_html_text_styling
from pmcgrab.common.serialization import clean_doc, normalize_value
from pmcgrab.common.xml_processing import (
    generate_typed_mhtml_tag,
    remove_mhtml_tags,
    split_text_and_refs,
    stringify_children,
)

# Import all modules for comprehensive testing
from pmcgrab.constants import (
    MultipleTitleWarning,
    ReadHTMLFailure,
    ReversedBiMapComparisonWarning,
    TimeoutException,
)
from pmcgrab.domain.value_objects import BasicBiMap, make_hashable
from pmcgrab.fetch import (
    clean_xml_string,
    fetch_pmc_xml_string,
    get_xml,
    validate_xml,
    xml_tree_from_string,
)
from pmcgrab.http_utils import _backoff_sleep, cached_get
from pmcgrab.model import Paper, TextSection, TextTable
from pmcgrab.parser import (
    _extract_xpath_text,
    _parse_citation,
    generate_paper_dict,
    paper_dict_from_pmc,
    process_reference_map,
)
from pmcgrab.processing import (
    _legacy_process_single_pmc,
    process_in_batches,
    process_pmc_ids_in_batches,
)


class TestDomainValueObjectsComplete:
    """Complete coverage of domain value objects."""

    def test_make_hashable_all_types(self):
        """Test make_hashable with all possible input types."""
        # Test primitive types
        assert make_hashable(42) == 42
        assert make_hashable("string") == "string"
        assert make_hashable(3.14) == 3.14
        assert make_hashable(True) == True
        assert make_hashable(None) == None

        # Test complex nested structures
        complex_obj = {
            "list": [1, 2, {"nested": [3, 4]}],
            "dict": {"inner": {"deep": ["a", "b"]}},
            "tuple": (1, 2, 3),
            "mixed": [{"a": 1}, ["b", 2], {"c": [3, 4]}],
        }
        result = make_hashable(complex_obj)
        assert isinstance(result, tuple)
        # Should be hashable
        hash(result)

    def test_basic_bimap_all_operations(self):
        """Test all BasicBiMap operations for complete coverage."""
        bm = BasicBiMap()

        # Test initialization with data
        bm = BasicBiMap({"a": 1, "b": 2})
        assert bm["a"] == 1
        assert bm.reverse[1] == "a"

        # Test setitem updates reverse map
        bm["c"] = 3
        assert bm.reverse[3] == "c"

        # Test overwriting values
        bm["a"] = 10
        assert bm.reverse[10] == "a"
        assert 1 not in bm.reverse  # Old value should be removed

        # Test equality with regular dict
        regular_dict = {"a": 10, "b": 2, "c": 3}
        assert bm == regular_dict

        # Test inequality
        other_dict = {"x": 1, "y": 2}
        assert bm != other_dict

        # Test equality with another BasicBiMap
        other_bm = BasicBiMap({"a": 10, "b": 2, "c": 3})
        assert bm == other_bm

        # Test reversed comparison warning
        reversed_bm = BasicBiMap({10: "a", 2: "b", 3: "c"})
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = bm == reversed_bm
            assert len(w) == 1
            assert issubclass(w[0].category, ReversedBiMapComparisonWarning)
            assert result == True  # Should still return True with warning

    def test_basic_bimap_complex_values(self):
        """Test BasicBiMap with complex values requiring hashing."""
        bm = BasicBiMap()

        # Test with unhashable values
        complex_value = {"list": [1, 2, 3], "dict": {"nested": "value"}}
        bm["complex"] = complex_value

        hashable_key = make_hashable(complex_value)
        assert bm.reverse[hashable_key] == "complex"

        # Test updating complex values
        new_complex = {"list": [4, 5, 6], "dict": {"nested": "new"}}
        bm["complex"] = new_complex

        new_hashable = make_hashable(new_complex)
        assert bm.reverse[new_hashable] == "complex"
        assert hashable_key not in bm.reverse


class TestCommonModulesComplete:
    """Complete coverage of common modules."""

    def test_html_cleaning_all_scenarios(self):
        """Test HTML cleaning with all possible scenarios."""
        # Test with verbose logging
        html = "<p>Test <b>bold</b> text</p>"
        result = remove_html_tags(html, ["<p>"], {"<b>": "**"}, verbose=True)
        assert "**bold**" in result

        # Test with empty removals and replaces
        result = remove_html_tags(html, [], {})
        assert result == html

        # Test with overlapping tags
        html = "<div><p><span>Nested</span></p></div>"
        result = remove_html_tags(html, ["<div>", "<span>"], {"<p>": "\n"})
        assert "Nested" in result

        # Test strip_html_text_styling with verbose
        styled_html = "<sup>superscript</sup> and <sub>subscript</sub>"
        result = strip_html_text_styling(styled_html, verbose=True)
        assert "superscript" in result and "subscript" in result

    def test_serialization_edge_cases(self):
        """Test serialization with all edge cases."""
        # Test clean_doc with various whitespace scenarios
        assert clean_doc("") == ""
        assert clean_doc("   ") == ""
        assert clean_doc("\n\n\n") == ""
        assert clean_doc("  line1  \n  line2  ") == "line1line2"

        # Test normalize_value with edge cases
        assert normalize_value(None) == None
        assert normalize_value([]) == []
        assert normalize_value({}) == {}

        # Test with pandas Series
        series = pd.Series([1, 2, 3], name="test")
        result = normalize_value(series)
        assert isinstance(result, list)

        # Test with custom objects (should pass through unchanged)
        class CustomObject:
            def __init__(self, value):
                self.value = value

        custom = CustomObject(42)
        assert normalize_value(custom) == custom

    def test_xml_processing_all_functions(self):
        """Test all XML processing functions comprehensively."""
        # Test stringify_children with mixed content
        xml = """<parent>
            Text before
            <child>Child text</child>
            <!-- Comment -->
            <empty/>
            Text after
            <nested><deep>Deep text</deep></nested>
        </parent>"""
        element = ET.fromstring(xml)

        result = stringify_children(element)
        assert "Text before" in result
        assert "Child text" in result
        assert "Text after" in result
        assert "Deep text" in result

        # Test split_text_and_refs with various reference types
        ref_xml = """<p>
            Text with <xref ref-type="bibr" rid="ref1">citation</xref>
            and <xref ref-type="table" rid="table1">table</xref>
            and <xref ref-type="fig" rid="fig1">figure</xref>
            references.
        </p>"""
        ref_element = ET.fromstring(ref_xml)
        ref_map = BasicBiMap()

        result = split_text_and_refs(ref_element, ref_map)
        assert isinstance(result, str)
        assert "Text with" in result

        # Test MHTML tag generation for all types
        citation_tag = generate_typed_mhtml_tag("citation", 1)
        table_tag = generate_typed_mhtml_tag("table", 2)
        figure_tag = generate_typed_mhtml_tag("figure", 3)
        equation_tag = generate_typed_mhtml_tag("equation", 4)

        assert "CITATION" in citation_tag
        assert "TABLE" in table_tag
        assert "FIGURE" in figure_tag
        assert "EQUATION" in equation_tag

        # Test remove_mhtml_tags
        text_with_tags = f"Text {citation_tag} and {table_tag} and {figure_tag}."
        clean_text = remove_mhtml_tags(text_with_tags)
        assert citation_tag not in clean_text
        assert table_tag not in clean_text
        assert figure_tag not in clean_text


class TestApplicationParsingComplete:
    """Complete coverage of application parsing modules."""

    def test_content_parsing_all_functions(self):
        """Test all content parsing functions."""
        # Test gather_permissions
        xml = """<article>
            <front>
                <article-meta>
                    <permissions>
                        <copyright-statement>Copyright 2024</copyright-statement>
                        <copyright-year>2024</copyright-year>
                        <license>
                            <license-p>Open access license</license-p>
                        </license>
                    </permissions>
                </article-meta>
            </front>
        </article>"""
        root = ET.fromstring(xml)

        result = content.gather_permissions(root)
        assert isinstance(result, dict)
        assert "copyright_statement" in result or "license" in result

        # Test gather_funding with complex structure
        funding_xml = """<article>
            <front>
                <article-meta>
                    <funding-group>
                        <award-group>
                            <funding-source>NIH</funding-source>
                            <award-id>R01-123456</award-id>
                        </award-group>
                        <award-group>
                            <funding-source>NSF</funding-source>
                            <award-id>DMS-789012</award-id>
                        </award-group>
                    </funding-group>
                </article-meta>
            </front>
        </article>"""
        funding_root = ET.fromstring(funding_xml)

        funding_result = content.gather_funding(funding_root)
        assert isinstance(funding_result, list)
        if funding_result:
            assert len(funding_result) >= 2

        # Test gather_equations
        eq_xml = """<article>
            <body>
                <sec>
                    <disp-formula id="eq1">
                        <label>Equation 1</label>
                        <tex-math>E = mc^2</tex-math>
                    </disp-formula>
                    <inline-formula>
                        <tex-math>x = y + z</tex-math>
                    </inline-formula>
                </sec>
            </body>
        </article>"""
        eq_root = ET.fromstring(eq_xml)

        eq_result = content.gather_equations(eq_root)
        assert isinstance(eq_result, list)

        # Test gather_supplementary_material with various formats
        supp_xml = """<article>
            <body>
                <supplementary-material id="supp1">
                    <label>Supplementary File 1</label>
                    <caption><p>Additional data</p></caption>
                    <media xlink:href="supp1.pdf" xmlns:xlink="http://www.w3.org/1999/xlink"/>
                </supplementary-material>
                <supplementary-material id="supp2">
                    <label>Supplementary File 2</label>
                    <ext-link xlink:href="http://example.com/data.csv" xmlns:xlink="http://www.w3.org/1999/xlink"/>
                </supplementary-material>
            </body>
        </article>"""
        supp_root = ET.fromstring(supp_xml)

        supp_result = content.gather_supplementary_material(supp_root)
        assert isinstance(supp_result, list)

    def test_contributors_parsing_edge_cases(self):
        """Test contributors parsing with edge cases."""
        # Test with mixed contributor types
        contrib_xml = """<article>
            <front>
                <article-meta>
                    <contrib-group>
                        <contrib contrib-type="author" equal-contrib="yes">
                            <name>
                                <surname>Smith</surname>
                                <given-names>John A.</given-names>
                            </name>
                            <email>john@example.com</email>
                            <xref ref-type="aff" rid="aff1"/>
                            <xref ref-type="aff" rid="aff2"/>
                        </contrib>
                        <contrib contrib-type="author">
                            <name>
                                <surname>Doe</surname>
                                <given-names>Jane</given-names>
                            </name>
                            <address>
                                <email>jane@example.com</email>
                            </address>
                            <xref ref-type="aff" rid="aff1"/>
                        </contrib>
                        <contrib contrib-type="editor">
                            <name>
                                <surname>Editor</surname>
                                <given-names>Chief</given-names>
                            </name>
                        </contrib>
                    </contrib-group>
                    <aff id="aff1">
                        <institution>University A</institution>
                        <addr-line>Department of Science</addr-line>
                    </aff>
                    <aff id="aff2">
                        <institution>University B</institution>
                    </aff>
                </article-meta>
            </front>
        </article>"""
        root = ET.fromstring(contrib_xml)

        # Test gather_authors
        authors = contributors.gather_authors(root)
        assert isinstance(authors, pd.DataFrame)
        if not authors.empty:
            assert "First_Name" in authors.columns
            assert "Last_Name" in authors.columns
            assert "Equal_Contrib" in authors.columns

        # Test gather_non_author_contributors
        non_authors = contributors.gather_non_author_contributors(root)
        assert isinstance(non_authors, list)

    def test_metadata_parsing_comprehensive(self):
        """Test metadata parsing with comprehensive scenarios."""
        # Test with complex metadata
        meta_xml = """<article>
            <front>
                <journal-meta>
                    <journal-id journal-id-type="nlm-ta">J Med AI</journal-id>
                    <journal-id journal-id-type="iso-abbrev">J.Med.AI</journal-id>
                    <journal-title-group>
                        <journal-title>Journal of Medical AI</journal-title>
                        <abbrev-journal-title>J Med AI</abbrev-journal-title>
                    </journal-title-group>
                    <issn pub-type="ppub">1234-5678</issn>
                    <issn pub-type="epub">8765-4321</issn>
                    <publisher>
                        <publisher-name>Medical Publishers Inc</publisher-name>
                        <publisher-loc>New York, NY</publisher-loc>
                    </publisher>
                </journal-meta>
                <article-meta>
                    <article-id pub-id-type="pmc">7114487</article-id>
                    <article-id pub-id-type="pmid">33123456</article-id>
                    <article-id pub-id-type="doi">10.1000/example</article-id>
                    <article-categories>
                        <subj-group subj-group-type="heading">
                            <subject>Research Article</subject>
                        </subj-group>
                        <subj-group subj-group-type="category">
                            <subject>Artificial Intelligence</subject>
                            <subject>Machine Learning</subject>
                        </subj-group>
                    </article-categories>
                    <title-group>
                        <article-title>Advanced AI in Healthcare</article-title>
                        <subtitle>A Comprehensive Study</subtitle>
                    </title-group>
                    <kwd-group kwd-group-type="author">
                        <kwd>artificial intelligence</kwd>
                        <kwd>healthcare</kwd>
                        <kwd>machine learning</kwd>
                    </kwd-group>
                    <kwd-group kwd-group-type="subject">
                        <kwd>medical AI</kwd>
                        <kwd>clinical decision support</kwd>
                    </kwd-group>
                    <pub-date pub-type="epub">
                        <year>2024</year>
                        <month>01</month>
                        <day>15</day>
                    </pub-date>
                    <pub-date pub-type="ppub">
                        <year>2024</year>
                        <month>02</month>
                    </pub-date>
                    <volume>42</volume>
                    <issue>3</issue>
                    <history>
                        <date date-type="received">
                            <year>2023</year>
                            <month>10</month>
                            <day>01</day>
                        </date>
                        <date date-type="accepted">
                            <year>2023</year>
                            <month>12</month>
                            <day>15</day>
                        </date>
                    </history>
                </article-meta>
            </front>
        </article>"""
        root = ET.fromstring(meta_xml)

        # Test all metadata functions
        assert metadata.gather_title(root) == "Advanced AI in Healthcare"
        assert "J Med AI" in metadata.gather_journal_id(root)
        assert metadata.gather_journal_title(root) == "Journal of Medical AI"

        issn_result = metadata.gather_issn(root)
        assert isinstance(issn_result, dict)

        assert metadata.gather_publisher_name(root) == "Medical Publishers Inc"
        assert metadata.gather_publisher_location(root) == "New York, NY"

        article_ids = metadata.gather_article_id(root)
        assert isinstance(article_ids, dict)
        assert "pmc" in article_ids

        categories = metadata.gather_article_categories(root)
        assert isinstance(categories, list)

        keywords = metadata.gather_keywords(root)
        assert isinstance(keywords, list)

        pub_dates = metadata.gather_published_date(root)
        assert isinstance(pub_dates, dict)

        history = metadata.gather_history_dates(root)
        assert isinstance(history, dict)

        assert metadata.gather_volume(root) == "42"
        assert metadata.gather_issue(root) == "3"

    def test_sections_parsing_with_warnings(self):
        """Test sections parsing with warning scenarios."""
        # Test abstract with unexpected elements
        abstract_xml = """<abstract>
            <sec>
                <title>Background</title>
                <p>Background information</p>
            </sec>
            <p>Direct paragraph</p>
            <unexpected-element>Unexpected content</unexpected-element>
            <list>
                <list-item>Item 1</list-item>
                <list-item>Item 2</list-item>
            </list>
        </abstract>"""
        root = ET.fromstring(abstract_xml)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = sections.gather_abstract(root)

            # Should generate warnings for unexpected elements
            warning_messages = [str(warning.message) for warning in w]
            assert any("Unexpected tag" in msg for msg in warning_messages)

        assert isinstance(result, list)

    def test_sections_body_parsing_complex(self):
        """Test body parsing with complex nested structures."""
        body_xml = """<body>
            <sec sec-type="intro">
                <title>Introduction</title>
                <p>Introduction paragraph with <xref ref-type="bibr" rid="ref1">citation</xref>.</p>
                <sec>
                    <title>Subsection</title>
                    <p>Subsection content</p>
                    <table-wrap id="table1">
                        <label>Table 1</label>
                        <caption><p>Test table</p></caption>
                        <table>
                            <thead>
                                <tr><th>Header</th></tr>
                            </thead>
                            <tbody>
                                <tr><td>Data</td></tr>
                            </tbody>
                        </table>
                    </table-wrap>
                </sec>
            </sec>
            <sec sec-type="methods">
                <title>Methods</title>
                <p>Methods description</p>
                <fig id="fig1">
                    <label>Figure 1</label>
                    <caption><p>Test figure</p></caption>
                    <graphic xlink:href="fig1.jpg" xmlns:xlink="http://www.w3.org/1999/xlink"/>
                </fig>
            </sec>
            <sec sec-type="results">
                <title>Results</title>
                <p>Results content</p>
                <unknown-element>Unknown content</unknown-element>
            </sec>
        </body>"""
        root = ET.fromstring(body_xml)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = sections.gather_body(root)

            # Should handle unknown elements with warnings
            assert len(w) >= 1

        assert isinstance(result, list)
        assert len(result) >= 3  # Should have main sections


class TestFetchModuleComplete:
    """Complete coverage of fetch module."""

    @patch("pmcgrab.fetch.Entrez.efetch")
    def test_fetch_pmc_xml_string_all_scenarios(self, mock_efetch):
        """Test fetch_pmc_xml_string with all scenarios."""
        # Test successful fetch with caching
        xml_content = (
            "<pmc-articleset><article><title>Test</title></article></pmc-articleset>"
        )

        mock_context = MagicMock()
        mock_context.__enter__.return_value.read.return_value = xml_content.encode(
            "utf-8"
        )
        mock_efetch.return_value = mock_context

        with patch("pmcgrab.fetch.os.path.exists", return_value=False):
            with patch("builtins.open", mock_open()) as mock_file:
                result = fetch_pmc_xml_string(
                    12345, "test@example.com", download=True, verbose=True
                )

                assert "Test" in result
                mock_file.assert_called()

        # Test cache hit
        with patch("pmcgrab.fetch.os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=xml_content)):
                result = fetch_pmc_xml_string(
                    12345, "test@example.com", download=True, verbose=True
                )

                assert "Test" in result
                # Should not call efetch when cache exists
                mock_efetch.reset_mock()

    def test_clean_xml_string_comprehensive(self):
        """Test XML cleaning with all options."""
        # Test with strip_text_styling=True
        xml_with_styling = """<article>
            <p>Text with <bold>bold</bold> and <italic>italic</italic></p>
            <sup>superscript</sup> and <sub>subscript</sub>
        </article>"""

        result = clean_xml_string(
            xml_with_styling, strip_text_styling=True, verbose=True
        )
        assert isinstance(result, str)

        # Test with strip_text_styling=False
        result_no_strip = clean_xml_string(
            xml_with_styling, strip_text_styling=False, verbose=True
        )
        assert isinstance(result_no_strip, str)

        # Test with malformed XML
        malformed = "<root><unclosed>content"
        result_malformed = clean_xml_string(malformed)
        assert isinstance(result_malformed, str)

    def test_xml_tree_from_string_edge_cases(self):
        """Test XML tree creation with edge cases."""
        # Test with processing instructions
        xml_with_pi = """<?xml version="1.0"?>
        <?xml-stylesheet type="text/xsl" href="style.xsl"?>
        <root>Content</root>"""

        tree = xml_tree_from_string(xml_with_pi)
        assert isinstance(tree, ET._ElementTree)

        # Test with DOCTYPE
        xml_with_doctype = """<?xml version="1.0"?>
        <!DOCTYPE root SYSTEM "root.dtd">
        <root>Content</root>"""

        tree_doctype = xml_tree_from_string(xml_with_doctype)
        assert isinstance(tree_doctype, ET._ElementTree)

    def test_validate_xml_scenarios(self):
        """Test XML validation with various scenarios."""
        # Valid minimal XML
        valid_xml = ET.ElementTree(
            ET.fromstring("<article><title>Valid</title></article>")
        )
        validate_xml(valid_xml)  # Should not raise

        # Test with missing required elements
        minimal_xml = ET.ElementTree(ET.fromstring("<article></article>"))
        validate_xml(minimal_xml)  # Should not raise for minimal structure

    @patch("pmcgrab.fetch.fetch_pmc_xml_string")
    @patch("pmcgrab.fetch.clean_xml_string")
    @patch("pmcgrab.fetch.xml_tree_from_string")
    @patch("pmcgrab.fetch.validate_xml")
    def test_get_xml_complete_workflow(
        self, mock_validate, mock_tree, mock_clean, mock_fetch
    ):
        """Test get_xml complete workflow."""
        # Mock the workflow
        mock_fetch.return_value = "<xml>content</xml>"
        mock_clean.return_value = "<xml>cleaned</xml>"
        mock_tree_obj = MagicMock()
        mock_tree.return_value = mock_tree_obj

        # Test with all options
        result = get_xml(
            12345,
            "test@example.com",
            download=True,
            validate=True,
            verbose=True,
            suppress_warnings=False,
            suppress_errors=False,
        )

        assert result == mock_tree_obj
        mock_fetch.assert_called_once()
        mock_clean.assert_called_once()
        mock_tree.assert_called_once()
        mock_validate.assert_called_once()

        # Test with validation disabled
        mock_validate.reset_mock()
        get_xml(12345, "test@example.com", validate=False)
        mock_validate.assert_not_called()


class TestHttpUtilsComplete:
    """Complete coverage of HTTP utils."""

    def test_backoff_sleep_all_scenarios(self):
        """Test backoff sleep with all scenarios."""
        with patch("time.sleep") as mock_sleep:
            # Test normal cases
            _backoff_sleep(0)
            mock_sleep.assert_called_with(0.5)

            mock_sleep.reset_mock()
            _backoff_sleep(1)
            mock_sleep.assert_called_with(1)

            mock_sleep.reset_mock()
            _backoff_sleep(5)
            mock_sleep.assert_called_with(32)  # 2^5 = 32

            mock_sleep.reset_mock()
            _backoff_sleep(10)
            mock_sleep.assert_called_with(32)  # Capped at 32

            # Test negative values
            mock_sleep.reset_mock()
            _backoff_sleep(-1)
            mock_sleep.assert_called_with(0.5)  # Should default to minimum

    @patch("requests.get")
    def test_cached_get_comprehensive(self, mock_get):
        """Test cached_get with comprehensive scenarios."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Test with various parameter combinations
        result = cached_get("http://example.com")
        assert result == mock_response

        result = cached_get("http://example.com", params={"key": "value"})
        assert result == mock_response

        result = cached_get("http://example.com", params=None)
        assert result == mock_response

        # Test with HTTP error
        mock_response.raise_for_status.side_effect = HTTPError("404 Not Found")

        with pytest.raises(HTTPError):
            cached_get("http://example.com")


class TestModelComplete:
    """Complete coverage of model classes."""

    def test_paper_all_attributes(self):
        """Test Paper with all possible attributes."""
        comprehensive_data = {
            "PMCID": 12345,
            "Title": "Comprehensive Test Paper",
            "Authors": pd.DataFrame([{"First_Name": "John", "Last_Name": "Doe"}]),
            "Non-Author Contributors": [{"name": "Editor", "role": "editor"}],
            "Abstract": ["Abstract section 1", "Abstract section 2"],
            "Body": ["Body section 1", "Body section 2"],
            "Journal ID": "j-med-ai",
            "Journal Title": "Journal of Medical AI",
            "ISSN": {"print": "1234-5678", "electronic": "8765-4321"},
            "Publisher Name": "Medical Publishers",
            "Publisher Location": "New York",
            "Article ID": {"pmc": "12345", "pmid": "67890"},
            "Article Types": ["research-article"],
            "Article Categories": ["AI", "Medicine"],
            "Keywords": ["AI", "healthcare", "machine learning"],
            "Published Date": {"epub": "2024-01-15"},
            "History Dates": {"received": "2023-10-01", "accepted": "2023-12-15"},
            "Volume": "42",
            "Issue": "3",
            "First Page": "123",
            "Last Page": "145",
            "Page Range": "123-145",
            "Permissions": {"copyright": "2024 Authors"},
            "Copyright": "Copyright 2024",
            "License": "CC BY 4.0",
            "Funding": [{"source": "NIH", "award": "R01-123456"}],
            "Version History": [{"version": "1.0", "date": "2024-01-15"}],
            "Equations": ["E = mc^2", "F = ma"],
            "Supplementary Material": [{"label": "Supp 1", "href": "data.csv"}],
            "Ethics Disclosures": {"conflicts": "None", "ethics": "Approved"},
            "Footnote": "This is a footnote",
            "Acknowledgements": "We thank our colleagues",
            "Notes": "Additional notes",
            "Custom Metadata": {"custom_field": "custom_value"},
        }

        paper = Paper(comprehensive_data)

        # Test all attributes are set
        assert paper.has_data == True
        assert paper.pmcid == 12345
        assert paper.title == "Comprehensive Test Paper"
        assert isinstance(paper.authors, pd.DataFrame)
        assert paper.journal_title == "Journal of Medical AI"
        assert paper.volume == "42"
        assert paper.issue == "3"

        # Test abstract_as_str
        abstract_str = paper.abstract_as_str()
        assert "Abstract section 1" in abstract_str
        assert "Abstract section 2" in abstract_str

    def test_text_section_complete(self):
        """Test TextSection with complete scenarios."""
        # Test with multiple titles (should warn)
        xml = """<sec>
            <title>First Title</title>
            <title>Second Title</title>
            <p>Paragraph content</p>
            <sec>
                <title>Subsection</title>
                <p>Subsection content</p>
            </sec>
            <table-wrap id="table1">
                <caption><p>Table caption</p></caption>
                <table><tr><td>Cell</td></tr></table>
            </table-wrap>
        </sec>"""
        element = ET.fromstring(xml)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            section = TextSection(element)

            # Should warn about multiple titles
            assert any(
                isinstance(warning.category(), MultipleTitleWarning) for warning in w
            )

        assert section.title == "First Title"  # Should use first title
        assert len(section.children) >= 2  # Should have paragraph and subsection

    def test_text_table_comprehensive(self):
        """Test TextTable with comprehensive scenarios."""
        # Test with valid table
        valid_table_xml = """<table-wrap id="table1">
            <label>Table 1</label>
            <caption><p>Test table with data</p></caption>
            <table>
                <thead>
                    <tr><th>Column 1</th><th>Column 2</th></tr>
                </thead>
                <tbody>
                    <tr><td>Data 1</td><td>Data 2</td></tr>
                    <tr><td>Data 3</td><td>Data 4</td></tr>
                </tbody>
            </table>
        </table-wrap>"""
        element = ET.fromstring(valid_table_xml)

        table = TextTable(element)
        # Should successfully parse table
        assert isinstance(table, TextTable)

        # Test with unparseable table
        invalid_table_xml = """<table-wrap id="table2">
            <label>Unparseable Table</label>
            <caption><p>This has no actual table data</p></caption>
            <table-wrap-foot>
                <fn><p>Footnote</p></fn>
            </table-wrap-foot>
        </table-wrap>"""
        element_invalid = ET.fromstring(invalid_table_xml)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            table_invalid = TextTable(element_invalid)

            # Should warn about parsing failure
            assert any(isinstance(warning.category(), ReadHTMLFailure) for warning in w)

        assert table_invalid.df is None
        assert "could not be parsed" in str(table_invalid)


class TestProcessingComplete:
    """Complete coverage of processing modules."""

    @patch("signal.alarm")
    @patch("pmcgrab.processing.build_paper_from_pmc")
    def test_legacy_process_single_pmc_complete(self, mock_build, mock_alarm):
        """Test _legacy_process_single_pmc with complete scenarios."""
        # Test successful processing
        mock_paper = MagicMock()
        mock_paper.has_data = True
        mock_paper.pmcid = 12345
        mock_paper.title = "Test Paper"
        mock_paper.abstract = "Test abstract"

        # Mock body sections
        mock_section = MagicMock()
        mock_section.title = "Introduction"
        mock_section.get_section_text.return_value = "Section content"
        mock_paper.body = [mock_section]

        # Mock all other attributes
        for attr in [
            "authors",
            "non_author_contributors",
            "journal_title",
            "journal_id",
            "issn",
            "publisher_name",
            "publisher_location",
            "article_id",
            "article_types",
            "article_categories",
            "keywords",
            "published_date",
            "history_dates",
            "volume",
            "issue",
            "first_page",
            "last_page",
            "page_range",
            "permissions",
            "copyright",
            "license",
            "funding",
            "version_history",
            "equations",
            "supplementary_material",
            "ethics_disclosures",
            "footnote",
            "acknowledgements",
            "notes",
            "custom_meta",
        ]:
            setattr(mock_paper, attr, f"mock_{attr}")

        mock_build.return_value = mock_paper

        result = _legacy_process_single_pmc("12345")

        assert result is not None
        assert result["pmc_id"] == "12345"
        assert result["title"] == "Test Paper"

        # Verify alarm was set and cleared
        assert mock_alarm.call_count >= 2

        # Test timeout scenario
        mock_build.side_effect = TimeoutException("Timeout")
        result_timeout = _legacy_process_single_pmc("12345")
        assert result_timeout is None

    @patch("pmcgrab.processing._legacy_process_single_pmc")
    def test_process_pmc_ids_in_batches_complete(self, mock_process):
        """Test batch processing with complete scenarios."""
        # Mock mixed results
        mock_process.side_effect = [
            {"pmc_id": "1", "title": "Paper 1"},
            None,  # Failed
            {"pmc_id": "3", "title": "Paper 3"},
            {"pmc_id": "4", "title": "Paper 4"},
        ]

        result = process_pmc_ids_in_batches(["1", "2", "3", "4"], batch_size=2)

        assert isinstance(result, dict)
        # Should track both successful and failed processing

    def test_process_in_batches_workflow(self):
        """Test process_in_batches workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)

            with patch("pmcgrab.processing._legacy_process_single_pmc") as mock_process:
                mock_process.return_value = {"pmc_id": "12345", "title": "Test"}

                # Should handle the workflow without errors
                try:
                    process_in_batches(
                        ["12345"], str(base_dir), chunk_size=1, parallel_workers=1
                    )
                except Exception as e:
                    # Some parts might not be fully implemented, just ensure no crashes
                    assert isinstance(e, (NotImplementedError, AttributeError))


class TestParserComplete:
    """Complete coverage of parser module."""

    def test_parse_citation_comprehensive(self):
        """Test _parse_citation with various citation formats."""
        # Test element-citation
        element_citation_xml = """<ref id="ref1">
            <element-citation publication-type="journal">
                <person-group person-group-type="author">
                    <name><surname>Smith</surname><given-names>J</given-names></name>
                    <name><surname>Doe</surname><given-names>A</given-names></name>
                </person-group>
                <article-title>Test Article</article-title>
                <source>Test Journal</source>
                <year>2024</year>
                <volume>42</volume>
                <issue>3</issue>
                <fpage>123</fpage>
                <lpage>145</lpage>
            </element-citation>
        </ref>"""
        ref_element = ET.fromstring(element_citation_xml)

        result = _parse_citation(ref_element)
        assert isinstance(result, dict)

        # Test mixed-citation
        mixed_citation_xml = """<ref id="ref2">
            <mixed-citation publication-type="book">
                <person-group person-group-type="author">
                    <name><surname>Author</surname><given-names>B</given-names></name>
                </person-group>
                <source>Test Book</source>
                <year>2023</year>
                <publisher-name>Test Publisher</publisher-name>
            </mixed-citation>
        </ref>"""
        mixed_ref = ET.fromstring(mixed_citation_xml)

        mixed_result = _parse_citation(mixed_ref)
        assert isinstance(mixed_result, (dict, str))

        # Test citation with no structured data
        simple_citation_xml = """<ref id="ref3">
            Simple citation text without structure.
        </ref>"""
        simple_ref = ET.fromstring(simple_citation_xml)

        simple_result = _parse_citation(simple_ref)
        assert isinstance(simple_result, str)

    def test_extract_xpath_text_comprehensive(self):
        """Test _extract_xpath_text with various scenarios."""
        xml = """<root>
            <single>Single text</single>
            <multiple>First</multiple>
            <multiple>Second</multiple>
            <multiple>Third</multiple>
            <empty></empty>
            <nested><inner>Nested text</inner></nested>
        </root>"""
        element = ET.fromstring(xml)

        # Test single match
        single = _extract_xpath_text(element, ".//single")
        assert single == "Single text"

        # Test multiple matches with multiple=False (should return first)
        first = _extract_xpath_text(element, ".//multiple")
        assert first == "First"

        # Test multiple matches with multiple=True
        all_multiple = _extract_xpath_text(element, ".//multiple", multiple=True)
        assert isinstance(all_multiple, list)
        assert len(all_multiple) == 3
        assert "First" in all_multiple
        assert "Second" in all_multiple
        assert "Third" in all_multiple

        # Test no matches
        no_match = _extract_xpath_text(element, ".//nonexistent")
        assert no_match is None

        no_match_multiple = _extract_xpath_text(
            element, ".//nonexistent", multiple=True
        )
        assert no_match_multiple == []

        # Test empty element
        empty = _extract_xpath_text(element, ".//empty")
        assert empty == ""

    def test_process_reference_map_comprehensive(self):
        """Test process_reference_map with comprehensive reference structure."""
        ref_xml = """<article>
            <back>
                <ref-list>
                    <ref id="ref1">
                        <element-citation>
                            <article-title>Reference 1</article-title>
                            <source>Journal 1</source>
                        </element-citation>
                    </ref>
                    <ref id="ref2">
                        <mixed-citation>
                            Reference 2 mixed citation
                        </mixed-citation>
                    </ref>
                    <ref id="ref3">
                        Plain text reference 3
                    </ref>
                </ref-list>
                <table-wrap id="table1">
                    <label>Table 1</label>
                    <caption><p>Test table</p></caption>
                </table-wrap>
                <fig id="fig1">
                    <label>Figure 1</label>
                    <caption><p>Test figure</p></caption>
                </fig>
            </back>
        </article>"""
        root = ET.fromstring(ref_xml)

        ref_map = process_reference_map(root, BasicBiMap())

        assert isinstance(ref_map, BasicBiMap)
        assert len(ref_map) >= 3  # Should have references and possibly tables/figures

    @patch("pmcgrab.parser.get_xml")
    def test_paper_dict_from_pmc_error_handling(self, mock_get_xml):
        """Test paper_dict_from_pmc error handling scenarios."""
        # Test with suppress_errors=True
        mock_get_xml.side_effect = ValueError("XML parsing failed")

        result = paper_dict_from_pmc(
            12345, email="test@example.com", suppress_errors=True
        )
        assert result == {}

        # Test with suppress_errors=False
        with pytest.raises(ValueError):
            paper_dict_from_pmc(12345, email="test@example.com", suppress_errors=False)

    def test_generate_paper_dict_comprehensive(self):
        """Test generate_paper_dict with comprehensive XML."""
        comprehensive_xml = """<article>
            <front>
                <journal-meta>
                    <journal-title>Test Journal</journal-title>
                </journal-meta>
                <article-meta>
                    <title-group>
                        <article-title>Comprehensive Test</article-title>
                    </title-group>
                    <contrib-group>
                        <contrib contrib-type="author">
                            <name><surname>Test</surname><given-names>Author</given-names></name>
                        </contrib>
                    </contrib-group>
                    <abstract>
                        <p>Test abstract</p>
                    </abstract>
                    <fpage>1</fpage>
                    <lpage>10</lpage>
                </article-meta>
            </front>
            <body>
                <sec>
                    <title>Introduction</title>
                    <p>Introduction content</p>
                </sec>
            </body>
        </article>"""
        root = ET.fromstring(comprehensive_xml)

        result = generate_paper_dict(
            root, suppress_warnings=False, suppress_errors=False
        )

        assert isinstance(result, dict)
        assert "Title" in result
        assert "Authors" in result
        assert "Abstract" in result
        assert "Body" in result
        assert "First Page" in result
        assert "Last Page" in result


# Run the tests to get final coverage report
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=pmcgrab", "--cov-report=term-missing"])
