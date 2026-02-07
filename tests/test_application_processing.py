from typing import Any, ClassVar

from pmcgrab.application import processing as app_proc


def test_process_single_pmc_returns_none_for_invalid(monkeypatch):
    # Monkeypatch builder to always return None (simulate network failure)
    monkeypatch.setattr(app_proc, "build_paper_from_pmc", lambda *a, **kw: None)
    out = app_proc.process_single_pmc("999999")
    assert out is None


def test_process_pmc_ids_success(monkeypatch):
    # Fake builder returns minimal Paper-like object

    class DummySection:
        title = "Test Section"
        children: ClassVar[list] = []

        def get_section_text(self):
            return "Test content"

        def get_clean_text(self):
            return "Test content"

        def __str__(self):
            return "Test content"

    class DummyPaper:
        has_data = True
        abstract: ClassVar[list] = []
        title = "Dummy"
        body: ClassVar[list] = [
            DummySection()
        ]  # Non-empty body so it doesn't return None
        authors = None
        non_author_contributors = None
        publisher_name = None
        publisher_location = None
        article_id = None
        journal_title = None
        journal_id = None
        issn = None
        article_types = None
        article_categories = None
        published_date = None
        history_dates = None
        volume = None
        issue = None
        fpage = None
        lpage = None
        elocation_id = None
        permissions = None
        copyright = None
        license = None
        funding = None
        ethics = None
        supplementary = None
        equations = None
        footnote = None
        acknowledgements = None
        notes = None
        custom_meta = None
        citations = None
        tables = None
        figures = None
        keywords = None
        counts = None
        self_uri = None
        related_articles = None
        conference = None
        version_history = None
        subtitle = None
        author_notes = None
        appendices = None
        glossary = None
        translated_titles = None
        translated_abstracts = None
        abstract_type = None
        tex_equations = None

        def abstract_as_str(self):
            return ""

        def abstract_as_dict(self):
            return {}

        def body_as_dict(self):
            return {"Test Section": "Test content"}

        def body_as_nested_dict(self):
            return {"Test Section": {"_text": "Test content"}}

        def body_as_paragraphs(self):
            return [
                {
                    "section": "Test Section",
                    "subsection": None,
                    "paragraph_index": 0,
                    "text": "Test content",
                }
            ]

        def full_text(self):
            return "Test content"

        def get_toc(self):
            return ["Test Section"]

    monkeypatch.setattr(app_proc, "build_paper_from_pmc", lambda *a, **kw: DummyPaper())
    res: dict[str, Any] = app_proc.process_pmc_ids(["1", "2"], workers=2)
    assert res == {"1": True, "2": True}
