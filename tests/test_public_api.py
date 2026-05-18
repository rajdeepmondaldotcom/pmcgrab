import inspect
from importlib import metadata

import pmcgrab


def test_runtime_version_matches_distribution_metadata():
    assert pmcgrab.__version__ == metadata.version("pmcgrab")


def test_top_level_process_single_pmc_exports_application_interface():
    signature = inspect.signature(pmcgrab.process_single_pmc)

    assert pmcgrab.process_single_pmc.__module__ == "pmcgrab.application.processing"
    assert "download" in signature.parameters
    assert "timeout" in signature.parameters
    assert "metadata_only" in signature.parameters
    assert "schema_version" in signature.parameters
    assert "output_style" in signature.parameters
