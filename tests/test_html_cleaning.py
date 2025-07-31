from pmcgrab.common.html_cleaning import strip_html_text_styling


def test_strip_html_text_styling():
    raw = "<p>This is <b>bold</b> and <i>italic</i> plus H<sub>2</sub>O.</p>"
    cleaned = strip_html_text_styling(raw)
    assert "<b>" not in cleaned and "<i>" not in cleaned
    assert "_2" in cleaned  # sub converted to underscore
