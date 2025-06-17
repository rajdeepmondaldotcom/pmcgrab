import lxml.etree as ET
import datetime
from pmcgrab import parser
from pmcgrab.model import TextSection, TextParagraph

SAMPLE_XML = """<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE pmc-articleset SYSTEM 'https://dtd.nlm.nih.gov/ncbi/pmc/articleset/nlm-articleset-2.0.dtd'>
<pmc-articleset>
  <article>
    <front>
      <journal-meta>
        <journal-id journal-id-type='pmc'>journal123</journal-id>
        <journal-title>Test Journal</journal-title>
        <issn pub-type='epub'>1234-5678</issn>
        <publisher>
          <publisher-name>Test Publisher</publisher-name>
        </publisher>
      </journal-meta>
      <article-meta>
        <article-id pub-id-type='pmcid'>PMC12345</article-id>
        <title-group><article-title>Sample Article</article-title></title-group>
        <pub-date pub-type='ppub'>
          <year>2024</year><month>1</month><day>15</day>
        </pub-date>
        <volume>1</volume>
        <issue>2</issue>
        <permissions>
          <copyright-statement>Copyright 2024</copyright-statement>
          <license license-type='open-access'>
            <license-p>License text</license-p>
          </license>
        </permissions>
      </article-meta>
    </front>
    <abstract><p>Abstract text</p></abstract>
    <body>
      <sec><title>Intro</title><p>Body paragraph</p></sec>
    </body>
    <back>
      <fn-group><fn id='fn1'><p>Footnote</p></fn></fn-group>
    </back>
  </article>
</pmc-articleset>
"""

def fake_get_xml(*args, **kwargs):
    return ET.ElementTree(ET.fromstring(SAMPLE_XML.encode()))

def test_paper_dict_from_pmc(monkeypatch):
    monkeypatch.setattr(parser, "get_xml", fake_get_xml)
    d = parser.paper_dict_from_pmc(1, "test@example.com", validate=False)
    assert d["Title"] == "Sample Article"
    assert d["Journal Title"] == "Test Journal"
    assert d["Published Date"]["ppub"] == datetime.date(2024, 1, 15)
    assert d["Footnote"] == "Footnote"
    assert isinstance(d["Body"][0], TextSection)
    assert isinstance(d["Abstract"][0], TextParagraph)
