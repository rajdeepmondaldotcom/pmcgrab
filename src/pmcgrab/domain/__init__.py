"""pmcgrab.domain

This package contains *pure* business-domain models and value objects. Nothing
inside this package should perform network requests, file I/O, or depend on
external frameworks. Keeping the domain layer free of side-effects ensures that
it remains easily testable and reusable.
"""

from pmcgrab.domain.value_objects import BasicBiMap

__all__: list[str] = [
    "BasicBiMap",
]
