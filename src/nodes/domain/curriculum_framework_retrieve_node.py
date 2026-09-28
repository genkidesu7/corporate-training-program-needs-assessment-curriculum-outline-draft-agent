"""AgentCore Platform v1.0"""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.services.events import emitter
from shared.services.events.types import EventType
from shared.utils.audit_logger import emit_trace_event

from src.services.kb_service import DSS_INDEX, LABOR_LAW_INDEX, KnowledgeBaseService


class CurriculumFrameworkRetrieveNode(FunctionNode):
    """Vector-searches DSS + labor-law indices. Reads skill_gap_matrix, target_dss_level. Writes retrieved_framework_passages."""

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        emitter().emit_event(
            event_type=EventType.PROGRESS_UPDATE,
            message="Retrieving curriculum framework passages...",
            metadata={"stage": "curriculum_framework_retrieve"},
        )
        skill_gap_matrix = state.get("skill_gap_matrix") or {}
        target_dss_level = state.get("target_dss_level", "DX-Standard")

        if not skill_gap_matrix:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["CurriculumFrameworkRetrieveNode: skill_gap_matrix missing"],
            }

        gapped_dimensions = sorted(
            {
                dimension
                for dimensions in skill_gap_matrix.values()
                for dimension, severity in dimensions.items()
                if severity > 0
            }
        )
        query = f"target={target_dss_level} gaps={','.join(gapped_dimensions) or target_dss_level}"

        try:
            kb = KnowledgeBaseService()
            passages = asyncio.run(kb.search(DSS_INDEX, query, target_dss_level))
            passages += asyncio.run(kb.search(LABOR_LAW_INDEX, query, target_dss_level))
        except Exception as exc:
            return {
                "status": AgentStatus.RETRY.value,
                "error_log": [f"CurriculumFrameworkRetrieveNode: [RETRY] {exc}"],
            }

        emit_trace_event(
            "curriculum_framework_retrieved",
            {"passage_count": len(passages)},
            state,
        )

        return {
            "retrieved_framework_passages": passages,
            "status": AgentStatus.SUCCESS.value,
        }
