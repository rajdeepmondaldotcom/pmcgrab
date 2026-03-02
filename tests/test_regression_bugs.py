"""Regression tests for parser bugs fixed in this release.

Each test class corresponds to one of the three reported issue categories:

1. PMC10576104 — consecutive self-closing <xref/> tags caused the regex in
   split_text_and_refs to capture a multi-element string as a single ref-map
   entry, which then raised lxml.etree.XMLSyntaxError inside
   process_reference_map.  The fix adds a negative lookbehind (``(?<!/)>``)
   to the paired-tag regex alternative so that self-closing tags no longer
   match as opening tags.

2. PMC10576104 (also) / PMC12590228 / PMC4643452 — when a paper has multiple
   <abstract> elements the parser always used nodes[0], which may be a typed
   variant (executive-summary, author-highlights, …) rather than the main text
   abstract.  The fix prefers the abstract without an abstract-type attribute.

3. PMC12590228 / PMC4643452 — <list> elements nested inside a <p> were passed
   verbatim through stringify_children and emerged as raw XML markup in the
   paragraph text.  The fix pre-processes the <p> element with
   _flatten_block_elements_in_paragraph before serialisation.
"""

import lxml.etree as ET
import pytest

from pmcgrab import parser
from pmcgrab.application.parsing.sections import gather_abstract
from pmcgrab.common.xml_processing import split_text_and_refs
from pmcgrab.constants import UnexpectedMultipleMatchWarning
from pmcgrab.domain.value_objects import BasicBiMap
from pmcgrab.model import TextParagraph, _flatten_block_elements_in_paragraph

# ---------------------------------------------------------------------------
# Helpers shared across tests
# ---------------------------------------------------------------------------


def _make_article(front_extra: str = "", body_extra: str = "") -> ET.Element:
    xml = f"""<article>
      <front>
        <article-meta>
          <article-id pub-id-type="pmcid">PMC99999</article-id>
          {front_extra}
        </article-meta>
      </front>
      <body>{body_extra}</body>
    </article>"""
    return ET.fromstring(xml.encode())


# ---------------------------------------------------------------------------
# Issue 1a: regex fix — consecutive self-closing xref tags
# ---------------------------------------------------------------------------


class TestSelfClosingXrefRegex:
    """Consecutive self-closing <xref/> must not be merged into one ref-map entry."""

    def test_single_selfclosing_xref_stored_correctly(self):
        ref_map = BasicBiMap()
        text = 'See <xref rid="r1" ref-type="bibr"/> for details.'
        split_text_and_refs(text, ref_map)
        assert len(ref_map) == 1
        assert ref_map[0] == '<xref rid="r1" ref-type="bibr"/>'
        # lxml must be able to round-trip the stored string
        root = ET.fromstring(ref_map[0])
        assert root.tag == "xref"
        assert root.get("rid") == "r1"

    def test_consecutive_selfclosing_xrefs_stored_separately(self):
        ref_map = BasicBiMap()
        text = (
            'Refs <xref rid="r4" ref-type="bibr"/>'
            '<xref rid="r5" ref-type="bibr"/>–'
            '<xref rid="r6" ref-type="bibr">6</xref> here.'
        )
        split_text_and_refs(text, ref_map)
        # Every stored string must be parseable as a single XML element
        for key, item in ref_map.items():
            root = ET.fromstring(item)  # must not raise XMLSyntaxError
            assert root.tag == "xref", f"ref_map[{key}] has unexpected tag: {root.tag}"

    def test_paired_xref_content_still_captured(self):
        ref_map = BasicBiMap()
        text = 'See <xref rid="r1" ref-type="bibr">Smith 2020</xref>.'
        result = split_text_and_refs(text, ref_map)
        assert "Smith 2020" in result
        assert len(ref_map) == 1
        root = ET.fromstring(ref_map[0])
        assert root.get("rid") == "r1"


# ---------------------------------------------------------------------------
# Issue 1b: defensive ET.fromstring in process_reference_map
# ---------------------------------------------------------------------------


