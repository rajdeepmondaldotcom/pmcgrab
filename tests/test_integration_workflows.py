"""Integration tests for end-to-end workflows using real PMC IDs."""

import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import warnings

from pmcgrab.application.processing import process_single_pmc
from pmcgrab.application.paper_builder import build_paper_from_pmc
from pmcgrab.parser import paper_dict_from_pmc
from pmcgrab.model import Paper
from pmcgrab.infrastructure.settings import next_email
from pmcgrab.constants import TimeoutException


# Real PMC IDs from examples for integration testing
REAL_PMC_IDS = ["7114487", "3084273", "7690653"]
INVALID_PMC_IDS = ["999999999", "0", "-1", "invalid"]


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows with real and mocked data."""
    
    @pytest.mark.parametrize("pmcid", REAL_PMC_IDS)
    @patch('pmcgrab.fetch.Entrez.efetch')
    def test_complete_workflow_with_real_pmcids(self, mock_efetch, pmcid):
        """Test complete workflow from PMC ID to parsed paper object."""
        # Mock realistic XML response for each PMC ID
        mock_xml_responses = {
            "7114487": """<?xml version="1.0"?>
            <pmc-articleset>
                <article>
                    <front>
                        <article-meta>
                            <title-group>
                                <article-title>Machine Learning in Healthcare: A Comprehensive Review</article-title>
                            </title-group>
                            <contrib-group>
                                <contrib contrib-type="author">
                                    <name>
                                        <surname>Smith</surname>
                                        <given-names>John A</given-names>
                                    </name>
                                </contrib>
                            </contrib-group>
                            <abstract>
                                <p>This paper reviews machine learning applications in healthcare.</p>
                            </abstract>
                            <article-id pub-id-type="pmc">7114487</article-id>
                            <journal-meta>
                                <journal-title>AI in Medicine</journal-title>
                            </journal-meta>
                        </article-meta>
                    </front>
                    <body>
                        <sec>
                            <title>Introduction</title>
                            <p>Machine learning has revolutionized healthcare.</p>
                        </sec>
                    </body>
                </article>
            </pmc-articleset>""",
            "3084273": """<?xml version="1.0"?>
            <pmc-articleset>
                <article>
                    <front>
                        <article-meta>
                            <title-group>
                                <article-title>Deep Learning for Medical Image Analysis</article-title>
                            </title-group>
                            <contrib-group>
                                <contrib contrib-type="author">
                                    <name>
                                        <surname>Johnson</surname>
                                        <given-names>Emily R</given-names>
                                    </name>
                                </contrib>
                            </contrib-group>
                            <abstract>
                                <p>Deep learning techniques for analyzing medical images.</p>
                            </abstract>
                            <article-id pub-id-type="pmc">3084273</article-id>
                        </article-meta>
                    </front>
                    <body>
                        <sec>
                            <title>Methods</title>
                            <p>We used convolutional neural networks.</p>
                        </sec>
                    </body>
                </article>
            </pmc-articleset>""",
            "7690653": """<?xml version="1.0"?>
            <pmc-articleset>
                <article>
                    <front>
                        <article-meta>
                            <title-group>
                                <article-title>Natural Language Processing in Clinical Notes</article-title>
                            </title-group>
                            <contrib-group>
                                <contrib contrib-type="author">
                                    <name>
                                        <surname>Brown</surname>
                                        <given-names>Michael K</given-names>
                                    </name>
                                </contrib>
                            </contrib-group>
                            <abstract>
                                <p>NLP techniques for processing clinical documentation.</p>
                            </abstract>
                            <article-id pub-id-type="pmc">7690653</article-id>
                        </article-meta>
                    </front>
                    <body>
                        <sec>
                            <title>Results</title>
                            <p>Our NLP model achieved 95% accuracy.</p>
                        </sec>
                    </body>
                </article>
            </pmc-articleset>"""
        }
        
        # Mock the efetch context manager
        mock_context = MagicMock()
        mock_context.__enter__.return_value.read.return_value = mock_xml_responses[pmcid].encode('utf-8')
        mock_efetch.return_value = mock_context
        
        # Test the complete workflow
        email = next_email()
        
        # Step 1: Build paper from PMC
        paper = build_paper_from_pmc(int(pmcid), email=email)
        
        assert paper is not None
        assert isinstance(paper, Paper)
        assert paper.has_data
        assert paper.pmcid == int(pmcid)
        assert paper.title is not None
        assert len(paper.title) > 0
        
        # Step 2: Process single PMC (application layer)
        result = process_single_pmc(pmcid)
        
        assert result is not None
        assert isinstance(result, dict)
        assert result["pmc_id"] == pmcid
        assert "title" in result
        assert "abstract" in result
        assert "body" in result

    def test_batch_processing_workflow(self):
        """Test batch processing of multiple PMC IDs."""
        with patch('pmcgrab.application.processing.build_paper_from_pmc') as mock_build:
            # Mock different scenarios for each PMC ID
            mock_papers = []
            for i, pmcid in enumerate(REAL_PMC_IDS):
                mock_paper = MagicMock()
                mock_paper.has_data = True
                mock_paper.pmcid = int(pmcid)
                mock_paper.title = f"Test Paper {i+1}"
                mock_paper.abstract = f"Abstract for paper {i+1}"
                
                # Mock body with sections
                mock_section = MagicMock()
                mock_section.title = f"Section {i+1}"
                mock_section.get_section_text.return_value = f"Content for section {i+1}"
                mock_paper.body = [mock_section]
                
                # Mock other attributes
                for attr in ['authors', 'journal_title', 'published_date']:
                    setattr(mock_paper, attr, f"mock_{attr}_{i}")
                
                mock_papers.append(mock_paper)
            
            mock_build.side_effect = mock_papers
            
            # Process all PMC IDs
            results = []
            for pmcid in REAL_PMC_IDS:
                result = process_single_pmc(pmcid)
                if result:
                    results.append(result)
            
            assert len(results) == len(REAL_PMC_IDS)
            for i, result in enumerate(results):
                assert result["pmc_id"] == REAL_PMC_IDS[i]
                assert result["title"] == f"Test Paper {i+1}"

    def test_file_output_workflow(self):
        """Test complete workflow including file output like in examples."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "pmc_output"
            output_dir.mkdir(exist_ok=True)
            
            with patch('pmcgrab.application.processing.build_paper_from_pmc') as mock_build:
                # Mock a successful paper
                mock_paper = MagicMock()
                mock_paper.has_data = True
                mock_paper.pmcid = 7114487
                mock_paper.title = "Test Integration Paper"
                mock_paper.abstract = "This is a test abstract for integration testing."
                
                # Mock body
                mock_section = MagicMock()
                mock_section.title = "Introduction"
                mock_section.get_section_text.return_value = "Introduction content"
                mock_paper.body = [mock_section]
                
                # Mock other attributes
                mock_paper.authors = [{"name": "Test Author"}]
                mock_paper.journal_title = "Test Journal"
                
                mock_build.return_value = mock_paper
                
                # Process and save
                pmcid = "7114487"
                data = process_single_pmc(pmcid)
                
                assert data is not None
                
                # Save to file (like in examples)
                dest = output_dir / f"PMC{pmcid}.json"
                with dest.open("w", encoding="utf-8") as fh:
                    json.dump(data, fh, indent=2, ensure_ascii=False)
                
                # Verify file was created and contains expected data
                assert dest.exists()
                
                with dest.open("r", encoding="utf-8") as fh:
                    saved_data = json.load(fh)
                
                assert saved_data["pmc_id"] == pmcid
                assert saved_data["title"] == "Test Integration Paper"
                assert "abstract" in saved_data
                assert "body" in saved_data


