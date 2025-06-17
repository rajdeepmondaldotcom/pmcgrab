import importlib.resources
from pathlib import Path

import lxml.etree as ET
import pytest

from pmcgrab.fetch import xml_tree_from_string, validate_xml

MIN_XML = (
    '<!DOCTYPE nlm-articleset PUBLIC "-//NLM//DTD ARTICLE SET 2.0//EN" '
    '"https://dtd.nlm.nih.gov/ncbi/pmc/articleset/nlm-articleset-2.0.dtd">'
    '<nlm-articleset><article></article></nlm-articleset>'
)


def test_validate_xml_finds_dtd(monkeypatch):
    captured = {}

    real_open = open

    def fake_open(path, *args, **kwargs):
        spath = str(path)
        if spath.endswith('nlm-articleset-2.0.dtd'):
            captured['path'] = spath
        return real_open(path, *args, **kwargs)

    class Dummy:
        def validate(self, tree):
            return True

    monkeypatch.setattr('builtins.open', fake_open)
    monkeypatch.setattr('lxml.etree.DTD', lambda f: Dummy())

    tree = xml_tree_from_string(MIN_XML)
    assert validate_xml(tree) is True
    dtd_path = Path(captured['path'])
    assert dtd_path.exists()
    assert dtd_path.name == 'nlm-articleset-2.0.dtd'
