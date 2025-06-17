import lxml.etree as ET
import pytest

from pmcgrab.fetch import validate_xml
from pmcgrab.constants import NoDTDFoundError

SUPPORTED_DTD = "https://dtd.nlm.nih.gov/ncbi/pmc/articleset/nlm-articleset-2.0.dtd"

SIMPLE_XML = f"""<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE pmc-articleset SYSTEM '{SUPPORTED_DTD}'>
<pmc-articleset>
  <article></article>
</pmc-articleset>
"""

UNSUPPORTED_XML = """<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE something SYSTEM 'http://example.com/unsupported.dtd'>
<something></something>
"""

NO_DOCTYPE_XML = "<root/>"

class DummyDTD:
    def __init__(self, *args, **kwargs):
        pass

    def validate(self, tree):
        return False


def test_validate_xml_with_supported_dtd_returns_false(monkeypatch):
    monkeypatch.setattr(ET, "DTD", DummyDTD)
    tree = ET.ElementTree(ET.fromstring(SIMPLE_XML.encode()))
    assert validate_xml(tree) is False

def test_validate_xml_unsupported_dtd_raises_error():
    tree = ET.ElementTree(ET.fromstring(UNSUPPORTED_XML.encode()))
    with pytest.raises(NoDTDFoundError):
        validate_xml(tree)

def test_validate_xml_missing_doctype_raises_error():
    tree = ET.ElementTree(ET.fromstring(NO_DOCTYPE_XML.encode()))
    with pytest.raises(NoDTDFoundError):
        validate_xml(tree)
