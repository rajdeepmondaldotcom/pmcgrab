import json

import lxml.etree as ET
import numpy as np
import pandas as pd

from pmcgrab.common.serialization import normalize_value
from pmcgrab.model import Paper, TextSection


def _section(xml: str) -> TextSection:
    return TextSection(ET.fromstring(xml))


def test_paper_to_dict_emits_canonical_v2_schema():
    paper = Paper(
        {
            "PMCID": 12345,
            "Title": "Structured Output",
            "Subtitle": "A schema test",
            "Article ID": {
                "pmcid": "PMC12345",
                "pmid": "999",
                "doi": "10.1234/example",
                "publisher-id": "pub-1",
            },
            "Authors": pd.DataFrame([{"First_Name": "Ada", "Last_Name": "Lovelace"}]),
            "Abstract": [_section("<sec><p>Abstract text.</p></sec>")],
            "Body": [
                _section(
                    """
                    <sec id="s1">
                      <title>Methods</title>
                      <p>Method paragraph.</p>
                      <sec id="s1-1">
                        <title>Nested</title>
                        <p>Nested paragraph.</p>
                      </sec>
                      <table-wrap id="t1">
                        <label>Table 1</label>
                        <caption><p>Table caption.</p></caption>
                        <table>
                          <thead><tr><th>A</th></tr></thead>
                          <tbody><tr><td>1</td></tr></tbody>
                        </table>
                      </table-wrap>
                      <fig id="f1">
                        <label>Figure 1</label>
                        <caption><p>Figure caption.</p></caption>
                      </fig>
                    </sec>
                    """
                )
            ],
            "Journal Title": "Schema Journal",
            "Publisher Name": ["Primary Publisher", "Alt Publisher"],
            "Publisher Location": ["New York", "London"],
            "Published Date": {},
            "Citations": [{"title": "Reference"}],
            "Tables": [],
            "Figures": [],
        }
    )

    data = paper.to_dict()

    assert data["schema_version"] == 2
    assert data["identifiers"] == {
        "pmc_id": "12345",
        "pmcid": "PMC12345",
        "pmid": "999",
        "doi": "10.1234/example",
        "publisher_id": "pub-1",
        "other": {},
    }
    assert data["title"] == {
        "main": "Structured Output",
        "subtitle": "A schema test",
        "translated": [],
    }
    assert data["publication"]["journal"]["title"] == "Schema Journal"
    assert data["publication"]["publisher"]["name"] == "Primary Publisher"
    assert data["publication"]["publisher"]["alternate_names"] == ["Alt Publisher"]
    assert data["publication"]["publisher"]["location"] == "New York"
    assert data["publication"]["publisher"]["alternate_locations"] == ["London"]
    assert data["contributors"]["authors"] == [
        {"First_Name": "Ada", "Last_Name": "Lovelace"}
    ]

    removed_duplicate_keys = {
        "pmc_id",
        "article_id",
        "abstract",
        "abstract_text",
        "body",
        "body_nested",
        "paragraphs",
        "full_text",
        "journal_title",
    }
    assert removed_duplicate_keys.isdisjoint(data)

    section = data["content"]["sections"][0]
    assert section["title"] == "Methods"
    assert section["children"][0]["title"] == "Nested"
    assert section["blocks"][0] == {
        "type": "paragraph",
        "id": "",
        "text": "Method paragraph.",
    }
    assert {"type": "table_ref", "id": "t1"} in section["blocks"]
    assert {"type": "figure_ref", "id": "f1"} in section["blocks"]
    assert data["assets"]["tables"][0]["id"] == "t1"
    assert data["assets"]["figures"][0]["id"] == "f1"

    json.dumps(data)


def test_paper_output_is_strict_json_with_missing_dataframe_values():
    paper = Paper(
        {
            "PMCID": 12345,
            "Title": "Strict JSON",
            "Authors": pd.DataFrame(
                [
                    {
                        "First_Name": "Ada",
                        "Email_Address": np.nan,
                        "ORCID": pd.NA,
                        "Score": np.inf,
                    }
                ]
            ),
            "Body": [_section("<sec><title>Methods</title><p>Text.</p></sec>")],
            "Tables": [
                pd.DataFrame(
                    [
                        {
                            "value": np.float64("nan"),
                            "date": np.datetime64("NaT"),
                        }
                    ]
                )
            ],
        }
    )

    data = paper.to_dict()

    author = data["contributors"]["authors"][0]
    assert author["Email_Address"] is None
    assert author["ORCID"] is None
    assert author["Score"] is None
    assert data["assets"]["tables"][0]["records"][0]["value"] is None
    assert data["assets"]["tables"][0]["records"][0]["date"] is None
    json.dumps(data, allow_nan=False)
    json.dumps(json.loads(paper.to_json()), allow_nan=False)


def test_normalize_value_converts_non_finite_scalars_to_none():
    data = normalize_value(
        {
            "nan": float("nan"),
            "inf": float("inf"),
            "np_nan": np.float64("nan"),
            "pd_na": pd.NA,
            "pd_nat": pd.NaT,
            "nested": [1, -np.inf],
        }
    )

    assert data == {
        "nan": None,
        "inf": None,
        "np_nan": None,
        "pd_na": None,
        "pd_nat": None,
        "nested": [1, None],
    }


def test_body_assets_are_not_duplicated_by_flat_asset_lists():
    body = _section(
        """
        <sec id="s1">
          <title>Results</title>
          <table-wrap id="t1">
            <label>Table 1</label>
            <caption><p>Table caption.</p></caption>
            <table><tbody><tr><td>1</td></tr></tbody></table>
          </table-wrap>
          <fig id="f1">
            <label>Figure 1</label>
            <caption><p>Figure caption.</p></caption>
          </fig>
        </sec>
        """
    )
    table = next(
        child for child in body.children if child.__class__.__name__ == "TextTable"
    )
    figure = next(
        child for child in body.children if child.__class__.__name__ == "TextFigure"
    )
    paper = Paper(
        {
            "PMCID": 12345,
            "Title": "No duplicate assets",
            "Body": [body],
            "Tables": [table.df],
            "Figures": [figure.fig_dict],
        }
    )

    data = paper.to_dict()

    assert data["content"]["sections"][0]["blocks"] == [
        {"type": "table_ref", "id": "t1"},
        {"type": "figure_ref", "id": "f1"},
    ]
    assert [table["id"] for table in data["assets"]["tables"]] == ["t1"]
    assert [figure["id"] for figure in data["assets"]["figures"]] == ["f1"]


def test_empty_paper_uses_full_schema_defaults():
    data = Paper({}).to_dict()

    assert data["identifiers"] == {
        "pmc_id": "",
        "pmcid": "",
        "pmid": "",
        "doi": "",
        "publisher_id": "",
        "other": {},
    }
    assert data["content"]["abstract"] == []
    assert data["content"]["sections"] == []


def test_figure_links_are_primary_plus_alternates_without_duplication():
    figure_xml = """
    <fig id="f1">
      <label>Figure 1</label>
      <caption><p>Figure caption.</p></caption>
      <graphic xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="main.png"/>
      <alternatives>
        <graphic xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="alt.png"/>
      </alternatives>
    </fig>
    """
    body = _section(f"<sec><title>Results</title>{figure_xml}</sec>")
    paper = Paper({"PMCID": 12345, "Title": "Figure links", "Body": [body]})

    figure = paper.to_dict()["assets"]["figures"][0]

    assert figure["link"] == "main.png"
    assert figure["alternate_links"] == ["alt.png"]
    assert "graphics" not in figure
