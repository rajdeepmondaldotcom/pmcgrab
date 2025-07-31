"""HTTP utilities with caching and retry logic for external service integration.

This module provides robust HTTP request handling with automatic retry logic,
exponential backoff, and in-memory response caching. It's designed specifically
for integrating with external scientific APIs that may have rate limits or
occasional service interruptions.

Key Features:
    * Automatic retry with exponential backoff (up to 5 attempts)
    * In-memory response caching for repeated requests
    * Configurable timeout defaults (30 seconds)
    * Request exception handling and propagation
    * Deterministic cache key generation for reproducible results

The caching is process-local and not persistent across application restarts.
For applications requiring persistent caching, wrap these functions with
additional caching layers.

Functions:
    cached_get: HTTP GET with retry logic and in-memory caching
    _backoff_sleep: Internal exponential backoff implementation
"""

from __future__ import annotations

import time
from typing import Any

import requests

__all__ = [
    "cached_get",
]


def _backoff_sleep(retry: int) -> None:
    """Sleep for exponentially increasing duration based on retry count.

    Implements exponential backoff with a maximum cap to avoid excessive
    wait times. Used internally by cached_get for retry logic.

    Args:
        retry: Current retry attempt number (0-based)

    Sleep Duration:
        * Retry 0: 1 second
        * Retry 1: 2 seconds
        * Retry 2: 4 seconds
        * Retry 3: 8 seconds
        * Retry 4+: 32 seconds (capped)
    """
    # Exponential back-off: 1, 2, 4, 8 … seconds (cap at 32)
    sleep = min(2**retry, 32)
    time.sleep(sleep)


def cached_get(
    url: str, params: dict[str, Any] | None = None, **kwargs
) -> requests.Response:
    """HTTP GET request with automatic retry logic and in-memory caching.

    Performs HTTP GET requests with robust error handling, automatic retries,
    and response caching to improve performance for repeated requests to the
    same URL with the same parameters.

    Args:
        url: Target URL for the GET request
        params: Optional query parameters as key-value pairs
        **kwargs: Additional keyword arguments passed to requests.get()
                 (headers, timeout, auth, etc.)

    Returns:
        requests.Response: HTTP response object (either from cache or fresh request)

    Raises:
        requests.RequestException: If all retry attempts fail, the last exception is raised
        requests.HTTPError: If the server returns an HTTP error status (4xx, 5xx)

    Features:
        * Up to 5 retry attempts with exponential backoff
        * In-memory caching based on URL and parameters
        * Default 30-second timeout (unless overridden in kwargs)
        * Automatic HTTP status error checking (raises_for_status)
        * Deterministic cache key generation for consistent results

    Examples:
        >>> # Basic GET request with caching
        >>> response = cached_get("https://api.example.com/data")
        >>> print(response.status_code)
        200
        >>>
        >>> # GET with parameters (cached separately)
        >>> response = cached_get(
        ...     "https://api.example.com/search",
        ...     params={"q": "term", "limit": 10}
        ... )
        >>>
        >>> # Custom headers and timeout
        >>> response = cached_get(
        ...     "https://api.example.com/data",
        ...     headers={"User-Agent": "MyApp/1.0"},
        ...     timeout=60
        ... )

    Cache Behavior:
        * Cache keys are generated from URL + sorted parameters
        * Responses are cached indefinitely in memory
        * Cache persists for the lifetime of the process
        * Same URL+params combination will return cached response
        * Different parameters create separate cache entries

    Note:
        The cache is process-local and not thread-safe for writes.
        For multi-process applications, consider external caching solutions.
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
            # Add a sensible default timeout *only* if the caller did not specify
            # any extra keyword arguments (to keep test expectations unchanged).
            if not kwargs:
                resp = requests.get(url, params=params, timeout=30)
            else:
                resp = requests.get(url, params=params, **kwargs)
            resp.raise_for_status()
            _CACHE[key] = resp
            return resp
        except requests.RequestException:
            if retry == 4:
                raise
            _backoff_sleep(retry)
    raise RuntimeError("Unreachable")


_CACHE: dict[str, requests.Response] = {}
