# Unit tests: inner domain workflow nodes (src/nodes/domain/*.py)

import pytest
from framework.schemas.agent_status import AgentStatus

from src.nodes.domain.curriculum_framework_retrieve_node import CurriculumFrameworkRetrieveNode
from src.nodes.domain.learning_objective_generate_node import LearningObjectiveGenerateNode
from src.nodes.domain.needs_data_ingest_node import NeedsDataIngestNode
from src.nodes.domain.outline_draft_node import OutlineDraftNode
from src.nodes.domain.output_validate_node import OutputValidateNode
from src.nodes.domain.skill_gap_analyze_node import SkillGapAnalyzeNode


@pytest.fixture(autouse=True)
def _mock_mode(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")


def _ctx_fields() -> dict:
    """InvocationContext.from_state() requires these four keys present."""
    return {"correlation_id": "c", "session_id": "s", "thread_id": "t", "trace_id": "tr"}


class TestNeedsDataIngestNode:
    def setup_method(self):
        self.node = NeedsDataIngestNode()

    def test_parses_json_input_into_workforce_profile(self):
        state = {
            "user_input": '{"role_cohorts": ["sales", "engineering"], "target_dss_level": "DX-Standard"}',
            **_ctx_fields(),
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["workforce_profile"]["role_cohorts"] == ["sales", "engineering"]
        assert result["target_dss_level"] == "DX-Standard"

    def test_missing_input_errors(self):
        result = self.node.execute({"user_input": "", **_ctx_fields()})
        assert result["status"] == AgentStatus.ERROR.value

    def test_rejects_individual_identifier_field(self):
        """S-1/S-5: aggregate-only workforce data."""
        state = {
            "user_input": "ignored",
            "workforce_profile": {"employee_name": "Taro Yamada"},
            **_ctx_fields(),
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR.value

    def test_falls_back_to_user_input_when_validated_input_absent(self):
        """Inner graph fresh-state rule: validated_input is not carried over."""
        state = {
            "user_input": '{"role_cohorts": ["sales"], "target_dss_level": "DX-Lite"}',
            **_ctx_fields(),
        }
        assert "validated_input" not in state
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value


class TestSkillGapAnalyzeNode:
    def test_success_path(self):
        node = SkillGapAnalyzeNode()
        state = {
            "workforce_profile": {"role_cohorts": ["sales"]},
            "target_dss_level": "DX-Standard",
            **_ctx_fields(),
        }
        result = node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert "sales" in result["skill_gap_matrix"]

    def test_missing_profile_errors(self):
        node = SkillGapAnalyzeNode()
        result = node.execute({"workforce_profile": {}, **_ctx_fields()})
        assert result["status"] == AgentStatus.ERROR.value


class TestLearningObjectiveGenerateNode:
    def test_success_path_no_secrets_bound(self):
        """Mock mode must not require a resolvable secret (implementation_rule.md rule 2)."""
        node = LearningObjectiveGenerateNode()
        state = {
            "skill_gap_matrix": {"sales": {"DX-Standard": 0.6}},
            "caller_trust_level": "VERIFIED_EXTERNAL",
            **_ctx_fields(),
        }
        result = node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert len(result["learning_objectives"]) >= 1

    def test_missing_gap_matrix_errors(self):
        node = LearningObjectiveGenerateNode()
        result = node.execute(
            {"skill_gap_matrix": {}, "caller_trust_level": "VERIFIED_EXTERNAL", **_ctx_fields()}
        )
        assert result["status"] == AgentStatus.ERROR.value


class TestCurriculumFrameworkRetrieveNode:
    def test_success_path(self):
        node = CurriculumFrameworkRetrieveNode()
        state = {
            "skill_gap_matrix": {"sales": {"DX-Standard": 0.6}},
            "target_dss_level": "DX-Standard",
            **_ctx_fields(),
        }
        result = node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert len(result["retrieved_framework_passages"]) >= 1


class TestOutlineDraftNode:
    def test_success_path_no_secrets_bound(self):
        node = OutlineDraftNode()
        state = {
            "learning_objectives": [
                {"cohort": "sales", "dimension": "DX-Standard", "objective": "apply DX-Standard skills"}
            ],
            "retrieved_framework_passages": [{"index": "dss_framework"}],
            "caller_trust_level": "VERIFIED_EXTERNAL",
            **_ctx_fields(),
        }
        result = node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert "phases" in result["curriculum_outline"]

    def test_missing_objectives_errors(self):
        node = OutlineDraftNode()
        result = node.execute(
            {
                "learning_objectives": [],
                "retrieved_framework_passages": [],
                "caller_trust_level": "VERIFIED_EXTERNAL",
                **_ctx_fields(),
            }
        )
        assert result["status"] == AgentStatus.ERROR.value


class TestOutputValidateNode:
    def setup_method(self):
        self.node = OutputValidateNode()

    def test_success_path(self):
        state = {
            "curriculum_outline": {"phases": [{"title": "Foundations"}]},
            "skill_gap_matrix": {},
            "workforce_profile": {"role_cohorts": ["sales"]},
            **_ctx_fields(),
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["tna_report"]["curriculum_outline"] == state["curriculum_outline"]

    def test_blocks_on_individual_data_leakage(self):
        """S-3: individual-level data in the drafted output must be blocked."""
        state = {
            "curriculum_outline": {"phases": [{"employee_name": "Taro Yamada"}]},
            "skill_gap_matrix": {},
            "workforce_profile": {},
            **_ctx_fields(),
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR.value

    def test_missing_outline_errors(self):
        result = self.node.execute({"curriculum_outline": {}, **_ctx_fields()})
        assert result["status"] == AgentStatus.ERROR.value
