import importlib


def test_next_email_cycle(monkeypatch):
    monkeypatch.setenv("PMCGRAB_EMAILS", "a@example.com,b@example.com")
    settings = importlib.reload(
        importlib.import_module("pmcgrab.infrastructure.settings")
    )

    first = settings.next_email()
    second = settings.next_email()
    third = settings.next_email()

    assert first == "a@example.com"
    assert second == "b@example.com"
    assert third == "a@example.com"  # cycle should repeat
