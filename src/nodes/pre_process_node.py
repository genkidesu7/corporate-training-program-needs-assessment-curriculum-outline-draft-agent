"""AgentCore Platform v1.0"""

# Node contract (agents_layer_design.md §1):
#  - Extend FunctionNode; implement execute(state) -> dict
#  - Return ONLY the fields this node changes (never full state)
#  - Return AgentStatus enum constants — never plain strings [A1]
#  - Read input_context via state.get("input_context", {}) — read-only [C1]
#  - Never import from mediator/, api/, or other agents

from __future__ import annotations

import re
from typing import Any, ClassVar

from framework.errors import SecurityViolationError
from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.services.events import emitter
from shared.services.events.types import EventType
from shared.utils.audit_logger import emit_trace_event

MAX_CHARS = 3000

# S-2: reject any field resembling an individual employee identifier before
# the profile enters state — aggregate-only workforce data (docs/02_design.md).
_INDIVIDUAL_IDENTIFIER_KEYS = re.compile(
    r"(employee_id|employee_name|full_name|first_name|last_name|email|ssn|mynumber)",
    re.IGNORECASE,
)


class PreProcessNode(FunctionNode):
    """Validate and enrich incoming input before main processing."""

    # S-1: explicit by design, not inherited implicitly. Raise to
    # VERIFIED_EXTERNAL/INTERNAL only if this node performs a privileged
    # operation.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def _extra_security_gate_input(self, state: dict[str, Any]) -> dict[str, Any]:
        """S-2 domain extension. Rejects individual-employee-identifier fields."""
        user_input = state.get("user_input", "")
        if isinstance(user_input, str) and len(user_input) > MAX_CHARS:
            raise SecurityViolationError(f"user_input exceeds {MAX_CHARS} chars")
        workforce_profile = state.get("workforce_profile") or {}
        for key in workforce_profile:
            if _INDIVIDUAL_IDENTIFIER_KEYS.search(str(key)):
                raise SecurityViolationError(f"individual-identifier field rejected: {key}")
        return state

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        emitter().emit_event(
            event_type=EventType.PROGRESS_UPDATE,
            message="Validating input...",
            metadata={"stage": "pre_process"},
        )
        user_input = state.get("user_input", "")
        input_context = state.get("input_context", {})  # read-only [C1]

        if not user_input or not user_input.strip():
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["PreProcessNode: user_input is empty or missing"],
            }

        emit_trace_event("input_validated", {"input_length": len(user_input.strip())}, state)

        return {
            "validated_input": user_input.strip(),
            "enriched_context": {
                "source": "edu-c2-030",
                "channel": input_context.get("channel", "unknown"),
            },
            "status": AgentStatus.SUCCESS.value,
        }
