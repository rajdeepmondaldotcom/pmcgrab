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

    data = paper.to_dict(schema_version=2)

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

    data = paper.to_dict(schema_version=2)

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

    data = paper.to_dict(schema_version=2)

    assert data["content"]["sections"][0]["blocks"] == [
        {"type": "table_ref", "id": "t1"},
        {"type": "figure_ref", "id": "f1"},
    ]
    assert [table["id"] for table in data["assets"]["tables"]] == ["t1"]
    assert [figure["id"] for figure in data["assets"]["figures"]] == ["f1"]


def test_empty_paper_uses_full_schema_defaults():
    data = Paper({}).to_dict()

    assert data["schema_version"] == 4
    assert data["article"]["identifiers"] == {
        "pmc_id": "",
        "pmcid": "",
        "pmid": "",
        "doi": "",
        "publisher_id": "",
        "other": {},
        "all": [],
    }
    assert data["content"]["abstracts"] == []
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


def test_v2_schema_remains_available():
    data = Paper({}).to_dict(schema_version=2)

    assert data["schema_version"] == 2
    assert data["identifiers"]["pmcid"] == ""
    assert data["content"]["abstract"] == []


def test_v3_preserves_full_references_links_and_date_precision():
    from pmcgrab.parser import build_complete_paper_dict

    xml = """
    <article>
      <front>
        <journal-meta><journal-title>Journal</journal-title></journal-meta>
        <article-meta>
          <article-id pub-id-type="pmcid">PMC12345</article-id>
          <title-group><article-title>V3 Fidelity</article-title></title-group>
          <abstract abstract-type="author-highlights"><p>Highlight text.</p></abstract>
          <abstract><p>See <xref ref-type="bibr" rid="r1">1</xref>.</p></abstract>
          <trans-abstract xml:lang="es"><p>Resumen traducido.</p></trans-abstract>
          <pub-date pub-type="epub"><year>2024</year><month>5</month></pub-date>
        </article-meta>
      </front>
      <body>
        <sec id="s1">
          <title>Results</title>
          <p>Body cites <xref ref-type="bibr" rid="r1">1</xref> and
          <xref ref-type="fig" rid="f1">Fig. 1</xref>.</p>
          <fig id="f1"><label>Figure 1</label><caption><p>Caption.</p></caption></fig>
        </sec>
      </body>
      <back>
        <ref-list>
          <ref id="r1"><element-citation><article-title>Cited</article-title></element-citation></ref>
          <ref id="r2"><element-citation><article-title>Uncited</article-title></element-citation></ref>
        </ref-list>
      </back>
    </article>
    """
    legacy = build_complete_paper_dict(12345, ET.fromstring(xml.encode()))
    data = Paper(legacy).to_dict(schema_version=3)

    assert data["schema_version"] == 3
    assert [abstract["kind"] for abstract in data["content"]["abstracts"]] == [
        "author-highlights",
        "primary",
        "translated",
    ]
    assert data["content"]["primary_abstract"]["kind"] == "primary"
    assert data["article"]["publication"]["dates"]["published"]["epub"] == {
        "raw": "2024 5",
        "date": "2024-05",
        "precision": "month",
        "year": "2024",
        "month": "5",
        "day": "",
    }
    assert [ref["id"] for ref in data["assets"]["references"]] == ["r1", "r2"]
    assert [link["type"] for link in data["links"]] == [
        "citation",
        "citation",
        "figure",
    ]
    assert all(link["resolved"] for link in data["links"])


