"""AgentCore Platform v1.0"""

# Service layer: shared LLM call interface used by LearningObjectiveGenerate
# and OutlineDraft nodes. Must NOT contain business routing.
#
# Credential resolution follows implementation_rule.md rule 2: mock mode must
# short-circuit BEFORE any credential is required. Never weaken this to
# ctx.secrets.get(key, "mock") — that would let a misconfigured real
# deployment proceed with a placeholder credential.
#
# Real calls always go through AzureOpenAIClient (agenticstar-deploy hard
# rule 1) — never a raw openai/langchain client.

from __future__ import annotations

import json
from typing import Any

from src.services.mock_mode import mock_mode_enabled

SYSTEM_PROMPT = (
    "You are a Japanese corporate training and リスキリング (reskilling) specialist. "
    "Design curricula strictly per the METI デジタルスキル標準 (DSS) framework and align "
    "to 職業能力開発促進法 requirements. Never include individual employee names, "
    "identifiers, or performance data in any output — aggregate role-cohort data only."
)


def _call_llm(prompt: str, credential_handle: Any, max_tokens: int, temperature: float) -> str:
    """The one place AzureOpenAIClient is constructed — never inline in a node."""
    from shared.services.llm.azure_openai_client import AzureOpenAIClient  # lazy import

    api_key = credential_handle.require("AZURE_OPENAI_API_KEY")
    azure_endpoint = credential_handle.require("AZURE_OPENAI_ENDPOINT")
    azure_deployment = credential_handle.require("AZURE_OPENAI_DEPLOYMENT")

    client = AzureOpenAIClient(
        config={
            "api_key": api_key,
            "azure_endpoint": azure_endpoint,
            "azure_deployment": azure_deployment,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
    )
    response = client.complete([{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}])
    return str(response["content"])


class LLMService:
    """Thin wrapper around the shared LLM client for objective/outline generation."""

    def __init__(self) -> None:
        self._mock_mode: bool = mock_mode_enabled()

    async def generate_learning_objectives(
        self, skill_gap_matrix: dict[str, Any], credential_handle: Any
    ) -> list[dict[str, Any]]:
        if self._mock_mode:
            from src.services.mock_data import stub_learning_objectives

            return await stub_learning_objectives(skill_gap_matrix)

        prompt = (
            "Given this skill-gap matrix (role cohort -> DSS dimension -> severity 0-1), "
            "generate Bloom's Revised Taxonomy-aligned learning objectives for every "
            "cohort/dimension pair with severity >= 0.5. Respond as a JSON array of "
            'objects: [{"cohort": str, "dimension": str, "cognitive_level": str, "objective": str}].\n\n'
            f"skill_gap_matrix: {json.dumps(skill_gap_matrix, ensure_ascii=False)}"
        )
        content = _call_llm(prompt, credential_handle, max_tokens=1500, temperature=0.3)
        objectives = json.loads(content)
        if not isinstance(objectives, list):
            raise ValueError("LLM did not return a JSON array of learning objectives")
        return objectives

    async def draft_curriculum_outline(
        self,
        learning_objectives: list[dict[str, Any]],
        retrieved_passages: list[dict[str, Any]],
        credential_handle: Any,
    ) -> dict[str, Any]:
        if self._mock_mode:
            from src.services.mock_data import stub_curriculum_outline

            return await stub_curriculum_outline(learning_objectives, retrieved_passages)

        prompt = (
            "Draft a phased curriculum outline (phase number, title, duration_weeks, "
            "modules) from these learning objectives, grounded in the retrieved DSS / "
            'labor-law framework passages. Respond as JSON: {"phases": [{"phase": int, '
            '"title": str, "duration_weeks": int, "modules": [str]}], "framework_references": [str]}.\n\n'
            f"learning_objectives: {json.dumps(learning_objectives, ensure_ascii=False)}\n"
            f"retrieved_passages: {json.dumps(retrieved_passages, ensure_ascii=False)}"
        )
        content = _call_llm(prompt, credential_handle, max_tokens=2000, temperature=0.3)
        outline = json.loads(content)
        if not isinstance(outline, dict):
            raise ValueError("LLM did not return a JSON object for the curriculum outline")
        return outline
