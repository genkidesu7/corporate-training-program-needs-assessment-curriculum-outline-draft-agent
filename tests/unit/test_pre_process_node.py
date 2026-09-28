# Unit tests: PreProcessNode

from framework.errors import SecurityViolationError
from framework.schemas.agent_status import AgentStatus

from src.nodes.pre_process_node import PreProcessNode


class TestPreProcessNode:
    def setup_method(self):
        self.node = PreProcessNode()

    def test_success_path(self):
        state = {
            "user_input": '{"role_cohorts": ["sales"], "target_dss_level": "DX-Standard"}',
            "input_context": {},
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["validated_input"] == state["user_input"]

    def test_empty_input(self):
        state = {"user_input": "", "input_context": {}, "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR.value

    def test_s2_rejects_individual_identifier_field(self):
        """S-1/S-5: reject workforce_profile fields resembling individual identifiers."""
        state = {
            "user_input": "some input",
            "workforce_profile": {"employee_id": "E123"},
        }
        try:
            self.node._extra_security_gate_input(state)
            assert False, "expected SecurityViolationError"
        except SecurityViolationError:
            pass

    def test_s2_accepts_aggregate_only_profile(self):
        state = {
            "user_input": "some input",
            "workforce_profile": {"role_cohorts": ["sales"]},
        }
        returned = self.node._extra_security_gate_input(state)
        assert returned is state
