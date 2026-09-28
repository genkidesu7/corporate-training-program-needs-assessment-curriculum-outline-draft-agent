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


class OutlineDraftNode(FunctionNode):
    """LLM drafts a phased curriculum outline. Reads learning_objectives, retrieved_framework_passages. Writes curriculum_outline."""

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        emitter().emit_event(
            event_type=EventType.PROGRESS_UPDATE,
            message="Drafting curriculum outline...",
            metadata={"stage": "outline_draft"},
        )
        learning_objectives = state.get("learning_objectives") or []
        retrieved_passages = state.get("retrieved_framework_passages") or []

        if not learning_objectives:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["OutlineDraftNode: learning_objectives missing"],
            }

        ctx = InvocationContext.from_state(state)
        # credential_handle is the SecretProvider itself (see
        # learning_objective_generate_node.py for the same pattern).
        credential_handle = "mock" if mock_mode_enabled() else ctx.secrets

        try:
            service = LLMService()
            curriculum_outline = asyncio.run(
                service.draft_curriculum_outline(learning_objectives, retrieved_passages, credential_handle)
            )
        except Exception as exc:
            return {
                "status": AgentStatus.RETRY.value,
                "error_log": [f"OutlineDraftNode: [RETRY] {exc}"],
            }

        emit_trace_event(
            "curriculum_outline_drafted",
            {"phase_count": len(curriculum_outline.get("phases", []))},
            state,
        )

        return {
            "curriculum_outline": curriculum_outline,
            "status": AgentStatus.SUCCESS.value,
        }
