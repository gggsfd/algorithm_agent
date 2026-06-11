import sys

import pytest

sys.path.insert(0, "d:/Mycode/算法_agent/algorithm_agent")

from app.rag.dynamic_knowledge_store import DynamicKnowledgeStore
from app.services.adaptive_srt_service import AdaptiveSRTService
from app.services.dynamic_knowledge_service import DynamicKnowledgeService


class FakeDynamicKnowledgeService(DynamicKnowledgeService):
    def _adapt_material(
        self,
        file_path: str,
        filename: str,
        enable_supplement: bool = True,
        supplement_limit: int = 30,
    ) -> dict:
        return {
            "dict": {"主定理": {"category": "algorithm_analysis", "importance": 5}},
            "asr_mapping": {"主定里": "主定理"},
            "candidate_terms": [
                {
                    "term": "代入法",
                    "category": "algorithm_analysis",
                    "confidence": 0.65,
                    "reason": "递归式求解相关候选术语",
                    "related_terms": ["主定理"],
                }
            ],
            "candidate_asr_mapping": {
                "带入法": {"wrong": "带入法", "correct": "代入法", "confidence": 0.65}
            },
            "source_text_length": 100,
        }


@pytest.mark.asyncio
async def test_adaptive_correct_uses_current_dynamic_store(tmp_path):
    store = DynamicKnowledgeStore(base_path=str(tmp_path / "current"))
    knowledge_service = FakeDynamicKnowledgeService(store=store)
    material = tmp_path / "first.pptx"
    material.write_text("fake", encoding="utf-8")
    knowledge_service.upload_material(str(material), "first.pptx")
    adaptive = AdaptiveSRTService(knowledge_service=knowledge_service)

    srt = "1\n00:00:00,000 --> 00:00:01,000\n这里使用主定里求解递归式\n"
    result = await adaptive.correct_current(srt)

    assert result["success"] is True
    assert "主定理" in result["corrected_srt"]
    assert result["meta"]["dynamic_term_count"] == 1
    assert result["meta"]["candidate_term_count"] == 1


@pytest.mark.asyncio
async def test_adaptive_correct_uses_candidate_mapping_as_weak_evidence(tmp_path):
    store = DynamicKnowledgeStore(base_path=str(tmp_path / "current"))
    knowledge_service = FakeDynamicKnowledgeService(store=store)
    material = tmp_path / "first.pptx"
    material.write_text("fake", encoding="utf-8")
    knowledge_service.upload_material(str(material), "first.pptx")
    adaptive = AdaptiveSRTService(knowledge_service=knowledge_service)
    adaptive.threshold_adaptor.threshold = 0.35

    srt = "1\n00:00:00,000 --> 00:00:01,000\n这里可以用带入法求解递归式\n"
    result = await adaptive.correct_current(srt)

    assert result["success"] is True
    assert "代入法" in result["corrected_srt"]
    assert result["meta"]["candidate_asr_mapping_count"] == 1
