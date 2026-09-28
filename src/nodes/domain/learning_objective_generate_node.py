"""AgentCore Platform v1.0"""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel
from shared.services.events import emitter
from shared.services.events.types import EventType
from shared.utils.audit_logger import emit_trace_event

from src.services.llm_service import LLMService
from src.services.mock_mode import mock_mode_enabled


class LearningObjectiveGenerateNode(FunctionNode):
    """LLM-generates Bloom's-aligned objectives per gap. Reads skill_gap_matrix. Writes learning_objectives."""

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        emitter().emit_event(
            event_type=EventType.PROGRESS_UPDATE,
            message="Generating learning objectives...",
            metadata={"stage": "learning_objective_generate"},
        )
        skill_gap_matrix = state.get("skill_gap_matrix") or {}

        if not skill_gap_matrix:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["LearningObjectiveGenerateNode: skill_gap_matrix missing"],
            }

        ctx = InvocationContext.from_state(state)
        # Mock mode must short-circuit before any credential is required
        # (implementation_rule.md rule 2) — the mock path never touches
        # credential_handle. credential_handle is the SecretProvider itself
        # (not a pre-fetched value): LLMService needs all 3 Azure OpenAI
        # secrets, resolved at the point of actual use.
        credential_handle = "mock" if mock_mode_enabled() else ctx.secrets

        try:
            service = LLMService()
            learning_objectives = asyncio.run(service.generate_learning_objectives(skill_gap_matrix, credential_handle))
        except Exception as exc:
            return {
                "status": AgentStatus.RETRY.value,
                "error_log": [f"LearningObjectiveGenerateNode: [RETRY] {exc}"],
            }

        emit_trace_event(
            "learning_objectives_generated",
            {"objective_count": len(learning_objectives)},
            state,
        )

        return {
            "learning_objectives": learning_objectives,
            "status": AgentStatus.SUCCESS.value,
        }
