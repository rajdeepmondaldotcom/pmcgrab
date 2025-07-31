import types
import lxml.etree as ET
import json
import pytest

import pmcgrab.oai as oai
import pmcgrab.oa_service as oa_service
import pmcgrab.bioc as bioc
import pmcgrab.idconvert as idconv
import pmcgrab.litctxp as litctxp
from pmcgrab import http_utils


class DummyResp:
    def __init__(self, text: str, content: bytes | None = None):
        self.text = text
        self.content = content if content is not None else text.encode()
    def raise_for_status(self):
        return


def test_oai_list_sets(monkeypatch):
    xml = """<OAI-PMH xmlns='http://www.openarchives.org/OAI/2.0/'>\n<ListSets>\n<set><setSpec>open</setSpec><setName>OA</setName></set>\n</ListSets></OAI-PMH>"""
    monkeypatch.setattr(http_utils, "cached_get", lambda *a, **kw: DummyResp(xml))
    sets = oai.list_sets()
    assert sets == [{"setSpec": "open", "setName": "OA"}]


def test_oa_fetch(monkeypatch):
    xml = """<records><record pmcid='PMC1'><link>file.pdf</link></record></records>"""
    monkeypatch.setattr(http_utils, "cached_get", lambda *a, **kw: DummyResp(xml))
    rec = oa_service.fetch("PMC1")
    assert rec["pmcid"] == "PMC1"
    assert rec["link"] == "file.pdf"


def test_bioc_fetch(monkeypatch):
    data = {"source": "pmc", "documents": []}
    monkeypatch.setattr(http_utils, "cached_get", lambda *a, **kw: DummyResp(json.dumps(data)))
    out = bioc.fetch_json("PMC1")
    assert out["source"] == "pmc"


def test_idconvert(monkeypatch):
    data = {"records": [{"pmcid": "PMC1", "pmid": "111"}]}
    monkeypatch.setattr(http_utils, "cached_get", lambda *a, **kw: DummyResp(json.dumps(data)))
    out = idconv.convert(["PMC1"])
    assert out["records"][0]["pmid"] == "111"


def test_litctxp(monkeypatch):
    monkeypatch.setattr(http_utils, "cached_get", lambda *a, **kw: DummyResp("MEDLINE DATA"))
    txt = litctxp.export("PMC1")
    assert "MEDLINE" in txt