def test_v4_emits_canonical_records_sources_relations_and_quality():
    from pmcgrab.parser import build_complete_paper_dict

    xml = """
    <article xmlns:xlink="http://www.w3.org/1999/xlink">
      <front>
        <journal-meta><journal-title>Journal</journal-title></journal-meta>
        <article-meta>
          <article-id pub-id-type="pmcid">PMC12345</article-id>
          <article-id pub-id-type="doi">10.1234/v4</article-id>
          <article-categories>
            <subj-group subj-group-type="heading"><subject>Research Article</subject></subj-group>
          </article-categories>
          <title-group><article-title>V4 Canonical</article-title></title-group>
          <contrib-group>
            <contrib contrib-type="author" id="c1" corresp="yes">
              <name><surname>Lovelace</surname><given-names>Ada</given-names></name>
              <contrib-id contrib-id-type="orcid">0000-0000-0000-0001</contrib-id>
              <xref ref-type="aff" rid="aff1">1</xref>
            </contrib>
            <aff id="aff1"><institution>Analytical Engines Lab</institution><country>UK</country></aff>
          </contrib-group>
          <kwd-group><kwd>json</kwd><kwd>jats</kwd></kwd-group>
          <counts><ref-count count="1"/><fig-count count="1"/></counts>
          <permissions>
            <license license-type="cc-by" xlink:href="https://creativecommons.org/licenses/by/4.0/">
              <license-p>Creative Commons Attribution.</license-p>
            </license>
          </permissions>
          <abstract><p id="ap1">Abstract cites <xref ref-type="bibr" rid="r1">1</xref>.</p></abstract>
        </article-meta>
      </front>
      <body>
        <sec id="s1">
          <title>Results</title>
          <p id="p1">Body cites <xref ref-type="bibr" rid="r1">1</xref>
          and <xref ref-type="fig" rid="f1">Fig. 1</xref>.</p>
          <fig id="f1"><label>Figure 1</label><caption><p>Caption.</p></caption></fig>
        </sec>
      </body>
      <back>
        <ref-list>
          <ref id="r1"><element-citation><article-title>Cited</article-title></element-citation></ref>
        </ref-list>
      </back>
    </article>
    """
    legacy = build_complete_paper_dict(12345, ET.fromstring(xml.encode()))
    data = Paper(legacy).to_dict()

    assert data["schema_version"] == 4
    assert data["article"]["identifiers"]["doi"] == "10.1234/v4"
    assert (
        data["article"]["identifiers"]["all"][0]["source"]["jats_tag"] == "article-id"
    )
    assert (
        data["article"]["title"]["records"][0]["source"]["jats_tag"] == "article-title"
    )
    assert (
        data["article"]["metadata"]["keyword_groups"][0]["keywords"][0]["text"]
        == "json"
    )
    assert data["article"]["compliance"]["licenses"][0]["type"] == "cc-by"
    assert data["contributors"]["people"][0]["display_name"] == "Ada Lovelace"
    assert data["contributors"]["affiliations"][0]["id"] == "aff1"
    assert data["content"]["sections"][0]["source"]["jats_tag"] == "sec"
    assert data["content"]["sections"][0]["blocks"][0]["source"]["jats_tag"] == "p"
    assert data["assets"]["references"][0]["source"]["jats_tag"] == "ref"
    assert data["assets"]["figures"][0]["source"]["jats_tag"] == "fig"
    assert {relation["type"] for relation in data["relations"]} == {
        "xref",
        "contributor_affiliation",
    }
    assert data["quality"]["summary"]["reference_count"] == 1
    assert data["quality"]["summary"]["figure_count"] == 1
    assert "raw_xml" not in json.dumps(data)


