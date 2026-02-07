"""PMCGrab: AI-ready retrieval and parsing of PubMed Central articles.

PMCGrab is a specialized Python toolkit for retrieving, validating and
restructuring PubMed Central (PMC) articles into clean, section-aware JSON
that large-language-model (LLM) pipelines can ingest directly for
Retrieval-Augmented Generation (RAG), question-answering, summarization
and other downstream tasks.

Key Features:
    * **Effortless Retrieval**: Fetch full-text articles with a single PMCID using NCBI Entrez
    * **AI-Optimized JSON**: Output is pre-segmented into Introduction, Methods, Results, Discussion, etc.
    * **Highly Concurrent**: Multithreaded batch downloader with configurable worker count, retries and timeouts
    * **HTML & Reference Cleaning**: Utilities to strip or normalize embedded HTML, citations and footnotes

Examples:
    Basic usage for retrieving a single paper:

        >>> from pmcgrab import Paper
        >>> paper = Paper.from_pmc("7181753", email="your-email@example.com")
        >>> print(paper.title)
        >>> print(paper.body["Introduction"][:500])

    Batch processing multiple papers:

        >>> from pmcgrab import process_pmc_ids_in_batches
        >>> pmc_ids = ["7181753", "3539614", "5454911"]
        >>> process_pmc_ids_in_batches(pmc_ids, "./output", batch_size=8)

Classes:
    Paper: Container for all parsed information about a PMC article

Functions:
    get_xml: Fetch, parse and optionally validate XML for a PMCID
    parse_local_xml: Read and parse a local JATS XML file from disk
    paper_dict_from_pmc: Convert PMC article to structured dictionary
    paper_dict_from_local_xml: Convert local JATS XML file to structured dictionary
    build_complete_paper_dict: Low-level orchestrator for parsing PMC XML
    process_single_pmc: Download and parse a single PMC article
    process_single_local_xml: Parse a single local JATS XML file
    process_local_xml_dir: Batch-process a directory of local XML files
    process_pmc_ids_in_batches: Process multiple PMC IDs concurrently
    process_in_batches: Process PMC IDs in sequential chunks
    process_in_batches_with_retry: Batch processing with automatic retries

External Service Functions:
    bioc_fetch: Fetch JSON from BioC service
    id_convert: Convert between different identifier types
    citation_export: Export citations in various formats
    oa_fetch: Fetch from Open Access service
    oai_get_record: Get OAI-PMH record
    oai_list_identifiers: List OAI-PMH identifiers
    oai_list_records: List OAI-PMH records
    oai_list_sets: List OAI-PMH sets
"""

__version__ = "0.6.0"

from pmcgrab.application.processing import (
    process_local_xml_dir,
    process_single_local_xml,
)
from pmcgrab.bioc import fetch_json as bioc_fetch
from pmcgrab.fetch import get_xml, parse_local_xml
from pmcgrab.idconvert import convert as id_convert
from pmcgrab.idconvert import (
    normalize_id,
    normalize_ids,
    normalize_pmid,
    normalize_pmids,
)
from pmcgrab.litctxp import export as citation_export
from pmcgrab.model import Paper
from pmcgrab.oa_service import fetch as oa_fetch
from pmcgrab.oai import get_record as oai_get_record
from pmcgrab.oai import list_identifiers as oai_list_identifiers
from pmcgrab.oai import list_records as oai_list_records
from pmcgrab.oai import list_sets as oai_list_sets
from pmcgrab.parser import (
    build_complete_paper_dict,
    paper_dict_from_local_xml,
    paper_dict_from_pmc,
)
from pmcgrab.processing import (
    process_in_batches,
    process_in_batches_with_retry,
    process_pmc_ids_in_batches,
    process_single_pmc,
)

__all__ = [
    "Paper",
    "bioc_fetch",
    "build_complete_paper_dict",
    "citation_export",
    "get_xml",
    "id_convert",
    "normalize_id",
    "normalize_ids",
    "normalize_pmid",
    "normalize_pmids",
    "oa_fetch",
    "oai_get_record",
    "oai_list_identifiers",
    "oai_list_records",
    "oai_list_sets",
    # Local XML processing
    "paper_dict_from_local_xml",
    "paper_dict_from_pmc",
    "parse_local_xml",
    "process_in_batches",
    "process_in_batches_with_retry",
    "process_local_xml_dir",
    "process_pmc_ids_in_batches",
    "process_single_local_xml",
    "process_single_pmc",
]
