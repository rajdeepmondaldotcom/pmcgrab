"""Utility functions and data dictionaries for PMCGrab Paper class.

This module provides utility functions and documentation data structures
used by the Paper class and other components. It centralizes field
documentation and provides helpers for data dictionary creation.

The main purpose is to maintain comprehensive documentation for all
Paper class attributes in a single location, making it easy to understand
what each field contains and how it should be used.

Key Functions:
    define_data_dict: Returns comprehensive documentation for Paper fields

Note:
    Some utility functions (clean_doc, normalize_value) are imported from
    the common.serialization module to avoid circular dependencies.
"""

# clean_doc is imported from common.serialization below


# normalize_value is imported from common.serialization below

from pmcgrab.common.serialization import clean_doc


def define_data_dict() -> dict[str, str]:
    """Return comprehensive documentation dictionary for Paper class fields.

    Creates a mapping from Paper attribute names to human-readable
    documentation strings explaining what each field contains and
    how it should be interpreted. This serves as the definitive
    reference for Paper class field semantics.

    Returns:
        dict[str, str]: Dictionary mapping field names to documentation strings.
                       Each string explains the field's purpose, data type,
                       and usage patterns.

    Examples:
        >>> data_dict = define_data_dict()
        >>> print(data_dict['Title'])
        Title of the PMC article.
        >>> print(data_dict['Authors'])
        DataFrame of PMC Authors including names, emails, and affiliations.

    Note:
        This function is used internally by the Paper class to populate
        the data_dict attribute, providing self-documenting capabilities
        for Paper instances.
    """
    return {
        "PMCID": "PMCID of the PMC article. Unique.",
        "Title": "Title of the PMC article.",
        "Authors": clean_doc(
            "DataFrame of PMC Authors including names, emails, and affiliations."
        ),
        "Non-Author Contributors": clean_doc(
            "DataFrame of non-author contributors with names, emails, and affiliations."
        ),
        "Abstract": clean_doc(
            "List of TextSections parsed from the abstract. Use Paper.abstract_as_str() for a simple view."
        ),
        "Body": clean_doc(
            "List of TextSections parsed from the body. Use Paper.body_as_str() for a simple view."
        ),
        "Journal ID": clean_doc(
            "Dict of journal ID types and values (e.g. NLM-TA, ISO-ABBREV)."
        ),
        "Journal Title": "Journal title in text.",
        "ISSN": "Dict of ISSN types and values.",
        "Publisher Name": "Name of the publisher.",
        "Publisher Location": "Location of the publisher.",
        "Article ID": clean_doc(
            "Dict of article ID types and values. e.g., p.article_id['pmc'] returns the PMCID."
        ),
        "Article Types": "List of header article types.",
        "Article Categories": "List of non-header article types.",
        "Keywords": "Keywords or subject terms for the article. Strings or grouped dicts.",
        "Published Date": clean_doc(
            "Dict of publication dates (e.g., electronic, print)."
        ),
        "History Dates": clean_doc(
            "Dict of manuscript history dates (received, accepted, revised, etc.)."
        ),
        "Volume": clean_doc("Volume number."),
        "Issue": clean_doc("Issue number."),
        "FPage": "First page of publication.",
        "LPage": "Last page of publication.",
        "First Page": "First page of publication (alias).",
        "Last Page": "Last page of publication (alias).",
        "Permissions": clean_doc(
            "Summary of copyright, license type, and full license text."
        ),
        "Copyright Statement": clean_doc(
            "Copyright statement, typically a short phrase."
        ),
        "License": clean_doc("License type (e.g., Open Access)."),
        "Funding": clean_doc("List of funding groups, important for bias detection."),
        "Ethics": clean_doc(
            "Dict of ethics / disclosure statements (conflicts, ethics statement, trial registration, etc.)."
        ),
        "Footnote": "Text of any footnotes provided with the article.",
        "Acknowledgements": clean_doc("List of acknowledgement statements."),
        "Notes": "List of notes included with the article.",
        "Custom Meta": clean_doc("Dict of custom metadata key/value pairs."),
        "Citations": "List of parsed citation dictionaries or strings.",
        "Tables": "List of pandas DataFrame objects parsed from tables.",
        "Figures": "List of figure metadata dictionaries (Label, Caption, Link).",
        "Supplementary Material": "List of supplementary-material/media objects with Label, Caption, Href.",
        "Equations": "List of MathML equation strings present in the article.",
        "Ref Map": clean_doc(
            "Dict mapping reference indices to reference data for linking text with citations, tables, etc."
        ),
    }
