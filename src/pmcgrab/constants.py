"""Constants, configuration, and exception definitions for PMCGrab.

This module centralizes all constant values, regular expressions, configuration
settings, and custom exception/warning classes used throughout the PMCGrab
package. It handles cross-platform compatibility issues and provides
standardized logging and warning configuration.

Key Components:
    * DTD validation constants and patterns
    * Custom exception classes for error handling
    * Warning classes for non-fatal issues
    * Cross-platform signal handling compatibility
    * Test email addresses for NCBI API access
    * Logging and warning format configuration

The module ensures consistent behavior across different operating systems,
particularly for signal handling differences between POSIX and Windows systems.
"""

import logging
import re
import signal
import warnings

logger = logging.getLogger(__name__)
warnings.formatwarning = (
    lambda msg, cat, *_args, **_kwargs: f"{cat.__name__}: {msg}\n\n"
)

SUPPORTED_DTD_URLS = [
    "https://dtd.nlm.nih.gov/ncbi/pmc/articleset/nlm-articleset-2.0.dtd"
]
DTD_URL_PATTERN = re.compile(r'"(https?://\S+)"')
END_OF_URL_PATTERN = re.compile(r"[^/]+$")


class NoDTDFoundError(Exception):
    """Raised when required DTD schema file cannot be found or loaded.

    This exception indicates that the XML document references a DTD
    (Document Type Definition) that is either unsupported by PMCGrab
    or cannot be located in the expected DTD file directory.
    """

    pass


class TimeoutException(Exception):
    """Raised when an operation exceeds its allocated time limit.

    Used in conjunction with signal.alarm() to implement timeouts
    for network requests and parsing operations that might hang
    indefinitely on problematic content or network issues.
    """

    pass


def timeout_handler(_signum, _frame):
    """Signal handler that raises TimeoutException on SIGALRM.

    This function is registered as the handler for SIGALRM signals
    to implement timeout functionality for long-running operations.
    When signal.alarm() triggers, this handler converts the signal
    into a Python exception that can be caught and handled.

    Args:
        _signum: Signal number (unused)
        _frame: Frame object (unused)

    Raises:
        TimeoutException: Always raised when called

    Note:
        This handler is only used on POSIX systems that support SIGALRM.
        Windows compatibility is handled separately below.
    """
    raise TimeoutException("Operation timed out")


# ---------------------------------------------------------------------------
# Optional POSIX-only SIGALRM registration
# Windows lacks SIGALRM; we fall back to a no-op placeholder so that test code
# referencing ``signal.SIGALRM`` still works cross-platform.
# ---------------------------------------------------------------------------
try:
    _sigalrm = signal.SIGALRM  # type: ignore[attr-defined]
    signal.signal(_sigalrm, timeout_handler)  # type: ignore[arg-type]
except (AttributeError, ValueError):
    # Provide a dummy attribute for compatibility (used only in unit tests).
    signal.SIGALRM = 0  # type: ignore[attr-defined]
    if not hasattr(signal, "alarm"):

        def _noop_alarm(_secs: int) -> None:
            """Dummy replacement for signal.alarm on non-POSIX systems."""
            return

        signal.alarm = _noop_alarm  # type: ignore[assignment]


# Email pool moved to pmcgrab.infrastructure.settings
# Kept for backwards compatibility -- imports redirect there
from pmcgrab.infrastructure.settings import EMAIL_POOL as EMAILS  # noqa: F401

email_counter = 0  # Deprecated: use infrastructure.settings.next_email() instead


class ReversedBiMapComparisonWarning(Warning):
    """Warning for deprecated or problematic bidirectional map comparison operations.

    Issued when code attempts to use bidirectional map features that may
    produce unexpected results or are deprecated in favor of better alternatives.
    """

    pass


class ValidationWarning(Warning):
    """Warning for XML validation issues that don't prevent parsing.

    Issued when PMC XML documents fail DTD validation but can still be
    processed. Indicates potential data quality issues that may affect
    parsing accuracy or completeness.
    """

    pass


class MultipleTitleWarning(Warning):
    """Warning when multiple article titles are found in PMC XML.

    Issued when an article contains multiple title elements, which may
    indicate structural issues in the XML or alternative title formats.
    PMCGrab uses the first title found.
    """

    pass


class UnhandledTextTagWarning(Warning):
    """Warning for XML tags that don't have specific handling logic.

    Issued when the parser encounters XML elements that aren't explicitly
    handled by the current parsing logic. Content may still be processed
    but formatting or structure could be lost.
    """

    pass


class ReadHTMLFailure(Warning):
    """Warning when HTML/XML reading or parsing operations fail.

    Issued when attempts to process HTML-like content within PMC XML
    fail due to malformed markup, encoding issues, or unsupported
    HTML constructs.
    """

    pass


class UnexpectedMultipleMatchWarning(Warning):
    """Warning when XPath queries return more results than expected.

    Issued when parsing operations find multiple elements where only
    one was expected. PMCGrab typically uses the first match but this
    may indicate structural variations in the XML.
    """

    pass


class UnexpectedZeroMatchWarning(Warning):
    """Warning when XPath queries return no results where content was expected.

    Issued when parsing operations fail to find expected elements in
    the PMC XML structure. May indicate missing metadata or structural
    differences between articles.
    """

    pass


class UnmatchedCitationWarning(Warning):
    """Warning for citation references that cannot be resolved.

    Issued when internal citation cross-references point to citation
    elements that don't exist or cannot be parsed properly. The
    reference may be preserved but without full bibliographic data.
    """

    pass


class UnmatchedTableWarning(Warning):
    """Warning for table references that cannot be resolved.

    Issued when internal table cross-references point to table elements
    that don't exist or cannot be parsed properly. The reference may
    be preserved but without structured table data.
    """

    pass


class UnexpectedTagWarning(Warning):
    """Warning for XML tags that appear in unexpected contexts.

    Issued when XML elements appear in locations where they're not
    typically expected according to PMC XML schema patterns. May
    indicate publisher-specific variations or evolving standards.
    """

    pass


class EmptyTextWarning(Warning):
    """Warning for text elements that are unexpectedly empty.

    Issued when elements that typically contain text content are found
    to be empty or contain only whitespace. May indicate incomplete
    content or structural issues in the source XML.
    """

    pass


class PubmedHTTPError(Warning):
    """Warning for HTTP-related errors when accessing PubMed/PMC services.

    Issued when network requests to NCBI services encounter HTTP errors,
    timeouts, or other connectivity issues. May be transient and suitable
    for retry attempts.
    """

    pass
