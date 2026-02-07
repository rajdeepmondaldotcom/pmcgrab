"""PMCGrab runtime configuration and settings management.

This module manages runtime configuration for PMCGrab, following the
12-factor app methodology by allowing configuration through environment
variables. This enables behavior modification without code changes,
supporting different deployment environments and user preferences.

The primary configuration managed here is the email pool used for NCBI
Entrez API authentication, which is required for accessing PMC content.
The system supports both default test emails and user-provided alternatives.

Key Features:
    * Environment variable configuration support
    * Thread-safe email rotation for concurrent processing
    * Fallback to default test emails
    * 12-factor app compliance for deployment flexibility

Environment Variables:
    PMCGRAB_EMAILS: Comma-separated list of email addresses for NCBI Entrez
                   Example: "user1@example.com,user2@example.com"

Default Behavior:
    If no environment override is provided, uses a pool of test email addresses
    that are rotated in round-robin fashion to distribute API requests.

Thread Safety:
    Email rotation uses itertools.cycle which provides thread-safe iteration
    without requiring locks or shared counters, making it suitable for
    concurrent processing scenarios.

Functions:
    next_email: Get next email address in round-robin rotation

Configuration:
    EMAIL_POOL: List of available email addresses for NCBI API access
"""

from __future__ import annotations

import os
import threading
import time

__all__: list[str] = [
    "EMAIL_POOL",
    "NCBI_API_KEY",
    "NCBI_TIMEOUT",
    "NCBI_RETRIES",
    "next_email",
    "rate_limit_wait",
]

# ---------------------------------------------------------------------------
# Email pool – used when querying NCBI Entrez
# ---------------------------------------------------------------------------

_DEFAULT_EMAIL_POOL: list[str] = [
    "bk68g1gx@test.com",
    "wkv1h06c@sample.com",
    "m42touro@sample.com",
    "vy8u7tsx@test.com",
    "8xsqaxke@sample.com",
    "cilml02q@sample.com",
    "1s1ywssv@demo.com",
    "pfd4bf0y@demo.com",
    "hvjhnv7o@test.com",
    "vtirmn0j@sample.com",
]

_env_emails = os.getenv("PMCGRAB_EMAILS")
if _env_emails:
    _candidate = [e.strip() for e in _env_emails.split(",") if e.strip()]
    EMAIL_POOL: list[str] = _candidate or _DEFAULT_EMAIL_POOL
else:
    EMAIL_POOL = _DEFAULT_EMAIL_POOL

# ---------------------------------------------------------------------------
# NCBI API key – allows 10 req/s instead of 3 req/s
# ---------------------------------------------------------------------------

NCBI_API_KEY: str | None = os.getenv("NCBI_API_KEY") or None

# ---------------------------------------------------------------------------
# Configurable timeouts and retries via env vars
# ---------------------------------------------------------------------------

NCBI_TIMEOUT: int = int(os.getenv("PMCGRAB_TIMEOUT", "60"))
NCBI_RETRIES: int = int(os.getenv("PMCGRAB_RETRIES", "3"))

# ---------------------------------------------------------------------------
# Thread-safe email rotation (with lock instead of bare itertools.cycle)
# ---------------------------------------------------------------------------

_email_lock = threading.Lock()
_email_index = 0


def next_email() -> str:
    """Return the next email address in round-robin rotation.

    Thread-safe via a lock-protected index counter.

    Returns:
        str: Next email address from the configured pool
    """
    global _email_index
    with _email_lock:
        email = EMAIL_POOL[_email_index % len(EMAIL_POOL)]
        _email_index += 1
    return email


# ---------------------------------------------------------------------------
# Token-bucket rate limiter for NCBI API
# ---------------------------------------------------------------------------


class _RateLimiter:
    """Simple token-bucket rate limiter.

    NCBI allows 3 requests/second without an API key and 10/second with one.
    This limiter enforces that ceiling across all threads.
    """

    def __init__(self, rate: float) -> None:
        self._min_interval = 1.0 / rate
        self._last_call = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_call = time.monotonic()


_rate = 10.0 if NCBI_API_KEY else 3.0
_limiter = _RateLimiter(_rate)


def rate_limit_wait() -> None:
    """Block until the next NCBI API call is allowed by the rate limiter."""
    _limiter.wait()
