"""AgentCore Platform v1.0"""

# EDU-C2-030 — Corporate Training Program Needs Assessment & Curriculum
# Outline Draft Agent. Cat 2: outer AgentBaseGraph with domain complexity
# encapsulated inside CorporateTrainingWorkflowGraphNode (`main` slot),
# wrapping the inner graph at src/graph/domain_workflow_graph.py.
# See docs/02_design.md for the full architecture.
#
# Outer backbone (fixed):
#   START → initialize → pre_process → main → {route} → post_process → finalize → END
#                                          ↓ (RETRY, max 3)
#                                       pre_process

from typing import Any, ClassVar

from framework.graph.agent_base_graph import AgentBaseGraph
from framework.nodes.graph_node import GraphNode
from framework.schemas.agent_state import AgentState

from src.nodes.pre_process_node import PreProcessNode
from src.nodes.post_process_node import PostProcessNode
from src.schemas.state import State


class CorporateTrainingWorkflowGraphNode(GraphNode):
    """Wraps the inner CorporateTrainingWorkflowGraph; assigned to the `main` slot."""

    # Fail fast: a mis-scored DSS gap or failed framework retrieval should
    # fail the invocation, not silently produce an incomplete curriculum
    # outline an HR manager could mistake for reliable (docs/02_design.md
    # Design Decision Record).
    error_strategy: ClassVar[str] = "propagate"
    propagate_hitl: ClassVar[bool] = False

    def get_subgraph(self) -> Any:
        from src.graph.domain_workflow_graph import CorporateTrainingWorkflowGraph

        return CorporateTrainingWorkflowGraph(config=self._parent_config())

    def extract_input(self, state: AgentState) -> str:
        return str(state.get("validated_input", state.get("user_input", "")))

    def merge_output(self, state: AgentState, sub_result: dict[str, Any]) -> dict[str, Any]:
        return {
            "result": sub_result.get("output"),
            "status": sub_result.get("status"),
        }

    def _parent_config(self) -> dict[str, Any]:
        return {}


class EduC2030CorporateTrainingNeedsAssessmentAgent(AgentBaseGraph):
    """Outer graph. Backbone: initialize → pre_process → main → post_process → finalize."""

    @property
    def name(self) -> str:
        return "edu-c2-030"

    @property
    def state_schema(self) -> type:
        return State

    def register_nodes(self) -> None:
        super().register_nodes()  # injects InitializeNode + FinalizeNode

        self._nodes["pre_process"] = PreProcessNode()
        self._nodes["main"] = CorporateTrainingWorkflowGraphNode()
        self._nodes["post_process"] = PostProcessNode()

    # add_edges() is NOT overridden — backbone wiring belongs to the framework.