def test_v4_preserves_jats_blocks_without_raw_xml_or_synthetic_sources():
    from pmcgrab.parser import build_complete_paper_dict

    xml = """
    <article xmlns:xlink="http://www.w3.org/1999/xlink"
             xmlns:mml="http://www.w3.org/1998/Math/MathML">
      <front>
        <journal-meta><journal-title>Journal</journal-title></journal-meta>
        <article-meta>
          <article-id pub-id-type="pmcid">PMC12345</article-id>
          <title-group><article-title>Loss-aware V4</article-title></title-group>
          <abstract>
            <sec id="as1">
              <title>Background</title>
              <p id="ap1">Abstract sentinel.</p>
              <list id="al1"><list-item><p>Abstract list sentinel.</p></list-item></list>
            </sec>
          </abstract>
        </article-meta>
      </front>
      <body>
        <sec id="s1">
          <title>Results</title>
          <p id="p1">Paragraph <bold>bold sentinel</bold>
            <unknown-inline data-x="1">inline sentinel</unknown-inline>.
          </p>
          <list id="l1" list-type="order">
            <list-item id="li1">
              <p>List sentinel <xref ref-type="fig" rid="f1">Fig. 1</xref>.</p>
            </list-item>
          </list>
          <def-list id="dl1">
            <def-item id="di1">
              <term>Term sentinel</term>
              <def><p>Definition sentinel.</p></def>
            </def-item>
          </def-list>
          <boxed-text id="bt1">
            <caption><title>Box title sentinel</title></caption>
            <p>Box body sentinel.</p>
          </boxed-text>
          <disp-formula id="eq1">
            <label>Eq. 1</label>
            <alternatives>
              <tex-math>E=mc^2</tex-math>
              <mml:math><mml:mi>E</mml:mi></mml:math>
            </alternatives>
          </disp-formula>
          <unknown-block id="ub1" custom="yes"><p>Unknown sentinel.</p></unknown-block>
          <fig id="f1">
            <label>Figure 1</label>
            <caption><p>Figure caption sentinel.</p></caption>
            <graphic xlink:href="fig1.png"/>
          </fig>
          <table-wrap id="t1">
            <label>Table 1</label>
            <caption><p>Table caption sentinel.</p></caption>
            <table>
              <thead><tr><th>A</th></tr></thead>
              <tbody><tr><td>Cell sentinel</td></tr></tbody>
            </table>
          </table-wrap>
          <supplementary-material id="sup1" xlink:href="s1.csv">
            <label>Supplement</label>
            <caption><p>Supplement caption sentinel.</p></caption>
          </supplementary-material>
        </sec>
      </body>
      <back>
        <ref-list>
          <ref id="r1"><mixed-citation>Reference sentinel.</mixed-citation></ref>
        </ref-list>
      </back>
    </article>
    """
    legacy = build_complete_paper_dict(12345, ET.fromstring(xml.encode()))
    data = Paper(legacy).to_dict()
    payload = json.dumps(data)

    section = data["content"]["sections"][0]
    blocks = section["blocks"]
    block_types = [block["type"] for block in blocks]

    assert block_types == [
        "paragraph",
        "list",
        "def_list",
        "boxed_text",
        "formula",
        "unknown_block",
        "figure_ref",
        "table_ref",
        "supplementary_ref",
    ]
    assert [block["source"]["jats_tag"] for block in blocks[1:6]] == [
        "list",
        "def-list",
        "boxed-text",
        "disp-formula",
        "unknown-block",
    ]
    assert blocks[1]["items"][0]["blocks"][0]["inline"][1]["type"] == "xref"
    assert blocks[2]["items"][0]["term"] == "Term sentinel"
    assert blocks[3]["title"] == "Box title sentinel"
    assert blocks[4]["mathml"]["tag"] == "math"
    assert blocks[5]["parse_status"] == "generic_fallback"

    assert data["assets"]["tables"][0]["records"] == [{"A": "Cell sentinel"}]
    assert data["assets"]["figures"][0]["graphics"][0]["href"] == "fig1.png"
    assert data["assets"]["supplementary_material"][0]["href"] == "s1.csv"
    assert data["assets"]["equations"]["records"][0]["id"] == "eq1"
    assert any(relation["target_ids"] == ["f1"] for relation in data["relations"])
    assert data["quality"]["coverage"]["unrepresented_text_count"] == 0
    assert data["quality"]["summary"]["generic_fallback_count"] == 1

    for sentinel in [
        "Abstract list sentinel",
        "bold sentinel",
        "inline sentinel",
        "List sentinel",
        "Definition sentinel",
        "Box body sentinel",
        "Unknown sentinel",
        "Figure caption sentinel",
        "Table caption sentinel",
        "Supplement caption sentinel",
        "Reference sentinel",
    ]:
        assert sentinel in payload

    assert "raw_xml" not in payload
    assert "raw_text" not in payload
    assert "citation_raw" not in payload
    assert "<mml" not in payload


def test_v4_structures_legacy_mathml_strings_instead_of_emitting_xml_markup():
    paper = Paper(
        {
            "PMCID": 12345,
            "Title": "Legacy MathML",
            "Abstract": [_section("<sec><p>Abstract.</p></sec>")],
            "Body": [_section("<sec><title>Results</title><p>Text.</p></sec>")],
            "Equations": [
                '<mml:math xmlns:mml="http://www.w3.org/1998/Math/MathML">'
                "<mml:mi>x</mml:mi>"
                "</mml:math>"
            ],
        }
    )

    data = paper.to_dict()
    payload = json.dumps(data)

    assert data["assets"]["equations"]["mathml"][0]["tag"] == "math"
    assert data["assets"]["equations"]["mathml"][0]["children"][0]["tag"] == "mi"
    assert "<mml" not in payload
