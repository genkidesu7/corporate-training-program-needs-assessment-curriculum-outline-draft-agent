# Integration test: outer EduC2030CorporateTrainingNeedsAssessmentAgent
# compiled + invoked end-to-end via .invoke() (not stubbed execute()/route()
# calls) — exercises the full pipeline including the Cat 2 GraphNode
# composition into the inner domain workflow graph.

import pytest
from framework.secrets.context import bound_secrets
from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel
from shared.secrets.inmemory_provider import InMemoryProvider

from src.graph.graph import EduC2030CorporateTrainingNeedsAssessmentAgent


@pytest.fixture(autouse=True)
def _mock_mode(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")


def test_outer_graph_invoke_success_verified_external():
    agent = EduC2030CorporateTrainingNeedsAssessmentAgent(config={"max_retry": 1})
    agent.compile()
    provider = InMemoryProvider({"ANTHROPIC_API_KEY": "mock-api-key-for-testing"})
    agent.provision_secrets(provider)

    ctx = InvocationContext(caller_trust_level=TrustLevel.VERIFIED_EXTERNAL, secrets=provider)
    sample_input = '{"role_cohorts": ["sales", "engineering"], "target_dss_level": "DX-Standard"}'

    with bound_secrets(provider):
        result = agent.invoke(sample_input, ctx=ctx)

    assert result["status"] == "success"
    output = result.get("output") or result.get("formatted_output")
    assert output["disclaimer"]
    assert output["tna_report"]["curriculum_outline"]["phases"]


def test_outer_graph_denies_anonymous_caller():
    """S-1: nodes requiring VERIFIED_EXTERNAL must deny an ANONYMOUS caller."""
    agent = EduC2030CorporateTrainingNeedsAssessmentAgent(config={"max_retry": 1})
    agent.compile()
    provider = InMemoryProvider({"ANTHROPIC_API_KEY": "mock-api-key-for-testing"})
    agent.provision_secrets(provider)

    ctx = InvocationContext(caller_trust_level=TrustLevel.ANONYMOUS, secrets=provider)
    sample_input = '{"role_cohorts": ["sales"], "target_dss_level": "DX-Standard"}'

    with bound_secrets(provider):
        result = agent.invoke(sample_input, ctx=ctx)

    assert result["status"] == "error"
