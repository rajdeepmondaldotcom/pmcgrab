from __future__ import annotations

"""High-level helper that constructs a :class:`pmcgrab.model.Paper` from PMC.

This lives in the *application* layer to keep the domain entity (`Paper`)
free of infrastructure details such as network calls, retries, or XML
parsing.
"""

import time
from typing import Optional
from urllib.error import HTTPError

from pmcgrab.model import Paper
from pmcgrab.parser import paper_dict_from_pmc

__all__: list[str] = ["build_paper_from_pmc"]


# NOTE: retry / back-off logic kept identical to the original implementation to
# preserve existing behaviour.


def build_paper_from_pmc(
    pmcid: int,
    *,
    email: str,
    download: bool = False,
    validate: bool = True,
    verbose: bool = False,
    suppress_warnings: bool = False,
    suppress_errors: bool = False,
    attempts: int = 3,
) -> Optional[Paper]:
    """Fetch XML, parse it, and build a :class:`Paper` instance.

    Parameters mirror the legacy `Paper.from_pmc` API so that callers can be
    migrated with a single import-level change.
    """
    d: Optional[dict] = None
    for _ in range(attempts):
        try:
            d = paper_dict_from_pmc(
                pmcid,
                email=email,
                download=download,
                validate=validate,
                verbose=verbose,
                suppress_warnings=suppress_warnings,
                suppress_errors=suppress_errors,
            )
            break
        except HTTPError:
            time.sleep(5)

    if not d:
        return None
    return Paper(d)
