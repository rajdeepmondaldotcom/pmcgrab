__version__ = "0.1.0"

from .model import Paper
from .fetch import get_xml
from .parser import paper_dict_from_pmc, build_complete_paper_dict
from .processing import process_single_pmc, process_pmc_ids_in_batches, process_in_batches, process_in_batches_with_retry

__all__ = [
    "Paper",
    "get_xml",
    "paper_dict_from_pmc",
    "build_complete_paper_dict",
    "process_single_pmc",
    "process_pmc_ids_in_batches",
    "process_in_batches",
    "process_in_batches_with_retry",
]