class TestMalformedRefMapDefense:
    """process_reference_map must not crash when a ref-map entry is bad XML."""

    ARTICLE_XML = """<article>
      <front>
        <article-meta>
          <article-id pub-id-type="pmcid">PMC99998</article-id>
          <abstract><p>Abstract text here.</p></abstract>
        </article-meta>
      </front>
      <body>
        <sec>
          <title>Intro</title>
          <p>See refs <xref rid="r4" ref-type="bibr"/><xref rid="r5" ref-type="bibr"/>.</p>
        </sec>
      </body>
      <back>
        <ref-list>
          <ref id="r4"><mixed-citation>Author A 2020</mixed-citation></ref>
          <ref id="r5"><mixed-citation>Author B 2021</mixed-citation></ref>
        </ref-list>
      </back>
    </article>"""

    def test_no_exception_with_consecutive_selfclosing_xrefs(self, monkeypatch):
        tree = ET.ElementTree(ET.fromstring(self.ARTICLE_XML.encode()))
        monkeypatch.setattr(parser, "get_xml", lambda *a, **kw: tree)
        # Should not raise; the fix ensures each xref is stored as valid XML
        d = parser.paper_dict_from_pmc(99998, email="test@example.com", validate=False)
        assert d  # non-empty dict means parsing succeeded


# ---------------------------------------------------------------------------
# Issue 2: smart abstract selection — prefer untyped abstract
# ---------------------------------------------------------------------------


class TestSmartAbstractSelection:
    """gather_abstract must prefer the main (untyped) abstract over typed ones."""

    def _root_with_two_abstracts(
        self, typed_type: str, typed_content: str, main_content: str
    ) -> ET.Element:
        xml = f"""<article>
          <front>
            <article-meta>
              <abstract abstract-type="{typed_type}">
                <title>Highlights</title>
                <p>{typed_content}</p>
              </abstract>
              <abstract>
                <p>{main_content}</p>
              </abstract>
            </article-meta>
          </front>
        </article>"""
        return ET.fromstring(xml.encode())

    def test_prefers_untyped_over_executive_summary(self):
        root = self._root_with_two_abstracts(
            "executive-summary", "EXEC_CONTENT", "MAIN_CONTENT"
        )
        ref_map = BasicBiMap()
        with pytest.warns(UnexpectedMultipleMatchWarning):
            sections = gather_abstract(root, ref_map)
        assert sections is not None
        text = " ".join(str(s) for s in sections)
        assert "MAIN_CONTENT" in text
        assert "EXEC_CONTENT" not in text

    def test_prefers_untyped_over_author_highlights(self):
        root = self._root_with_two_abstracts(
            "author-highlights",
            "HIGHLIGHTS_CONTENT",
            "STRUCTURED_ABSTRACT",
        )
        ref_map = BasicBiMap()
        with pytest.warns(UnexpectedMultipleMatchWarning):
            sections = gather_abstract(root, ref_map)
        assert sections is not None
        text = " ".join(str(s) for s in sections)
        assert "STRUCTURED_ABSTRACT" in text
        assert "HIGHLIGHTS_CONTENT" not in text

    def test_falls_back_to_first_when_all_typed(self):
        xml = """<article>
          <front>
            <article-meta>
              <abstract abstract-type="graphical"><p>GRAPHICAL</p></abstract>
              <abstract abstract-type="toc"><p>TOC</p></abstract>
            </article-meta>
          </front>
        </article>"""
        root = ET.fromstring(xml.encode())
        ref_map = BasicBiMap()
        with pytest.warns(UnexpectedMultipleMatchWarning):
            sections = gather_abstract(root, ref_map)
        assert sections is not None
        text = " ".join(str(s) for s in sections)
        assert "GRAPHICAL" in text  # first element used as fallback

    def test_single_abstract_no_warning(self, recwarn):
        xml = """<article>
          <front>
            <article-meta>
              <abstract><p>ONLY_ABSTRACT</p></abstract>
            </article-meta>
          </front>
        </article>"""
        root = ET.fromstring(xml.encode())
        ref_map = BasicBiMap()
        sections = gather_abstract(root, ref_map)
        multi_warnings = [
            w
            for w in recwarn.list
            if issubclass(w.category, UnexpectedMultipleMatchWarning)
        ]
        assert not multi_warnings
        assert sections is not None


# ---------------------------------------------------------------------------
# Issue 3: block elements (<list>) nested inside <p>
# ---------------------------------------------------------------------------


