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

        def get_section_text(self):
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
        volume = None
        issue = None
        permissions = None
        copyright = None
        license = None
        funding = None
        footnote = None
        acknowledgements = None
        notes = None
        custom_meta = None

        def abstract_as_str(self):
            return ""

    monkeypatch.setattr(app_proc, "build_paper_from_pmc", lambda *a, **kw: DummyPaper())
    res: dict[str, Any] = app_proc.process_pmc_ids(["1", "2"], workers=2)
    assert res == {"1": True, "2": True}
