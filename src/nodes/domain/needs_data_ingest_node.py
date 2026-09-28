"""AgentCore Platform v1.0"""

# Node contract (agents_layer_design.md §1):
#  - Extend FunctionNode; implement execute(state) -> dict
#  - Return ONLY the fields this node changes (never full state)
#  - Return AgentStatus enum constants — never plain strings [A1]
#  - Never import from mediator/, api/, or other agents
#
# Inner-graph node: the inner graph's initial_state only contains user_input
# (BaseGraph.invoke() never copies validated_input from the outer graph) —
# see sdk-expertise "Cat 2 — composition via GraphNode".

from __future__ import annotations

import json
import re
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.services.events import emitter
from shared.services.events.types import EventType
from shared.utils.audit_logger import emit_trace_event

MAX_CHARS = 3000
VALID_DSS_LEVELS = ("DX-Lite", "DX-Standard", "DX-Expert")

# S-1/S-5: reject any field resembling an individual employee identifier —
# aggregate role-cohort data only (docs/02_design.md, engineer_proposal.md §10 row 5).
_INDIVIDUAL_IDENTIFIER_KEYS = re.compile(
    r"(employee_id|employee_name|full_name|first_name|last_name|email|ssn|mynumber)",
    re.IGNORECASE,
)


class NeedsDataIngestNode(FunctionNode):
    """Parses/validates the aggregate workforce profile. Reads user_input. Writes workforce_profile, target_dss_level."""

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        emitter().emit_event(
            event_type=EventType.PROGRESS_UPDATE,
            message="Ingesting workforce needs data...",
            metadata={"stage": "needs_data_ingest"},
        )
        validated_input = state.get("validated_input", state.get("user_input", ""))

        if not validated_input or not validated_input.strip():
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["NeedsDataIngestNode: input is empty or missing"],
            }

        if len(validated_input) > MAX_CHARS:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": [f"NeedsDataIngestNode: input exceeds {MAX_CHARS} chars"],
            }

        workforce_profile = state.get("workforce_profile") or {}
        if not workforce_profile:
            try:
                parsed = json.loads(validated_input)
                if isinstance(parsed, dict):
                    workforce_profile = parsed
            except (json.JSONDecodeError, TypeError):
                workforce_profile = {}

        role_cohorts = workforce_profile.get("role_cohorts") or ["general_staff"]
        target_dss_level = workforce_profile.get("target_dss_level", "DX-Standard")

        for key in workforce_profile:
            if _INDIVIDUAL_IDENTIFIER_KEYS.search(str(key)):
                return {
                    "status": AgentStatus.ERROR.value,
                    "error_log": [f"NeedsDataIngestNode: rejected individual-identifier field '{key}'"],
                }

        if target_dss_level not in VALID_DSS_LEVELS:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": [f"NeedsDataIngestNode: invalid target_dss_level '{target_dss_level}'"],
            }

        emit_trace_event(
            "needs_data_ingested",
            {"role_cohort_count": len(role_cohorts), "target_dss_level": target_dss_level},
            state,
        )

        return {
            "workforce_profile": {**workforce_profile, "role_cohorts": role_cohorts},
            "target_dss_level": target_dss_level,
            "status": AgentStatus.SUCCESS.value,
        }
