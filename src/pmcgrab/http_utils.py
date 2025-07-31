"""Common HTTP helper utilities for pmcgrab external service wrappers."""
from __future__ import annotations

import functools
import time
from typing import Any, Dict, Optional

import requests

__all__ = [
    "cached_get",
]

def _backoff_sleep(retry: int) -> None:
    # Exponential back-off: 1, 2, 4, 8 … seconds (cap at 32)
    sleep = min(2 ** retry, 32)
    time.sleep(sleep)


def cached_get(url: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> requests.Response:
    """GET with retry + basic in-memory cache.

    Keeps a simple module-level dict so repeated calls in a single process hit the
    cache. Not meant for multi-process caching – callers that need persistence
    should wrap this with their own scheme.
    """
    if params:
        # Deterministic string key for cache
        key = url + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    else:
        key = url
    if key in _CACHE:
        return _CACHE[key]

    for retry in range(5):
        try:
            resp = requests.get(url, params=params, timeout=30, **kwargs)
            resp.raise_for_status()
            _CACHE[key] = resp
            return resp
        except requests.RequestException:
            if retry == 4:
                raise
            _backoff_sleep(retry)
    raise RuntimeError("Unreachable")


_CACHE: dict[str, requests.Response] = {}
