import lxml.etree as ET
from typing import Optional

from pmcgrab.utils import BasicBiMap


class TextFigure:
    """Wrapper for a figure element providing easy access to its metadata.

    Currently PMC XML provides only relative links to figure images that are
    not guaranteed to be publicly accessible. Therefore the class focuses on
    capturing the information that *is* available – label, caption and the
    relative link reference – and makes it available in a convenient
    dictionary form via the ``fig_dict`` attribute.
    """

    def __init__(
        self,
        fig_root: ET.Element,
        parent: Optional["TextFigure"] = None,
        ref_map: Optional[BasicBiMap] = None,
    ) -> None:
        # The figure class is intentionally light-weight; we do not currently
        # attempt to download the underlying image as the PMC archive does not
        # expose a stable public URL in the XML. The caller can decide how to
        # resolve the link if required.
        self.root = fig_root
        self.parent = parent  # for API compatibility with TextElement-like classes
        self.ref_map = ref_map if ref_map is not None else BasicBiMap()

        label_el = fig_root.find(".//label")
        caption_el = fig_root.find(".//caption")
        graphic_el = fig_root.find(".//graphic")

        label = label_el.text if label_el is not None else None
        caption = ("".join(caption_el.itertext()).strip() if caption_el is not None else None)

        graphic_href: Optional[str] = None
        if graphic_el is not None:
            # The graphic xlink:href attribute is namespaced. Using the explicit
            # namespace avoids issues if the default xlink prefix is missing.
            graphic_href = graphic_el.get("{http://www.w3.org/1999/xlink}href")

        self.fig_dict = {
            "Label": label,
            "Caption": caption,
            "Link": graphic_href,
        }

    # String / repr helpers -------------------------------------------------
    def __str__(self) -> str:
        return str(self.fig_dict)

    def __repr__(self) -> str:
        return repr(self.fig_dict)
