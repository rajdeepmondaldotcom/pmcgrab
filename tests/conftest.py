# Tests package -- conftest.py
"""Shared pytest configuration and fixtures for PMCGrab tests."""

import sys
import types


def _ensure_psutil_stub():
    """Install a minimal psutil stub if the real package is not available.

    This avoids requiring psutil as a test dependency while keeping tests
    that reference psutil.Process functional.
    """
    if "psutil" not in sys.modules:
        mock_psutil = types.ModuleType("psutil")

        class _Process:
            def __init__(self, _pid: int) -> None:
                self._pid = _pid

            def memory_info(self) -> object:
                class mem:
                    rss = 0

                return mem()

        mock_psutil.Process = _Process  # type: ignore[attr-defined]
        sys.modules["psutil"] = mock_psutil


_ensure_psutil_stub()
