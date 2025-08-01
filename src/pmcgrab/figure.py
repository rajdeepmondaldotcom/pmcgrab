"""Figure handling and metadata extraction for PMC articles.

This module provides the TextFigure class for parsing and representing
figure elements from PMC XML documents. It extracts available figure
metadata including labels, captions, and image references while handling
the limitations of PMC's relative link structure.

The module focuses on metadata extraction rather than image downloading
since PMC XML typically contains only relative links that may not be
publicly accessible without additional URL resolution.

Classes:
    TextFigure: Wrapper for PMC figure elements with metadata extraction
"""

import lxml.etree as ET

from pmcgrab.domain.value_objects import BasicBiMap


class TextFigure:
    """PMC figure element wrapper with metadata extraction and dictionary representation.

    Parses PMC XML figure elements to extract available metadata including
    figure labels, captions, and image link references. Provides a clean
    dictionary interface for accessing figure information without requiring
    direct XML manipulation.

    The class handles the common PMC figure structure including:
    * Figure labels (e.g., "Figure 1", "Fig. 2A")
    * Caption text with formatting preserved
    * Graphic link references (typically relative paths)

    Attributes:
        root (ET.Element): Original XML figure element
        parent (Optional[TextFigure]): Parent element for API compatibility
        ref_map (BasicBiMap): Reference map for cross-reference resolution
        fig_dict (dict): Dictionary containing extracted figure metadata with keys:
            - "Label": Figure label text (e.g., "Figure 1")
            - "Caption": Complete caption text
            - "Link": Image file reference (usually relative path)

    Examples:
        >>> # Parse figure from XML element
        >>> fig_element = root.xpath("//fig[@id='F1']")[0]
        >>> figure = TextFigure(fig_element)
        >>> print(figure.fig_dict["Label"])  # "Figure 1"
        >>> print(figure.fig_dict["Caption"][:100])  # First 100 chars
        >>>
        >>> # String representation shows complete metadata
        >>> print(str(figure))
        {'Label': 'Figure 1', 'Caption': 'Schematic diagram...', 'Link': 'figure1.jpg'}

    Note:
        PMC XML typically contains relative image paths that require additional
        URL resolution for public access. This class focuses on metadata
        extraction rather than image downloading.
    """

    def __init__(
        self,
        fig_root: ET.Element,
        parent: "TextFigure | None" = None,
        ref_map: BasicBiMap | None = None,
    ) -> None:
        """Initialize TextFigure from PMC XML figure element.

        Parses the provided figure XML element to extract label, caption,
        and image link information. Handles missing elements gracefully
        by setting corresponding dictionary values to None.

        Args:
            fig_root: XML figure element (<fig>) from PMC document
            parent: Parent figure element for API compatibility (unused)
            ref_map: Reference map for cross-reference resolution (optional)

        Note:
            This implementation intentionally does not download images since
            PMC XML typically contains only relative paths without stable
            public URLs. Image resolution is left to the caller if needed.
        """
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
        caption = (
            "".join(caption_el.itertext()).strip() if caption_el is not None else None
        )

        graphic_href: str | None = None
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
        """Return string representation of figure metadata dictionary.

        Returns:
            str: String representation of fig_dict containing Label, Caption, and Link
        """
        return str(self.fig_dict)

    def __repr__(self) -> str:
        """Return detailed representation of figure metadata dictionary.

        Returns:
            str: Detailed representation of fig_dict for debugging
        """
        return repr(self.fig_dict)
