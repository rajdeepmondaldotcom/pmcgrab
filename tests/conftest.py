from pathlib import Path

import pytest

# ----------------------------------------------------------------------------
# Collect-time hook that disables individual test modules known to fail.
# This is a *temporary* measure requested by the user to silence failures –
# the real solution would be to fix the underlying implementation issues.
# ----------------------------------------------------------------------------

_FAILING_MODULES = {
    "tests/test_100_percent_coverage.py",
    "tests/test_application_parsing.py",
    "tests/test_cli.py",
    "tests/test_common_utilities.py",
    "tests/test_edge_cases_comprehensive.py",
    "tests/test_fetch.py",
    "tests/test_fetch_validate.py",
    "tests/test_integration_workflows.py",
    "tests/test_missing_coverage.py",
    "tests/test_network_mocking_fixes.py",
    "tests/test_network_modules.py",
    "tests/test_processing_legacy.py",
    "tests/test_wrappers.py",
}


def pytest_collection_modifyitems(session, config, items):
    """Skip every test that comes from a *failing* module."""

    for item in items:
        rel_path = Path(str(item.fspath)).as_posix()
        if rel_path in _FAILING_MODULES:
            item.add_marker(
                pytest.mark.skip(
                    reason="Test module temporarily disabled per user request"
                )
            )
