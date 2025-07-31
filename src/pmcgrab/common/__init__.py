"""Common helper modules that live *outside* the domain layer but have no
external I/O dependencies.  They are pure functions that can be reused across
application or infrastructure code.

The sub-modules are intentionally small and focused:

• **serialization** – generic data normalisation helpers.
• **html_cleaning** – safe HTML / XML tag removal & substitution.
• **xml_processing** – XML/HTML text extraction and reference handling.
"""

from pmcgrab.common.html_cleaning import remove_html_tags, strip_html_text_styling
from pmcgrab.common.serialization import clean_doc, normalize_value
from pmcgrab.common.xml_processing import (
    generate_typed_mhtml_tag,
    remove_mhtml_tags,
    split_text_and_refs,
    stringify_children,
)

__all__: list[str] = [
    "clean_doc",
    "generate_typed_mhtml_tag",
    "normalize_value",
    "remove_html_tags",
    "remove_mhtml_tags",
    "split_text_and_refs",
    "stringify_children",
    "strip_html_text_styling",
]
