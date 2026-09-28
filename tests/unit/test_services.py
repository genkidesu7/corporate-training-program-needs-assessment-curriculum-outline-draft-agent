# Unit tests: src/services/*.py (mock-mode paths)

import pytest

from src.services.dss_gap_analysis_service import DssGapAnalysisService
from src.services.kb_service import DSS_INDEX, KnowledgeBaseService
from src.services.llm_service import LLMService


@pytest.fixture(autouse=True)
def _mock_mode(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")


class TestDssGapAnalysisService:
    @pytest.mark.asyncio
    async def test_analyze_returns_matrix_per_cohort(self):
        service = DssGapAnalysisService()
        result = await service.analyze({"role_cohorts": ["sales", "engineering"]}, "DX-Standard")
        assert set(result.keys()) == {"sales", "engineering"}
        for dimensions in result.values():
            assert set(dimensions.keys()) == {"DX-Lite", "DX-Standard", "DX-Expert"}


class TestKnowledgeBaseService:
    @pytest.mark.asyncio
    async def test_search_returns_passages(self):
        service = KnowledgeBaseService()
        result = await service.search(DSS_INDEX, "query", "DX-Standard")
        assert len(result) >= 1
        assert result[0]["index"] == DSS_INDEX


class TestLLMService:
    @pytest.mark.asyncio
    async def test_generate_learning_objectives(self):
        service = LLMService()
        gap_matrix = {"sales": {"DX-Standard": 0.6}}
        objectives = await service.generate_learning_objectives(gap_matrix, "mock")
        assert len(objectives) == 1
        assert objectives[0]["cohort"] == "sales"

    @pytest.mark.asyncio
    async def test_draft_curriculum_outline(self):
        service = LLMService()
        objectives = [{"cohort": "sales", "dimension": "DX-Standard", "objective": "apply skills"}]
        passages = [{"index": DSS_INDEX}]
        outline = await service.draft_curriculum_outline(objectives, passages, "mock")
        assert "phases" in outline
