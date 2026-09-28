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

from src.services.dss_gap_analysis_service import DssGapAnalysisService


class SkillGapAnalyzeNode(FunctionNode):
    """Maps role cohorts to DSS dimensions, computes gap severity. Reads workforce_profile, target_dss_level. Writes skill_gap_matrix."""

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        emitter().emit_event(
            event_type=EventType.PROGRESS_UPDATE,
            message="Analyzing skill gaps...",
            metadata={"stage": "skill_gap_analyze"},
        )
        workforce_profile = state.get("workforce_profile") or {}
        target_dss_level = state.get("target_dss_level", "DX-Standard")

        if not workforce_profile:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["SkillGapAnalyzeNode: workforce_profile missing"],
            }

        try:
            service = DssGapAnalysisService()
            skill_gap_matrix = asyncio.run(service.analyze(workforce_profile, target_dss_level))
        except Exception as exc:  # transient KB/service failure -> retry via outer pre_process
            return {
                "status": AgentStatus.RETRY.value,
                "error_log": [f"SkillGapAnalyzeNode: [RETRY] {exc}"],
            }

        emit_trace_event(
            "skill_gap_analyzed",
            {"cohort_count": len(skill_gap_matrix)},
            state,
        )

        return {
            "skill_gap_matrix": skill_gap_matrix,
            "status": AgentStatus.SUCCESS.value,
        }
