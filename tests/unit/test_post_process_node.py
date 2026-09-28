# Unit tests: PostProcessNode

from framework.schemas.agent_status import AgentStatus

from src.nodes.post_process_node import DISCLAIMER, PostProcessNode


class TestPostProcessNode:
    def setup_method(self):
        self.node = PostProcessNode()

    def test_success_path_attaches_disclaimer(self):
        state = {"result": {"tna_report": {"target_dss_level": "DX-Standard"}}, "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["formatted_output"]["disclaimer"] == DISCLAIMER
        assert result["formatted_output"]["tna_report"] == state["result"]

    def test_s3_adds_disclaimer_if_missing(self):
        result = {"formatted_output": {"tna_report": {}}}
        gated = self.node._extra_security_gate_output(result)
        assert gated["formatted_output"]["disclaimer"] == DISCLAIMER

    def test_s3_preserves_existing_disclaimer(self):
        result = {"formatted_output": {"disclaimer": "custom"}}
        gated = self.node._extra_security_gate_output(result)
        assert gated["formatted_output"]["disclaimer"] == "custom"
