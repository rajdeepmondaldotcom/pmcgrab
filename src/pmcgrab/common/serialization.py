"""Serialization helpers – kept free of framework dependencies so they can be
used from *any* layer.
"""
from __future__ import annotations

import datetime
from inspect import cleandoc
from typing import Any

import pandas as pd

__all__: list[str] = [
    "clean_doc",
    "normalize_value",
]


def clean_doc(text: str) -> str:
    """Collapse indentation and strip newlines for inline docs.

    This is primarily syntactic sugar for keeping long documentation strings
    readable in the source while emitting a compact single-line string in the
    application.
    """
    return cleandoc(text).replace("\n", "")


def normalize_value(val: Any):  # noqa: ANN001 – *Any* is exactly what we want here
    """Recursively normalise data into JSON-serialisable primitives.

    * ``datetime`` objects → ISO-8601 strings.
    * ``pandas.DataFrame`` → list-of-dicts (records orientation).
    * ``dict`` / ``list`` – traverse children.
    """
    if isinstance(val, (datetime.date, datetime.datetime)):
        return val.isoformat()
    if isinstance(val, pd.DataFrame):
        return val.to_dict(orient="records")
    if isinstance(val, dict):
        return {k: normalize_value(v) for k, v in val.items()}
    if isinstance(val, list):
        return [normalize_value(item) for item in val]
    return val
