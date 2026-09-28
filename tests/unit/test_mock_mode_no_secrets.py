# Test Rule 2 (.claude/rules/test_rule.md): nodes calling ctx.secrets.require(...)
# unconditionally fail in mock mode on a fresh checkout with no env/ secret tree.
# These tests run WITHOUT any bound_secrets() context — the exact condition
# in a fresh CI checkout — and assert mock mode still reaches SUCCESS.

import pytest
from framework.schemas.agent_status import AgentStatus

from src.nodes.domain.learning_objective_generate_node import LearningObjectiveGenerateNode
from src.nodes.domain.outline_draft_node import OutlineDraftNode


@pytest.fixture(autouse=True)
def _mock_mode(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def _ctx_fields() -> dict:
    return {"correlation_id": "c", "session_id": "s", "thread_id": "t", "trace_id": "tr"}


def test_learning_objective_generate_succeeds_with_no_secret_in_mock_mode():
    """Regression test: a fresh CI checkout has no env/ secret files at all.
    Mock mode must not depend on a secret being resolvable."""
    state = {
        "skill_gap_matrix": {"sales": {"DX-Standard": 0.6}},
        "caller_trust_level": "VERIFIED_EXTERNAL",
        **_ctx_fields(),
    }
    # No bound_secrets() context at all — current_secrets() falls back to NullProvider.
    result = LearningObjectiveGenerateNode().execute(state)
    assert result["status"] == AgentStatus.SUCCESS.value


def test_outline_draft_succeeds_with_no_secret_in_mock_mode():
    state = {
        "learning_objectives": [
            {"cohort": "sales", "dimension": "DX-Standard", "objective": "apply DX-Standard skills"}
        ],
        "retrieved_framework_passages": [{"index": "dss_framework"}],
        "caller_trust_level": "VERIFIED_EXTERNAL",
        **_ctx_fields(),
    }
    result = OutlineDraftNode().execute(state)
    assert result["status"] == AgentStatus.SUCCESS.value
