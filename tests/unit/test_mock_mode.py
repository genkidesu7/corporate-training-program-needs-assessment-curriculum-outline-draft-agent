# TC/Test Rule 1: mock-mode flag resolution, tested directly under every alias.
# See .claude/rules/test_rule.md rule 1 — the deploy-stg CI job sets
# STG_MOCK_MODE, never USE_MOCK; a test asserting only USE_MOCK would not
# have caught that class of bug.

from src.services.mock_mode import mock_mode_enabled


def test_mock_mode_enabled_via_use_mock(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    monkeypatch.delenv("STG_MOCK_MODE", raising=False)
    assert mock_mode_enabled() is True


def test_mock_mode_enabled_via_stg_mock_mode_alias(monkeypatch):
    """Regression test: deploy-stg sets STG_MOCK_MODE, never USE_MOCK."""
    monkeypatch.delenv("USE_MOCK", raising=False)
    monkeypatch.setenv("STG_MOCK_MODE", "true")
    assert mock_mode_enabled() is True


def test_mock_mode_disabled_when_neither_set(monkeypatch):
    monkeypatch.delenv("USE_MOCK", raising=False)
    monkeypatch.delenv("STG_MOCK_MODE", raising=False)
    assert mock_mode_enabled() is False
