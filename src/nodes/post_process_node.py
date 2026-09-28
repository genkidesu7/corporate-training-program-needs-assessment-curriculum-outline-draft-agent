"""AgentCore Platform v1.0"""

from __future__ import annotations

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.services.events import emitter
from shared.services.events.types import EventType
from shared.utils.audit_logger import emit_trace_event

DISCLAIMER = (
    "AI-generated curriculum outline. HR manager and qualified training "
    "professional must validate before program launch."
)


class PostProcessNode(FunctionNode):
    """Format and finalize the output."""

    # S-1: explicit by design, not inherited implicitly.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def _extra_security_gate_output(self, result: dict[str, Any]) -> dict[str, Any]:
        """S-3 domain extension. Ensures the disclaimer is present on the final output."""
        formatted_output = result.get("formatted_output") or {}
        if isinstance(formatted_output, dict) and "disclaimer" not in formatted_output:
            formatted_output = {**formatted_output, "disclaimer": DISCLAIMER}
            result["formatted_output"] = formatted_output
        return result

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        emitter().emit_event(
            event_type=EventType.PROGRESS_UPDATE,
            message="Finalizing output...",
            metadata={"stage": "post_process"},
        )
        result = state.get("result") or {}

        formatted_output = {
            "tna_report": result,
            "disclaimer": DISCLAIMER,
        }

        emit_trace_event("output_formatted", {"has_result": bool(result)}, state)

        return {
            "formatted_output": formatted_output,
            "status": AgentStatus.SUCCESS.value,
        }
