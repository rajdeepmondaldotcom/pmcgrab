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
    """Collapse multi-line documentation strings into compact single-line format.

    Utility function for converting readable multi-line documentation strings
    in source code into compact single-line strings suitable for data
    dictionaries and inline documentation. Preserves content while removing
    formatting whitespace.

    Args:
        text: Multi-line documentation string with indentation and line breaks

    Returns:
        str: Compact single-line string with excess whitespace removed
             but content preserved

    Examples:
        >>> multiline_doc = '''
        ...     This is a long documentation string
        ...     that spans multiple lines with
        ...     proper indentation.
        ... '''
        >>> clean_doc(multiline_doc)
        'This is a long documentation string that spans multiple lines with proper indentation.'

    Note:
        This function is primarily used for creating field documentation
        in data dictionaries where readability in source code needs to
        be balanced with compact runtime representation.
    """
    # Collapse indentation, strip leading/trailing whitespace per line and
    # join everything into a **single** string with *no* newlines or excess
    # internal spaces.
    cleaned_lines = [ln.strip() for ln in cleandoc(text).splitlines()]
    # Remove empty lines and concatenate without extra spaces
    return "".join(filter(None, cleaned_lines))


def normalize_value(val: Any):
    """Recursively normalize data structures into JSON-serializable primitives.

    Converts complex Python objects into basic data types that can be
    safely serialized to JSON. Handles nested structures recursively
    to ensure complete normalization of arbitrarily complex data.

    Args:
        val: Any Python object to normalize

    Returns:
        JSON-serializable primitive: Normalized representation using only
                                   basic Python types (str, int, float, bool,
                                   list, dict, None)

    Transformations:
        * datetime objects → ISO-8601 strings
        * pandas DataFrame → list of record dictionaries
        * pandas Series → list of values
        * dict → recursively normalized dict
        * list → recursively normalized list
        * Other types → returned as-is (assumed JSON-safe)

    Examples:
        >>> import datetime
        >>> import pandas as pd
        >>>
        >>> # DateTime normalization
        >>> normalize_value(datetime.date(2023, 1, 15))
        '2023-01-15'
        >>>
        >>> # DataFrame normalization
        >>> df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        >>> normalize_value(df)
        [{'a': 1, 'b': 3}, {'a': 2, 'b': 4}]
        >>>
        >>> # Nested structure normalization
        >>> complex_data = {'date': datetime.date(2023, 1, 15), 'values': [1, 2, 3]}
        >>> normalize_value(complex_data)
        {'date': '2023-01-15', 'values': [1, 2, 3]}

    Note:
        This function is essential for ensuring Paper class data can be
        safely serialized to JSON for storage, API responses, and other
        downstream applications that require standard data types.
    """
    if isinstance(val, datetime.date | datetime.datetime):
        return val.isoformat()
    if isinstance(val, pd.DataFrame):
        return val.to_dict(orient="records")
    if isinstance(val, pd.Series):
        return val.to_list()
    if isinstance(val, dict):
        return {k: normalize_value(v) for k, v in val.items()}
    if isinstance(val, list):
        return [normalize_value(item) for item in val]
    return val
