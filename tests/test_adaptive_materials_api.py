import sys

from fastapi.testclient import TestClient

sys.path.insert(0, "d:/Mycode/算法_agent/algorithm_agent")

from app.api import adaptive_materials
from app.main import app


class FakeKnowledgeService:
    def upload_materials(self, files, enable_supplement=True, supplement_limit=30):
        return {
            "uploaded": len(files),
            "active_domain": "dynamic_current",
            "added_terms": 1,
            "added_asr_mappings": 1,
            "added_candidate_terms": 1 if enable_supplement else 0,
            "added_candidate_asr_mappings": 1 if enable_supplement else 0,
            "total_terms": 1,
            "total_asr_mappings": 1,
            "total_candidate_terms": 1 if enable_supplement else 0,
            "total_candidate_asr_mappings": 1 if enable_supplement else 0,
            "version": 1,
            "supplement_limit": supplement_limit,
        }

    def get_stats(self):
        return {
            "active_domain": "dynamic_current",
            "material_count": 1,
            "term_count": 1,
            "asr_mapping_count": 1,
            "candidate_term_count": 1,
            "candidate_asr_mapping_count": 1,
            "pinyin_count": 1,
            "materials": [],
            "course_profile": {},
            "version": 1,
        }

    def get_candidates(self):
        return {
            "candidate_terms": {"代入法": {"term": "代入法"}},
            "candidate_asr_mapping": {},
            "course_profile": {},
            "candidate_term_count": 1,
            "candidate_asr_mapping_count": 0,
        }

    def reset(self):
        return {
            "active_domain": "dynamic_current",
            "term_count": 0,
            "asr_mapping_count": 0,
            "candidate_term_count": 0,
            "candidate_asr_mapping_count": 0,
            "material_count": 0,
            "version": 2,
        }


def test_adaptive_materials_api_upload_stats_candidates_reset(monkeypatch):
    monkeypatch.setattr(adaptive_materials, "get_dynamic_knowledge_service", lambda: FakeKnowledgeService())
    client = TestClient(app)

    upload = client.post(
        "/api/v1/adaptive/materials/upload",
        data={"enable_supplement": "true", "supplement_limit": "20"},
        files=[("files", ("course.pptx", b"fake", "application/vnd.openxmlformats-officedocument.presentationml.presentation"))],
    )
    stats = client.get("/api/v1/adaptive/materials/stats")
    candidates = client.get("/api/v1/adaptive/materials/candidates")
    reset = client.post("/api/v1/adaptive/materials/reset")

    assert upload.status_code == 200
    assert upload.json()["data"]["uploaded"] == 1
    assert upload.json()["data"]["added_candidate_terms"] == 1
    assert stats.status_code == 200
    assert stats.json()["data"]["term_count"] == 1
    assert candidates.status_code == 200
    assert candidates.json()["data"]["candidate_term_count"] == 1
    assert reset.status_code == 200
    assert reset.json()["data"]["candidate_term_count"] == 0
