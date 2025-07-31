"""pmcgrab.domain.value_objects

Value objects and small helper types that belong to the *inner* domain layer.
Everything here is pure Python with no external I/O so that the business logic
remains framework-agnostic and trivially unit-testable.
"""

from __future__ import annotations

import warnings
from collections.abc import Hashable
from typing import Any

from pmcgrab.constants import ReversedBiMapComparisonWarning

__all__: list[str] = [
    "BasicBiMap",
    "make_hashable",
]


def make_hashable(value: Any) -> Hashable:
    """Return a hashable representation of *value*.

    Nested lists and dictionaries are converted into tuples so that the result
    can be used as a key in a dictionary or set. The transformation is
    deterministic and therefore safe for memoisation or caching.
    """
    if isinstance(value, dict):
        return tuple(sorted((k, make_hashable(v)) for k, v in value.items()))
    if isinstance(value, list):
        return tuple(make_hashable(item) for item in value)
    return value


class BasicBiMap(dict[Hashable, Any]):
    """A minimal bi-directional map.

    The class keeps *both* forward and reverse dictionaries so that look-ups in
    either direction are **O(1)**.  It purposefully stays lightweight and does
    not attempt to be fully feature-complete compared to a dedicated library
    such as `bidict` - we only implement what is required by the pmcgrab
    code-base.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # -- __init__
        super().__init__(*args, **kwargs)
        self.reverse: dict[Hashable, Hashable] = {
            make_hashable(v): k for k, v in self.items()
        }

    # ------------------------------------------------------------------
    # dict API overrides
    # ------------------------------------------------------------------
    def __setitem__(self, key: Hashable, value: Any) -> None:  # type: ignore[override]
        # Remove old reverse mapping if key already exists
        if key in self:
            old_value = self.get(key)
            old_hash = make_hashable(old_value)
            if old_hash in self.reverse:
                del self.reverse[old_hash]
        super().__setitem__(key, value)
        # Update reverse mapping – latest key wins if duplicate values occur
        self.reverse[make_hashable(value)] = key

    # ------------------------------------------------------------------
    # Equality semantics
    # ------------------------------------------------------------------
    def __eq__(self, other: object) -> bool:  # type: ignore[override]
        if not isinstance(other, dict):
            return False
        if not super().__eq__(other):
            # Special-case: *reverse* comparison - useful in tests
            if isinstance(other, BasicBiMap) and other.reverse == dict(self):
                warnings.warn(
                    "BasicBiMap reversed key/value equivalence.",
                    ReversedBiMapComparisonWarning,
                    stacklevel=2,
                )
                return True
            return False
        return True
