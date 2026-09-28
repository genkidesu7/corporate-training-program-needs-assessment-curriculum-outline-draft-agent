# Integration test: inner CorporateTrainingWorkflowGraph compiled + invoked
# end-to-end. A stubbed-state unit test bypasses LangGraph's runtime schema
# projection and can pass while the compiled graph is actually broken — see
# sdk-expertise "Running and smoke-testing locally".

import pytest

from src.graph.domain_workflow_graph import CorporateTrainingWorkflowGraph


@pytest.fixture(autouse=True)
def _mock_mode(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")


def test_inner_graph_compiles_and_invokes_end_to_end():
    graph = CorporateTrainingWorkflowGraph(config={})
    graph.compile()

    initial_state = {
        "user_input": '{"role_cohorts": ["sales", "engineering"], "target_dss_level": "DX-Standard"}',
        "correlation_id": "c",
        "session_id": "s",
        "thread_id": "t",
        "trace_id": "tr",
        "caller_trust_level": "VERIFIED_EXTERNAL",
    }
    result = graph._compiled.invoke(initial_state)

    assert result["status"] == "success"
    assert result["node_history"] == [
        "NeedsDataIngestNode",
        "SkillGapAnalyzeNode",
        "LearningObjectiveGenerateNode",
        "CurriculumFrameworkRetrieveNode",
        "OutlineDraftNode",
        "OutputValidateNode",
    ]
    assert result["tna_report"]["curriculum_outline"]["phases"]


def test_inner_graph_get_output_shape():
    graph = CorporateTrainingWorkflowGraph(config={})
    graph.compile()

    initial_state = {
        "user_input": '{"role_cohorts": ["sales"], "target_dss_level": "DX-Lite"}',
        "correlation_id": "c",
        "session_id": "s",
        "thread_id": "t",
        "trace_id": "tr",
        "caller_trust_level": "VERIFIED_EXTERNAL",
    }
    result = graph._compiled.invoke(initial_state)
    sub_result = graph.get_output(result)

    assert sub_result["status"] == "success"
    assert sub_result["output"] is not None
