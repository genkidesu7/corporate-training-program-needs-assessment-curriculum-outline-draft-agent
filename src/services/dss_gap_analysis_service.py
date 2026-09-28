"""AgentCore Platform v1.0"""

# Service layer: structured DSS-to-role-cohort lookup table and gap-severity
# scoring. Deliberately NOT open-ended LLM judgment — see docs/02_design.md
# Design Decision Record ("SkillGapAnalyze logic") and docs/engineer_proposal.md
# §11 risk #1: gap scoring must stay auditable against METI's published DSS
# framework.
# Must NOT contain business routing or credentials.
#
# No validated lookup table is provisioned for this template. Per
# agenticstar-deploy's hard rule 2 ("every other service defaults to mock,
# including in real mode — only the LLM call is ever real"), this service
# always returns the sanctioned mock_data.py stub, regardless of
# mock_mode_enabled(). It never gates on it — see kb_service.py for the same
# pattern.

from __future__ import annotations

from typing import Any

# DSS competency dimensions, ordered by increasing proficiency.
DSS_DIMENSIONS = ("DX-Lite", "DX-Standard", "DX-Expert")


class DssGapAnalysisService:
    """Computes per-role-cohort, per-DSS-dimension skill-gap severity. Always mock — see module docstring."""

    async def analyze(self, workforce_profile: dict[str, Any], target_dss_level: str) -> dict[str, Any]:
        """Return a gap matrix: {cohort: {dimension: severity}}."""
        from src.services.mock_data import stub_gap_matrix

        return await stub_gap_matrix(workforce_profile, target_dss_level)
