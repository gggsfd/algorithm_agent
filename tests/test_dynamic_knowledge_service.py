import sys

sys.path.insert(0, "d:/Mycode/算法_agent/algorithm_agent")

from app.rag.dynamic_knowledge_store import DynamicKnowledgeStore
from app.services.dynamic_knowledge_service import DynamicKnowledgeService


class FakeDynamicKnowledgeService(DynamicKnowledgeService):
    def _adapt_material(
        self,
        file_path: str,
        filename: str,
        enable_supplement: bool = True,
        supplement_limit: int = 30,
    ) -> dict:
        if "second" in filename:
            return {
                "dict": {
                    "主定理": {"category": "algorithm_analysis", "importance": 5},
                    "递归树": {"category": "algorithm_analysis", "importance": 4},
                },
                "asr_mapping": {"主定里": "主定理", "递归数": "递归树"},
                "candidate_terms": [
                    {
                        "term": "代入法",
                        "category": "algorithm_analysis",
                        "confidence": 0.62,
                        "reason": "递归式求解相关候选术语",
                        "related_terms": ["主定理", "递归树"],
                    }
                ] if enable_supplement else [],
                "candidate_asr_mapping": {
                    "带入法": {
                        "wrong": "带入法",
                        "correct": "代入法",
                        "confidence": 0.6,
                    }
                } if enable_supplement else {},
                "course_profile": {"course_domain": "算法设计与分析", "chapters": ["second"]},
                "source_text_length": 200,
            }
        return {
            "dict": {"主定理": {"category": "algorithm_analysis", "importance": 5}},
            "asr_mapping": {"主定里": "主定理"},
            "candidate_terms": [],
            "candidate_asr_mapping": {},
            "course_profile": {"course_domain": "算法设计与分析", "chapters": ["first"]},
            "source_text_length": 100,
        }


def test_dynamic_knowledge_upload_append_candidates_and_reset(tmp_path):
    store = DynamicKnowledgeStore(base_path=str(tmp_path / "current"))
    service = FakeDynamicKnowledgeService(store=store)
    first = tmp_path / "first.pptx"
    second = tmp_path / "second.pptx"
    first.write_text("fake", encoding="utf-8")
    second.write_text("fake", encoding="utf-8")

    result1 = service.upload_material(str(first), "first.pptx")
    result2 = service.upload_material(str(second), "second.pptx")
    stats = service.get_stats()

    assert result1["added_terms"] == 1
    assert result2["added_terms"] == 1
    assert result2["added_candidate_terms"] == 1
    assert stats["term_count"] == 2
    assert stats["asr_mapping_count"] == 2
    assert stats["candidate_term_count"] == 1
    assert stats["candidate_asr_mapping_count"] == 1
    assert stats["material_count"] == 2

    reset = service.reset()
    assert reset["term_count"] == 0
    assert reset["candidate_term_count"] == 0
    assert service.get_stats()["candidate_term_count"] == 0


def test_dynamic_knowledge_persistence_restore_candidates(tmp_path):
    store = DynamicKnowledgeStore(base_path=str(tmp_path / "current"))
    service = FakeDynamicKnowledgeService(store=store)
    material = tmp_path / "second.pptx"
    material.write_text("fake", encoding="utf-8")
    service.upload_material(str(material), "second.pptx")

    restored = DynamicKnowledgeService(store=store)
    stats = restored.get_stats()
    context = restored.get_runtime_context()

    assert stats["term_count"] == 2
    assert stats["candidate_term_count"] == 1
    assert context["domain"] == "dynamic_current"
    assert context["vector_store"].find_asr_errors("这里讲主定里") == {"主定里": "主定理"}
    assert context["candidate_terms"]["代入法"]["status"] == "candidate"
    assert context["candidate_asr_mapping"]["带入法"]["correct"] == "代入法"


def test_dynamic_knowledge_store_handles_broken_json(tmp_path):
    store = DynamicKnowledgeStore(base_path=str(tmp_path / "current"))
    (tmp_path / "current").mkdir(parents=True, exist_ok=True)
    (tmp_path / "current" / "candidate_terms.json").write_text("{broken", encoding="utf-8")

    state = store.load_state()

    assert state["candidate_terms"] == {}
    assert (tmp_path / "current" / "candidate_terms.json.broken").exists()
