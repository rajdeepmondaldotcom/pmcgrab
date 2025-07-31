__version__ = "0.2.0"

from pmcgrab.fetch import get_xml
from pmcgrab.oai import list_records as oai_list_records, get_record as oai_get_record, list_identifiers as oai_list_identifiers, list_sets as oai_list_sets
from pmcgrab.oa_service import fetch as oa_fetch
from pmcgrab.bioc import fetch_json as bioc_fetch
from pmcgrab.idconvert import convert as id_convert
from pmcgrab.litctxp import export as citation_export
from pmcgrab.model import Paper
from pmcgrab.parser import build_complete_paper_dict, paper_dict_from_pmc
from pmcgrab.processing import (
    process_in_batches,
    process_in_batches_with_retry,
    process_pmc_ids_in_batches,
    process_single_pmc,
)

__all__ = [
    # external service helpers
    "oai_list_records",
    "oai_get_record",
    "oai_list_identifiers",
    "oai_list_sets",
    "oa_fetch",
    "bioc_fetch",
    "id_convert",
    "citation_export",
    "Paper",
    "build_complete_paper_dict",
    "get_xml",
    "paper_dict_from_pmc",
    "process_in_batches",
    "process_in_batches_with_retry",
    "process_pmc_ids_in_batches",
    "process_single_pmc",
]