class TestListInParagraph:
    """A <list> nested inside a <p> must not produce raw XML markup."""

    def _paragraph_with_inline_list(self, list_type: str = "simple") -> ET.Element:
        xml = f"""<p>Key findings:
          <list list-type="{list_type}">
            <list-item><label>•</label><p>Finding one.</p></list-item>
            <list-item><label>•</label><p>Finding two.</p></list-item>
          </list>
          End of paragraph.
        </p>"""
        return ET.fromstring(xml.encode())

    def test_no_raw_xml_in_paragraph_text(self):
        p_elem = self._paragraph_with_inline_list()
        para = TextParagraph(p_elem, ref_map=BasicBiMap())
        text = str(para)
        assert "<list" not in text
        assert "<list-item" not in text
        assert "<label>" not in text

    def test_list_item_content_preserved(self):
        p_elem = self._paragraph_with_inline_list()
        para = TextParagraph(p_elem, ref_map=BasicBiMap())
        text = str(para)
        assert "Finding one" in text
        assert "Finding two" in text

    def test_ordered_list_uses_numbers(self):
        xml = """<p>Steps:
          <list list-type="order">
            <list-item><p>Step A.</p></list-item>
            <list-item><p>Step B.</p></list-item>
          </list>
        </p>"""
        p_elem = ET.fromstring(xml.encode())
        para = TextParagraph(p_elem, ref_map=BasicBiMap())
        text = str(para)
        assert "1." in text
        assert "2." in text
        assert "Step A" in text

    def test_flatten_does_not_mutate_original(self):
        p_elem = self._paragraph_with_inline_list()
        original_xml = ET.tostring(p_elem, encoding="unicode")
        _flatten_block_elements_in_paragraph(p_elem)
        assert ET.tostring(p_elem, encoding="unicode") == original_xml

    def test_disp_formula_in_paragraph_no_raw_xml(self):
        xml = """<p>Consider <disp-formula><tex-math>x^2 + y^2 = r^2</tex-math></disp-formula> where x is real.</p>"""
        p_elem = ET.fromstring(xml.encode())
        para = TextParagraph(p_elem, ref_map=BasicBiMap())
        text = str(para)
        assert "<disp-formula" not in text
        assert "x^2 + y^2 = r^2" in text

    def test_paragraph_without_block_elements_unchanged(self):
        xml = """<p>Plain text with <bold>bold</bold> and numbers.</p>"""
        p_elem = ET.fromstring(xml.encode())
        para = TextParagraph(p_elem, ref_map=BasicBiMap())
        text = str(para)
        assert "Plain text with" in text
        assert "bold" in text


# ---------------------------------------------------------------------------
# Issue 2: _collect_sections handles <title> and block tags as direct children
# ---------------------------------------------------------------------------


class TestCollectSectionsBlockTags:
    """Block-level tags as direct children of <abstract>/<body> must not be dropped."""

    def test_title_as_direct_child_of_abstract_not_dropped(self):
        xml = """<article>
          <front>
            <article-meta>
              <abstract>
                <title>Executive Summary</title>
                <p>The main abstract content.</p>
              </abstract>
            </article-meta>
          </front>
        </article>"""
        root = ET.fromstring(xml.encode())
        ref_map = BasicBiMap()
        sections = gather_abstract(root, ref_map)
        assert sections is not None
        texts = [str(s) for s in sections]
        # Both the title text and paragraph text should be present
        combined = " ".join(texts)
        assert "Executive Summary" in combined
        assert "main abstract content" in combined

    def test_list_as_direct_child_of_abstract(self):
        xml = """<article>
          <front>
            <article-meta>
              <abstract>
                <list list-type="bullet">
                  <list-item><p>Item one.</p></list-item>
                  <list-item><p>Item two.</p></list-item>
                </list>
              </abstract>
            </article-meta>
          </front>
        </article>"""
        root = ET.fromstring(xml.encode())
        ref_map = BasicBiMap()
        sections = gather_abstract(root, ref_map)
        assert sections is not None
        combined = " ".join(str(s) for s in sections)
        assert "<list" not in combined
        assert "Item one" in combined
        assert "Item two" in combined

    def test_disp_formula_as_direct_child_of_abstract(self):
        xml = """<article>
          <front>
            <article-meta>
              <abstract>
                <p>We define the variable as follows.</p>
                <disp-formula>
                  <tex-math>E = mc^2</tex-math>
                </disp-formula>
              </abstract>
            </article-meta>
          </front>
        </article>"""
        root = ET.fromstring(xml.encode())
        ref_map = BasicBiMap()
        sections = gather_abstract(root, ref_map)
        assert sections is not None
        combined = " ".join(str(s) for s in sections)
        assert "<disp-formula" not in combined
        assert "E = mc^2" in combined