class TestErrorHandlingScenarios:
    """Test comprehensive error handling scenarios."""
    
    @pytest.mark.parametrize("invalid_pmcid", INVALID_PMC_IDS)
    def test_invalid_pmcid_handling(self, invalid_pmcid):
        """Test handling of various invalid PMC IDs."""
        with patch('pmcgrab.fetch.Entrez.efetch') as mock_efetch:
            # Mock HTTP error for invalid PMC IDs
            from urllib.error import HTTPError
            mock_context = MagicMock()
            mock_context.__enter__.return_value.read.side_effect = HTTPError(
                url="test", code=400, msg="Bad Request", hdrs=None, fp=None
            )
            mock_efetch.return_value = mock_context
            
            # Should handle error gracefully
            try:
                result = process_single_pmc(invalid_pmcid)
                # Should return None for invalid IDs
                assert result is None
            except Exception as e:
                # Or raise a handled exception
                assert isinstance(e, (HTTPError, ValueError, TimeoutException))

    def test_network_timeout_scenarios(self):
        """Test various network timeout scenarios."""
        with patch('pmcgrab.fetch.Entrez.efetch') as mock_efetch:
            # Test timeout during fetch
            mock_context = MagicMock()
            mock_context.__enter__.return_value.read.side_effect = TimeoutException("Network timeout")
            mock_efetch.return_value = mock_context
            
            result = process_single_pmc("7114487")
            assert result is None

    def test_malformed_xml_handling(self):
        """Test handling of malformed XML responses."""
        with patch('pmcgrab.fetch.Entrez.efetch') as mock_efetch:
            # Mock malformed XML
            malformed_xml = b"<invalid><xml>Not properly closed"
            
            mock_context = MagicMock()
            mock_context.__enter__.return_value.read.return_value = malformed_xml
            mock_efetch.return_value = mock_context
            
            # Should handle malformed XML gracefully
            result = process_single_pmc("7114487")
            # Depending on implementation, might return None or raise handled exception
            assert result is None or isinstance(result, dict)

    def test_empty_xml_response(self):
        """Test handling of empty XML responses."""
        with patch('pmcgrab.fetch.Entrez.efetch') as mock_efetch:
            mock_context = MagicMock()
            mock_context.__enter__.return_value.read.return_value = b""
            mock_efetch.return_value = mock_context
            
            result = process_single_pmc("7114487")
            assert result is None

    def test_xml_with_missing_required_fields(self):
        """Test XML with missing required fields."""
        with patch('pmcgrab.fetch.Entrez.efetch') as mock_efetch:
            # XML without title or other required fields
            minimal_xml = b"""<?xml version="1.0"?>
            <pmc-articleset>
                <article>
                    <front>
                        <article-meta>
                            <!-- Missing title-group -->
                        </article-meta>
                    </front>
                </article>
            </pmc-articleset>"""
            
            mock_context = MagicMock()
            mock_context.__enter__.return_value.read.return_value = minimal_xml
            mock_efetch.return_value = mock_context
            
            result = process_single_pmc("7114487")
            # Should still create a result but with None/empty values
            if result:
                assert result["title"] is None or result["title"] == ""

    def test_memory_pressure_scenarios(self):
        """Test behavior under memory pressure with large documents."""
        with patch('pmcgrab.fetch.Entrez.efetch') as mock_efetch:
            # Create a large XML document
            large_content = "<p>" + "Very long content. " * 10000 + "</p>"
            large_xml = f"""<?xml version="1.0"?>
            <pmc-articleset>
                <article>
                    <front>
                        <article-meta>
                            <title-group>
                                <article-title>Large Document Test</article-title>
                            </title-group>
                        </article-meta>
                    </front>
                    <body>
                        <sec>
                            <title>Large Section</title>
                            {large_content}
                        </sec>
                    </body>
                </article>
            </pmc-articleset>""".encode('utf-8')
            
            mock_context = MagicMock()
            mock_context.__enter__.return_value.read.return_value = large_xml
            mock_efetch.return_value = mock_context
            
            # Should handle large documents without crashing
            result = process_single_pmc("7114487")
            if result:
                assert "title" in result
                assert len(result["body"]) > 0


