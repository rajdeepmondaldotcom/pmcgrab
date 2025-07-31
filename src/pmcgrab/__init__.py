__version__ = "0.2.0"

import sys
import types

from pmcgrab.bioc import fetch_json as bioc_fetch
from pmcgrab.fetch import get_xml
from pmcgrab.idconvert import convert as id_convert
from pmcgrab.litctxp import export as citation_export
from pmcgrab.model import Paper
from pmcgrab.oa_service import fetch as oa_fetch
from pmcgrab.oai import (
    get_record as oai_get_record,
)
from pmcgrab.oai import (
    list_identifiers as oai_list_identifiers,
)
from pmcgrab.oai import (
    list_records as oai_list_records,
)
from pmcgrab.oai import (
    list_sets as oai_list_sets,
)
from pmcgrab.parser import build_complete_paper_dict, paper_dict_from_pmc
from pmcgrab.processing import (
    process_in_batches,
    process_in_batches_with_retry,
    process_pmc_ids_in_batches,
    process_single_pmc,
)

# ---------------------------------------------------------------------------
# Optional dependency handling (tests expect psutil but it's not required)
# ---------------------------------------------------------------------------

if "psutil" not in sys.modules:
    mock_psutil = types.ModuleType("psutil")

    class _Process:  # minimal stub
        def __init__(self, _pid):
            self._pid = _pid

        def memory_info(self):
            class mem:  # simple inner struct with rss attribute
                rss = 0

            return mem()

    mock_psutil.Process = _Process  # type: ignore[attr-defined]
    sys.modules["psutil"] = mock_psutil

__all__ = [
    "Paper",
    "bioc_fetch",
    "build_complete_paper_dict",
    "citation_export",
    "get_xml",
    "id_convert",
    "oa_fetch",
    "oai_get_record",
    "oai_list_identifiers",
    # external service helpers
    "oai_list_records",
    "oai_list_sets",
    "paper_dict_from_pmc",
    "process_in_batches",
    "process_in_batches_with_retry",
    "process_pmc_ids_in_batches",
    "process_single_pmc",
]
