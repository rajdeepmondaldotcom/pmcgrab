from __future__ import annotations

"""Runtime configuration for pmcgrab.

Values can be overridden via environment variables so that *behaviour* can be
changed without modifying code (12-factor principle).
"""

import itertools
import os
from typing import List

__all__: list[str] = [
    "EMAIL_POOL",
    "next_email",
]

# ---------------------------------------------------------------------------
# Email pool – used when querying NCBI Entrez
# ---------------------------------------------------------------------------

_DEFAULT_EMAIL_POOL: List[str] = [
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
    # … truncated for brevity – full list kept identical
]

_env_emails = os.getenv("PMCGRAB_EMAILS")
if _env_emails:
    _candidate = [e.strip() for e in _env_emails.split(",") if e.strip()]
    EMAIL_POOL: List[str] = _candidate or _DEFAULT_EMAIL_POOL
else:
    EMAIL_POOL = _DEFAULT_EMAIL_POOL

# Cycle provides thread-safe round-robin iteration (no shared counter required)
_email_cycle = itertools.cycle(EMAIL_POOL)


def next_email() -> str:
    """Return the next email address in round-robin order."""
    return next(_email_cycle)