class TestEdgeCaseScenarios:
    """Test edge cases and boundary conditions."""
    
    def test_unicode_and_special_characters(self):
        """Test handling of Unicode and special characters."""
        with patch('pmcgrab.fetch.Entrez.efetch') as mock_efetch:
            unicode_xml = """<?xml version="1.0" encoding="UTF-8"?>
            <pmc-articleset>
                <article>
                    <front>
                        <article-meta>
                            <title-group>
                                <article-title>测试文档 with émojis 🧬 and special chars &amp; &lt; &gt;</article-title>
                            </title-group>
                            <contrib-group>
                                <contrib contrib-type="author">
                                    <name>
                                        <surname>Müller</surname>
                                        <given-names>François</given-names>
                                    </name>
                                </contrib>
                            </contrib-group>
                            <abstract>
                                <p>Abstract with Greek letters α, β, γ and math symbols ∑, ∫, ∞</p>
                            </abstract>
                        </article-meta>
                    </front>
                    <body>
                        <sec>
                            <title>Section with 中文</title>
                            <p>Content with various Unicode: café, naïve, résumé</p>
                        </sec>
                    </body>
                </article>
            </pmc-articleset>""".encode('utf-8')
            
            mock_context = MagicMock()
            mock_context.__enter__.return_value.read.return_value = unicode_xml
            mock_efetch.return_value = mock_context
            
            result = process_single_pmc("7114487")
            
            assert result is not None
            assert "测试文档" in result["title"]
            assert "α, β, γ" in result["abstract"]

    def test_deeply_nested_xml_structure(self):
        """Test handling of deeply nested XML structures."""
        with patch('pmcgrab.fetch.Entrez.efetch') as mock_efetch:
            nested_xml = """<?xml version="1.0"?>
            <pmc-articleset>
                <article>
                    <front>
                        <article-meta>
                            <title-group>
                                <article-title>Deeply Nested Structure Test</article-title>
                            </title-group>
                        </article-meta>
                    </front>
                    <body>
                        <sec>
                            <title>Level 1</title>
                            <sec>
                                <title>Level 2</title>
                                <sec>
                                    <title>Level 3</title>
                                    <sec>
                                        <title>Level 4</title>
                                        <p>Deep content with <bold>formatting</bold> and 
                                           <italic>nested <underline>elements</underline></italic>
                                        </p>
                                    </sec>
                                </sec>
                            </sec>
                        </sec>
                    </body>
                </article>
            </pmc-articleset>""".encode('utf-8')
            
            mock_context = MagicMock()
            mock_context.__enter__.return_value.read.return_value = nested_xml
            mock_efetch.return_value = mock_context
            
            result = process_single_pmc("7114487")
            
            assert result is not None
            assert "body" in result
            # Should handle deep nesting without stack overflow

    def test_xml_with_many_references(self):
        """Test XML with many citations and references."""
        with patch('pmcgrab.fetch.Entrez.efetch') as mock_efetch:
            # Create XML with many references
            refs = []
            for i in range(100):
                refs.append(f"""
                    <ref id="ref{i}">
                        <element-citation>
                            <person-group person-group-type="author">
                                <name><surname>Author{i}</surname><given-names>A{i}</given-names></name>
                            </person-group>
                            <article-title>Reference {i}</article-title>
                            <source>Journal {i}</source>
                            <year>202{i % 10}</year>
                        </element-citation>
                    </ref>""")
            
            many_refs_xml = f"""<?xml version="1.0"?>
            <pmc-articleset>
                <article>
                    <front>
                        <article-meta>
                            <title-group>
                                <article-title>Paper with Many References</article-title>
                            </title-group>
                        </article-meta>
                    </front>
                    <body>
                        <sec>
                            <title>Introduction</title>
                            <p>This paper cites many works {''.join(f'<xref ref-type="bibr" rid="ref{i}">({i})</xref>' for i in range(50))}.</p>
                        </sec>
                    </body>
                    <back>
                        <ref-list>
                            {''.join(refs)}
                        </ref-list>
                    </back>
                </article>
            </pmc-articleset>""".encode('utf-8')
            
            mock_context = MagicMock()
            mock_context.__enter__.return_value.read.return_value = many_refs_xml
            mock_efetch.return_value = mock_context
            
            result = process_single_pmc("7114487")
            
            assert result is not None
            # Should handle many references efficiently

    def test_concurrent_processing_safety(self):
        """Test thread safety during concurrent processing."""
        import threading
        import time
        
        results = []
        errors = []
        
        def process_pmcid(pmcid):
            try:
                with patch('pmcgrab.fetch.Entrez.efetch') as mock_efetch:
                    mock_xml = f"""<?xml version="1.0"?>
                    <pmc-articleset>
                        <article>
                            <front>
                                <article-meta>
                                    <title-group>
                                        <article-title>Concurrent Test {pmcid}</article-title>
                                    </title-group>
                                </article-meta>
                            </front>
                        </article>
                    </pmc-articleset>""".encode('utf-8')
                    
                    mock_context = MagicMock()
                    mock_context.__enter__.return_value.read.return_value = mock_xml
                    mock_efetch.return_value = mock_context
                    
                    result = process_single_pmc(str(pmcid))
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=process_pmcid, args=(7114487 + i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should not have any thread safety errors
        assert len(errors) == 0
        assert len(results) == 5

    def test_email_rotation_workflow(self):
        """Test email rotation in batch processing."""
        emails_used = []
        
        def mock_next_email():
            email = next_email()
            emails_used.append(email)
            return email
        
        with patch('pmcgrab.infrastructure.settings.next_email', side_effect=mock_next_email):
            with patch('pmcgrab.application.processing.build_paper_from_pmc') as mock_build:
                mock_paper = MagicMock()
                mock_paper.has_data = True
                mock_paper.pmcid = 7114487
                mock_paper.title = "Test Paper"
                mock_build.return_value = mock_paper
                
                # Process multiple PMC IDs to test email rotation
                for pmcid in REAL_PMC_IDS:
                    process_single_pmc(pmcid)
        
        # Should have used different emails (if pool has multiple)
        assert len(emails_used) == len(REAL_PMC_IDS)
        # If there are multiple emails in the pool, they should rotate
        unique_emails = set(emails_used)
        assert len(unique_emails) >= 1  # At least one email used


class TestPerformanceAndStress:
    """Test performance characteristics and stress scenarios."""
    
    def test_large_batch_processing(self):
        """Test processing of large batches of PMC IDs."""
        large_batch = [str(7114487 + i) for i in range(20)]
        
        with patch('pmcgrab.application.processing.build_paper_from_pmc') as mock_build:
            # Mock fast responses
            mock_paper = MagicMock()
            mock_paper.has_data = True
            mock_paper.title = "Batch Test Paper"
            mock_build.return_value = mock_paper
            
            start_time = time.time()
            successful_results = []
            
            for pmcid in large_batch:
                result = process_single_pmc(pmcid)
                if result:
                    successful_results.append(result)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Should process efficiently
            assert len(successful_results) == len(large_batch)
            assert processing_time < 10  # Should complete within 10 seconds with mocking

    def test_memory_usage_with_large_documents(self):
        """Test memory usage patterns with large documents."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        with patch('pmcgrab.fetch.Entrez.efetch') as mock_efetch:
            # Create multiple large documents
            for i in range(5):
                large_xml = f"""<?xml version="1.0"?>
                <pmc-articleset>
                    <article>
                        <front>
                            <article-meta>
                                <title-group>
                                    <article-title>Large Document {i}</article-title>
                                </title-group>
                            </article-meta>
                        </front>
                        <body>
                            {''.join(f'<sec><title>Section {j}</title><p>{"Large content. " * 1000}</p></sec>' for j in range(10))}
                        </body>
                    </article>
                </pmc-articleset>""".encode('utf-8')
                
                mock_context = MagicMock()
                mock_context.__enter__.return_value.read.return_value = large_xml
                mock_efetch.return_value = mock_context
                
                result = process_single_pmc(str(7114487 + i))
                assert result is not None
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for this test)
        assert memory_increase < 100 * 1024 * 1024

    def test_error_recovery_patterns(self):
        """Test error recovery and resilience patterns."""
        pmcids_to_test = ["7114487", "3084273", "7690653"]
        
        with patch('pmcgrab.fetch.Entrez.efetch') as mock_efetch:
            # Simulate intermittent failures
            call_count = 0
            
            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                
                mock_context = MagicMock()
                
                if call_count % 2 == 0:  # Every second call fails
                    from urllib.error import HTTPError
                    mock_context.__enter__.return_value.read.side_effect = HTTPError(
                        url="test", code=500, msg="Server Error", hdrs=None, fp=None
                    )
                else:  # Successful calls
                    mock_xml = f"""<?xml version="1.0"?>
                    <pmc-articleset>
                        <article>
                            <front>
                                <article-meta>
                                    <title-group>
                                        <article-title>Recovery Test {call_count}</article-title>
                                    </title-group>
                                </article-meta>
                            </front>
                        </article>
                    </pmc-articleset>""".encode('utf-8')
                    mock_context.__enter__.return_value.read.return_value = mock_xml
                
                return mock_context
            
            mock_efetch.side_effect = side_effect
            
            successful_results = []
            failed_results = []
            
            for pmcid in pmcids_to_test:
                try:
                    result = process_single_pmc(pmcid)
                    if result:
                        successful_results.append(result)
                    else:
                        failed_results.append(pmcid)
                except Exception:
                    failed_results.append(pmcid)
            
            # Should have some successes and some failures
            assert len(successful_results) > 0
            assert len(failed_results) > 0
            assert len(successful_results) + len(failed_results) == len(pmcids_to_test)