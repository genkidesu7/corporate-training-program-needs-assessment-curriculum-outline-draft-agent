"""AgentCore Platform v1.0"""

# Inner graph for the Cat 2 corporate training needs assessment domain
# workflow. Called by CorporateTrainingWorkflowGraphNode.get_subgraph() in
# src/graph/graph.py. See docs/02_design.md "Inner Graph" section.
#
# Pipeline (linear):
#   START → needs_data_ingest → skill_gap_analyze → learning_objective_generate
#         → curriculum_framework_retrieve → outline_draft → output_validate → END

from typing import Any

from langgraph.graph import END, START

from framework.graph.base_graph import BaseGraph
from framework.schemas.agent_status import AgentStatus

from src.nodes.domain.curriculum_framework_retrieve_node import CurriculumFrameworkRetrieveNode
from src.nodes.domain.learning_objective_generate_node import LearningObjectiveGenerateNode
from src.nodes.domain.needs_data_ingest_node import NeedsDataIngestNode
from src.nodes.domain.outline_draft_node import OutlineDraftNode
from src.nodes.domain.output_validate_node import OutputValidateNode
from src.nodes.domain.skill_gap_analyze_node import SkillGapAnalyzeNode
from src.schemas.domain_state import DomainState


class CorporateTrainingWorkflowGraph(BaseGraph):
    """Inner graph: aggregate workforce profile -> DSS-aligned TNA report + curriculum outline."""

    @property
    def name(self) -> str:
        return "corporate_training_needs_assessment_workflow"

    @property
    def state_schema(self) -> type:
        return DomainState

    def _validate_config(self) -> None:
        """No mandatory config for this inner graph."""

    def register_nodes(self) -> None:
        """Register all domain nodes. No super() call — BaseGraph.register_nodes() is abstract.

        Do NOT register initialize/finalize; those are outer-backbone concerns.
        """
        self._nodes["needs_data_ingest"] = NeedsDataIngestNode()
        self._nodes["skill_gap_analyze"] = SkillGapAnalyzeNode()
        self._nodes["learning_objective_generate"] = LearningObjectiveGenerateNode()
        self._nodes["curriculum_framework_retrieve"] = CurriculumFrameworkRetrieveNode()
        self._nodes["outline_draft"] = OutlineDraftNode()
        self._nodes["output_validate"] = OutputValidateNode()

    def add_edges(self) -> None:
        """Linear topology — every registered node must be reachable from START."""
        self._sg.add_edge(START, "needs_data_ingest")
        self._sg.add_edge("needs_data_ingest", "skill_gap_analyze")
        self._sg.add_edge("skill_gap_analyze", "learning_objective_generate")
        self._sg.add_edge("learning_objective_generate", "curriculum_framework_retrieve")
        self._sg.add_edge("curriculum_framework_retrieve", "outline_draft")
        self._sg.add_edge("outline_draft", "output_validate")
        self._sg.add_edge("output_validate", END)

    def route(self, state: DomainState) -> str:
        """Required by BaseGraph ABC. Never called — purely linear topology, no conditional edges."""
        return END if state.get("status") == AgentStatus.ERROR.value else "output_validate"

    def get_output(self, state: DomainState) -> dict[str, Any]:
        """Shape sub_result for CorporateTrainingWorkflowGraphNode.merge_output() in graph.py."""
        return {
            "output": state.get("tna_report"),
            "status": state.get("status"),
            "trace_id": state.get("trace_id"),
            "correlation_id": state.get("correlation_id"),
            "node_history": state.get("node_history", []),
        }
