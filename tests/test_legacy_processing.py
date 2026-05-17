import json

from pmcgrab.processing import _check_output_file


def test_check_output_file_accepts_v2_content_sections(tmp_path):
    output = {
        "schema_version": 2,
        "content": {
            "sections": [
                {
                    "id": "s1",
                    "title": "Results",
                    "level": 1,
                    "blocks": [],
                    "children": [],
                }
            ]
        },
    }
    (tmp_path / "PMC123.json").write_text(json.dumps(output), encoding="utf-8")

    assert _check_output_file(str(tmp_path), "123") is True


def test_check_output_file_rejects_empty_v2_content(tmp_path):
    output = {"schema_version": 2, "content": {"sections": []}}
    (tmp_path / "PMC123.json").write_text(json.dumps(output), encoding="utf-8")

    assert _check_output_file(str(tmp_path), "123") is False


def test_check_output_file_keeps_v1_body_fallback(tmp_path):
    output = {"body": {"Results": "Legacy content"}}
    (tmp_path / "PMC123.json").write_text(json.dumps(output), encoding="utf-8")

    assert _check_output_file(str(tmp_path), "123") is True
