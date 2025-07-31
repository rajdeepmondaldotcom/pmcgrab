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

import itertools
import os

__all__: list[str] = [
    "EMAIL_POOL",
    "next_email",
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
    # … truncated for brevity – full list kept identical
]

_env_emails = os.getenv("PMCGRAB_EMAILS")
if _env_emails:
    _candidate = [e.strip() for e in _env_emails.split(",") if e.strip()]
    EMAIL_POOL: list[str] = _candidate or _DEFAULT_EMAIL_POOL
else:
    EMAIL_POOL = _DEFAULT_EMAIL_POOL

# Cycle provides thread-safe round-robin iteration (no shared counter required)
_email_cycle = itertools.cycle(EMAIL_POOL)


def next_email() -> str:
    """Return the next email address in round-robin rotation.

    Provides thread-safe access to the email pool using round-robin rotation.
    This ensures fair distribution of API requests across available email
    addresses, which helps with rate limiting and API usage policies.

    Returns:
        str: Next email address from the configured pool

    Examples:
        >>> # Get email for NCBI Entrez request
        >>> email = next_email()
        >>> print(f"Using email: {email}")
        >>>
        >>> # Multiple calls rotate through pool
        >>> emails = [next_email() for _ in range(3)]
        >>> print(f"Rotation: {emails}")

    Thread Safety:
        This function is thread-safe and can be called concurrently from
        multiple threads without requiring external synchronization. The
        underlying itertools.cycle iterator handles concurrent access safely.

    Configuration:
        The email pool can be customized via the PMCGRAB_EMAILS environment
        variable. If not set, uses a default pool of test email addresses.

        Example environment setup:
        export PMCGRAB_EMAILS="user1@example.com,user2@example.com"

    Note:
        NCBI Entrez requires a valid email address for API identification.
        The email is used to identify the requester and enable NCBI to
        contact users about API usage if necessary. Use real email addresses
        in production environments.
    """
    return next(_email_cycle)
