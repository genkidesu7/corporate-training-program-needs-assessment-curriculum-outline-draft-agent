"""AgentCore Platform v1.0"""

# Service layer: vector similarity search over three KB indices — DSS
# framework, 職業能力開発促進法 / 厚労省 ガイドライン, and Bloom's Revised
# Taxonomy templates. Must NOT contain business routing or credentials.
#
# No live vector-store index is provisioned for this template. Per
# agenticstar-deploy's hard rule 2 ("every other service defaults to mock,
# including in real mode — only the LLM call is ever real"), this service
# always returns the sanctioned mock_data.py stub, regardless of
# mock_mode_enabled(). It never gates on it and never raises a stand-in
# error — this IS the real, intended behavior for KB retrieval today.

from __future__ import annotations

from typing import Any

DSS_INDEX = "dss_framework"
LABOR_LAW_INDEX = "shokugyo_nouryoku_kaihatsu_sokushinho"
BLOOMS_INDEX = "blooms_taxonomy"


class KnowledgeBaseService:
    """Similarity search over the KB indices. Always mock — see module docstring."""

    def __init__(self, kb_path: str = "./kb/") -> None:
        self._kb_path = kb_path

    async def search(self, index: str, query: str, target_dss_level: str) -> list[dict[str, Any]]:
        """Return relevant passages from the given index, filtered to target_dss_level."""
        from src.services.mock_data import stub_kb_search

        return await stub_kb_search(index, query, target_dss_level)
