"""AgentCore Platform v1.0"""

# Mock-mode stub data for local/dev/CI use — no external calls, no secrets.
# Referenced by DssGapAnalysisService, KnowledgeBaseService, and LLMService
# when mock_mode_enabled() is True.

from __future__ import annotations

from typing import Any

DSS_DIMENSIONS = ("DX-Lite", "DX-Standard", "DX-Expert")


async def stub_gap_matrix(workforce_profile: dict[str, Any], target_dss_level: str) -> dict[str, Any]:
    """Representative skill-gap matrix keyed by role cohort → DSS dimension → severity."""
    cohorts = workforce_profile.get("role_cohorts") or ["general_staff"]
    return {
        cohort: {dimension: 0.6 if dimension == target_dss_level else 0.2 for dimension in DSS_DIMENSIONS}
        for cohort in cohorts
    }


async def stub_kb_search(index: str, query: str, target_dss_level: str) -> list[dict[str, Any]]:
    """Representative retrieved passages for a given KB index."""
    return [
        {
            "index": index,
            "passage": f"[mock] {index} reference passage for {target_dss_level} relevant to: {query[:80]}",
            "score": 0.87,
        }
    ]


async def stub_learning_objectives(skill_gap_matrix: dict[str, Any]) -> list[dict[str, Any]]:
    """Representative Bloom's-aligned learning objectives, one per gapped dimension."""
    objectives = []
    for cohort, dimensions in skill_gap_matrix.items():
        for dimension, severity in dimensions.items():
            if severity >= 0.5:
                objectives.append(
                    {
                        "cohort": cohort,
                        "dimension": dimension,
                        "cognitive_level": "apply",
                        "objective": f"[mock] {cohort} will apply {dimension} competencies in practice",
                    }
                )
    return objectives


async def stub_curriculum_outline(
    learning_objectives: list[dict[str, Any]], retrieved_passages: list[dict[str, Any]]
) -> dict[str, Any]:
    """Representative phased curriculum outline."""
    return {
        "phases": [
            {
                "phase": 1,
                "title": "[mock] Foundations",
                "duration_weeks": 4,
                "modules": [o["objective"] for o in learning_objectives[:3]],
            }
        ],
        "framework_references": [p["index"] for p in retrieved_passages],
    }
