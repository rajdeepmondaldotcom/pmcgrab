from types import SimpleNamespace
from unittest.mock import patch

from pmcgrab import idconvert


def test_convert_uses_current_ncbi_id_converter_endpoint():
    with patch("pmcgrab.idconvert.cached_get") as mock_get:
        mock_get.return_value = SimpleNamespace(
            text='{"status":"ok","records":[{"pmcid":"PMC7181753"}]}'
        )

        result = idconvert.convert(["10.1038/s42003-020-0922-4"])

    assert result["records"][0]["pmcid"] == "PMC7181753"
    url = mock_get.call_args.args[0]
    params = mock_get.call_args.kwargs["params"]
    assert url == "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/"
    assert params == {
        "ids": "10.1038/s42003-020-0922-4",
        "format": "json",
        "tool": "pmcgrab",
        "idtype": "doi",
    }


def test_convert_handles_mixed_identifier_types():
    def fake_get(_url, *, params, **_kwargs):
        ids = params["ids"]
        idtype = params["idtype"]
        if ids == "PMC7181753" and idtype == "pmcid":
            text = '{"records":[{"requested-id":"PMC7181753","pmcid":"PMC7181753"}]}'
        elif ids == "10.1038/s42003-020-0922-4" and idtype == "doi":
            text = '{"records":[{"requested-id":"10.1038/s42003-020-0922-4","pmcid":"PMC7181753"}]}'
        elif ids == "32327715" and idtype == "pmcid":
            text = '{"records":[{"requested-id":"32327715","status":"error"}]}'
        elif ids == "32327715" and idtype == "pmid":
            text = '{"records":[{"requested-id":"32327715","pmcid":"PMC7181753"}]}'
        else:  # pragma: no cover - makes unexpected API calls obvious
            raise AssertionError(params)
        return SimpleNamespace(text=text)

    with patch("pmcgrab.idconvert.cached_get", side_effect=fake_get):
        result = idconvert.convert(
            ["PMC7181753", "32327715", "10.1038/s42003-020-0922-4"]
        )

    assert [record["requested-id"] for record in result["records"]] == [
        "PMC7181753",
        "32327715",
        "10.1038/s42003-020-0922-4",
    ]
    assert [record["pmcid"] for record in result["records"]] == [
        "PMC7181753",
        "PMC7181753",
        "PMC7181753",
    ]


def test_normalize_doi_uses_converter_response():
    with patch("pmcgrab.idconvert.convert") as mock_convert:
        mock_convert.return_value = {
            "status": "ok",
            "records": [{"pmcid": "PMC7181753"}],
        }

        assert idconvert.normalize_id("10.1038/s42003-020-0922-4") == "7181753"

    mock_convert.assert_called_once_with(["10.1038/s42003-020-0922-4"])


def test_normalize_pmid_uses_converter_response():
    with patch("pmcgrab.idconvert.convert") as mock_convert:
        mock_convert.return_value = {
            "status": "ok",
            "records": [{"pmcid": "PMC7578824"}],
        }

        assert idconvert.normalize_pmid("33087749") == "7578824"

    mock_convert.assert_called_once_with(["33087749"])
