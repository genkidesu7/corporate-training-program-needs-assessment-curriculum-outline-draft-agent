"""AgentCore Platform v1.0"""

# Terminal node of the inner domain workflow. Runs the S-3 individual-data
# leakage scan on the drafted output (docs/02_design.md Services / Framework
# Utilization) and writes the S-4 audit log entry (input hash, output type,
# timestamp) — see docs/engineer_proposal.md §4 OutputValidate row.

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.services.events import emitter
from shared.services.events.types import EventType
from shared.utils.audit_logger import emit_trace_event

_INDIVIDUAL_IDENTIFIER_PATTERN = re.compile(
    r"(employee_id|employee_name|full_name|first_name|last_name|@[\w.-]+\.\w+)",
    re.IGNORECASE,
)


def _contains_individual_data(payload: object) -> bool:
    if isinstance(payload, dict):
        return any(
            _INDIVIDUAL_IDENTIFIER_PATTERN.search(str(k)) or _contains_individual_data(v) for k, v in payload.items()
        )
    if isinstance(payload, list):
        return any(_contains_individual_data(item) for item in payload)
    if isinstance(payload, str):
        return bool(_INDIVIDUAL_IDENTIFIER_PATTERN.search(payload))
    return False


class OutputValidateNode(FunctionNode):
    """S-3 individual-data leak scan + S-4 audit log. Reads curriculum_outline. Writes tna_report."""

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        emitter().emit_event(
            event_type=EventType.PROGRESS_UPDATE,
            message="Validating output and generating TNA report...",
            metadata={"stage": "output_validate"},
        )
        curriculum_outline = state.get("curriculum_outline") or {}
        skill_gap_matrix = state.get("skill_gap_matrix") or {}

        if not curriculum_outline:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["OutputValidateNode: curriculum_outline missing"],
            }

        if _contains_individual_data(curriculum_outline):
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["OutputValidateNode: S-3 blocked — individual-level data detected in output"],
            }

        tna_report = {
            "target_dss_level": state.get("target_dss_level"),
            "skill_gap_matrix": skill_gap_matrix,
            "learning_objectives": state.get("learning_objectives", []),
            "curriculum_outline": curriculum_outline,
        }

        input_hash = hashlib.sha256(str(state.get("workforce_profile", "")).encode("utf-8")).hexdigest()
        emit_trace_event(
            "output_validated",
            {
                "input_hash": input_hash,
                "output_type": "tna_report",
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            },
            state,
        )

        return {
            "tna_report": tna_report,
            "status": AgentStatus.SUCCESS.value,
        }
