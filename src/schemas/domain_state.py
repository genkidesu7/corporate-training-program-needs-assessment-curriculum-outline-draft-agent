"""AgentCore Platform v1.0"""

# ADR-005: State must be a flat TypedDict (see ADR-005 for the prohibited
# alternatives). LangGraph checkpoints use msgpack serialization, so only
# plain serializable fields are allowed. Do NOT add credentials or secrets.
#
# This is the INNER graph state for the Cat 2 domain workflow
# (src/graph/domain_workflow_graph.py). No individual employee identifiers,
# names, or performance data may ever be stored here — aggregate role-cohort
# data only (S-5, see docs/02_design.md).

from typing import Any

from framework.schemas.agent_state import AgentState


class DomainState(AgentState):
    """Inner domain workflow state.

    All shared fields (user_input, status, session_id, node_history,
    error_log, hitl_*, etc.) are inherited from AgentState.
    """

    workforce_profile: dict[str, Any]  # parsed aggregate role-cohort profile
    target_dss_level: str  # "DX-Lite" | "DX-Standard" | "DX-Expert"
    skill_gap_matrix: dict[str, Any]  # per-role-cohort, per-DSS-dimension gap severity
    learning_objectives: list[dict[str, Any]]  # Bloom's-aligned objectives per gap
    retrieved_framework_passages: list[dict[str, Any]]  # DSS + 職業能力開発促進法 framework passages
    curriculum_outline: dict[str, Any]  # draft phased curriculum outline
    tna_report: dict[str, Any]  # final validated TNA report + curriculum outline
