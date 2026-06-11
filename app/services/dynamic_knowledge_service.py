from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from app.core.llm_config import LLMConfig
from app.domain_adapter import DomainAdapter
from app.rag.dynamic_knowledge_store import DynamicKnowledgeStore
from app.rag.retrieval import register_engine
from app.rag.vector_store import VectorStore, get_default_vector_store


class DynamicKnowledgeService:
    ACTIVE_DOMAIN = "dynamic_current"

    def __init__(self, store: DynamicKnowledgeStore | None = None):
        self.store = store or DynamicKnowledgeStore()
        self.llm_config = LLMConfig.from_env()
        self._lock = RLock()
        self._loaded = False
        self._version = 0
        self._terms: dict[str, dict] = {}
        self._asr_mapping: dict[str, str] = {}
        self._asr_mapping_meta: dict[str, Any] = {}
        self._candidate_terms: dict[str, dict] = {}
        self._candidate_asr_mapping: dict[str, dict] = {}
        self._candidate_asr_mapping_meta: dict[str, Any] = {}
        self._course_profile: dict[str, Any] = {}
        self._materials: list[dict[str, Any]] = []

    def upload_material(
        self,
        file_path: str,
        filename: str,
        enable_supplement: bool = True,
        supplement_limit: int = 30,
    ) -> dict[str, Any]:
        with self._lock:
            self.ensure_loaded()
            before_terms = len(self._terms)
            before_asr = len(self._asr_mapping)
            before_candidate_terms = len(self._candidate_terms)
            before_candidate_asr = len(self._candidate_asr_mapping)

            evidence = self._adapt_material(file_path, filename, enable_supplement, supplement_limit)
            material_id = f"mat_{uuid4().hex[:12]}"
            stored_path = self.store.save_material_file(file_path, material_id, filename)
            self._merge_evidence(evidence, material_id)
            self._merge_candidate_evidence(evidence, material_id)

            material_record = {
                "id": material_id,
                "filename": filename,
                "file_type": Path(filename).suffix.lower().lstrip("."),
                "stored_path": stored_path,
                "text_length": evidence.get("source_text_length", 0),
                "term_count": max(0, len(self._terms) - before_terms),
                "asr_mapping_count": max(0, len(self._asr_mapping) - before_asr),
                "candidate_term_count": max(0, len(self._candidate_terms) - before_candidate_terms),
                "candidate_asr_mapping_count": max(0, len(self._candidate_asr_mapping) - before_candidate_asr),
            }
            self._materials.append(material_record)
            self._persist_and_refresh()
            return {
                "uploaded": 1,
                "active_domain": self.ACTIVE_DOMAIN,
                "added_terms": len(self._terms) - before_terms,
                "added_asr_mappings": len(self._asr_mapping) - before_asr,
                "added_candidate_terms": len(self._candidate_terms) - before_candidate_terms,
                "added_candidate_asr_mappings": len(self._candidate_asr_mapping) - before_candidate_asr,
                "total_terms": len(self._terms),
                "total_asr_mappings": len(self._asr_mapping),
                "total_candidate_terms": len(self._candidate_terms),
                "total_candidate_asr_mappings": len(self._candidate_asr_mapping),
                "material": material_record,
                "version": self._version,
            }

    def upload_materials(
        self,
        files: list[tuple[str, str]],
        enable_supplement: bool = True,
        supplement_limit: int = 30,
    ) -> dict[str, Any]:
        totals = {
            "uploaded": 0,
            "active_domain": self.ACTIVE_DOMAIN,
            "added_terms": 0,
            "added_asr_mappings": 0,
            "added_candidate_terms": 0,
            "added_candidate_asr_mappings": 0,
            "materials": [],
        }
        for path, filename in files:
            result = self.upload_material(path, filename, enable_supplement, supplement_limit)
            totals["uploaded"] += 1
            totals["added_terms"] += result["added_terms"]
            totals["added_asr_mappings"] += result["added_asr_mappings"]
            totals["added_candidate_terms"] += result["added_candidate_terms"]
            totals["added_candidate_asr_mappings"] += result["added_candidate_asr_mappings"]
            totals["materials"].append(result["material"])
        stats = self.get_stats()
        totals.update({
            "total_terms": stats["term_count"],
            "total_asr_mappings": stats["asr_mapping_count"],
            "total_candidate_terms": stats["candidate_term_count"],
            "total_candidate_asr_mappings": stats["candidate_asr_mapping_count"],
            "version": stats["version"],
        })
        return totals

    def reset(self) -> dict[str, Any]:
        with self._lock:
            manifest = self.store.reset()
            self._terms = {}
            self._asr_mapping = {}
            self._asr_mapping_meta = {}
            self._candidate_terms = {}
            self._candidate_asr_mapping = {}
            self._candidate_asr_mapping_meta = {}
            self._course_profile = {}
            self._materials = []
            self._version += 1
            vector_store = get_default_vector_store(domain=self.ACTIVE_DOMAIN)
            vector_store.clear_dynamic_terms()
            register_engine(self.ACTIVE_DOMAIN, vector_store)
            self._loaded = True
            return {
                "active_domain": self.ACTIVE_DOMAIN,
                "term_count": 0,
                "asr_mapping_count": 0,
                "candidate_term_count": 0,
                "candidate_asr_mapping_count": 0,
                "material_count": 0,
                "version": self._version,
                "manifest": manifest,
            }

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            self.ensure_loaded()
            vector_store = self.get_current_vector_store()
            runtime_stats = vector_store.get_dynamic_stats()
            return {
                "active_domain": self.ACTIVE_DOMAIN,
                "material_count": len(self._materials),
                "term_count": len(self._terms),
                "asr_mapping_count": len(self._asr_mapping),
                "candidate_term_count": len(self._candidate_terms),
                "candidate_asr_mapping_count": len(self._candidate_asr_mapping),
                "pinyin_count": runtime_stats["pinyin_count"],
                "materials": list(self._materials),
                "course_profile": dict(self._course_profile),
                "version": self._version,
            }

    def get_candidates(self) -> dict[str, Any]:
        with self._lock:
            self.ensure_loaded()
            return {
                "candidate_terms": dict(self._candidate_terms),
                "candidate_asr_mapping": dict(self._candidate_asr_mapping),
                "course_profile": dict(self._course_profile),
                "candidate_term_count": len(self._candidate_terms),
                "candidate_asr_mapping_count": len(self._candidate_asr_mapping),
            }

    def get_runtime_context(self) -> dict[str, Any]:
        with self._lock:
            self.ensure_loaded()
            vector_store = self.get_current_vector_store()
            return {
                "domain": self.ACTIVE_DOMAIN,
                "vector_store": vector_store,
                "term_count": len(self._terms),
                "asr_mapping_count": len(self._asr_mapping),
                "candidate_terms": dict(self._candidate_terms),
                "candidate_asr_mapping": dict(self._candidate_asr_mapping),
                "candidate_term_count": len(self._candidate_terms),
                "candidate_asr_mapping_count": len(self._candidate_asr_mapping),
                "version": self._version,
            }

    def get_current_vector_store(self) -> VectorStore:
        vector_store = get_default_vector_store(domain=self.ACTIVE_DOMAIN)
        register_engine(self.ACTIVE_DOMAIN, vector_store)
        return vector_store

    def ensure_loaded(self):
        if self._loaded:
            return
        state = self.store.load_state()
        self._terms = state.get("terms", {}) or {}
        self._asr_mapping = state.get("asr_mapping", {}) or {}
        self._asr_mapping_meta = state.get("asr_mapping_meta", {}) or {}
        self._candidate_terms = state.get("candidate_terms", {}) or {}
        self._candidate_asr_mapping = state.get("candidate_asr_mapping", {}) or {}
        self._candidate_asr_mapping_meta = state.get("candidate_asr_mapping_meta", {}) or {}
        self._course_profile = state.get("course_profile", {}) or {}
        self._materials = state.get("manifest", {}).get("materials", []) or []
        self._refresh_runtime()
        self._loaded = True

    def _adapt_material(
        self,
        file_path: str,
        filename: str,
        enable_supplement: bool = True,
        supplement_limit: int = 30,
    ) -> dict:
        if not self.llm_config.agent_a_api_key:
            raise ValueError("上传课程材料需要配置 LLM API Key")
        adapter = DomainAdapter(api_key=self.llm_config.agent_a_api_key, base_url=self.llm_config.base_url)
        return adapter.adapt_from_document(
            file_path,
            filename=filename,
            model=self.llm_config.agent_a_model,
            enable_supplement=enable_supplement,
            supplement_limit=supplement_limit,
            existing_terms=self._terms,
            existing_candidates=self._candidate_terms,
            existing_profile=self._course_profile,
        )

    def _merge_evidence(self, evidence: dict, material_id: str):
        terms = evidence.get("dict", {}) or {}
        for term, info in terms.items():
            current = self._terms.get(term, {})
            merged = {**current, **(info if isinstance(info, dict) else {"score": info})}
            materials = set(current.get("source_materials", []))
            materials.add(material_id)
            merged["source_materials"] = sorted(materials)
            self._terms[term] = merged

        asr_mapping = evidence.get("asr_mapping") or evidence.get("asr_map") or {}
        for wrong, correct in asr_mapping.items():
            if not wrong or not correct or wrong == correct:
                continue
            existing = self._asr_mapping.get(wrong)
            if existing and existing != correct:
                self._asr_mapping_meta.setdefault("_conflicts", []).append({
                    "wrong": wrong,
                    "existing": existing,
                    "incoming": correct,
                    "material_id": material_id,
                })
                continue
            self._asr_mapping[wrong] = correct
            meta = self._asr_mapping_meta.get(wrong, {})
            materials = set(meta.get("source_materials", []))
            materials.add(material_id)
            meta.update({"correct": correct, "source_materials": sorted(materials)})
            self._asr_mapping_meta[wrong] = meta

    def _merge_candidate_evidence(self, evidence: dict, material_id: str):
        now = datetime.now(timezone.utc).isoformat()
        if evidence.get("course_profile"):
            self._course_profile = self._merge_course_profile(self._course_profile, evidence["course_profile"])

        for item in evidence.get("candidate_terms", []) or []:
            if not isinstance(item, dict):
                continue
            term = str(item.get("term", "")).strip()
            if not term or term in self._terms:
                continue
            current = self._candidate_terms.get(term, {})
            materials = set(current.get("source_materials", []))
            materials.add(material_id)
            merged = {**current, **item}
            merged.update({
                "term": term,
                "source_materials": sorted(materials),
                "source_type": merged.get("source_type", "llm_supplement"),
                "status": merged.get("status", "candidate"),
                "hit_count": int(merged.get("hit_count", 0) or 0),
                "accepted_count": int(merged.get("accepted_count", 0) or 0),
                "rejected_count": int(merged.get("rejected_count", 0) or 0),
                "created_at": current.get("created_at") or now,
                "updated_at": now,
            })
            self._candidate_terms[term] = merged

        for wrong, info in (evidence.get("candidate_asr_mapping", {}) or {}).items():
            if not isinstance(info, dict):
                info = {"wrong": wrong, "correct": info}
            correct = str(info.get("correct", "")).strip()
            wrong = str(info.get("wrong", wrong)).strip()
            if not wrong or not correct or wrong == correct:
                continue
            if wrong in self._asr_mapping:
                continue
            if correct not in self._candidate_terms and correct not in self._terms:
                continue
            current = self._candidate_asr_mapping.get(wrong, {})
            existing_correct = current.get("correct")
            if existing_correct and existing_correct != correct:
                self._candidate_asr_mapping_meta.setdefault("_conflicts", []).append({
                    "wrong": wrong,
                    "existing": existing_correct,
                    "incoming": correct,
                    "material_id": material_id,
                })
                continue
            materials = set(current.get("source_materials", []))
            materials.add(material_id)
            merged = {**current, **info}
            merged.update({
                "wrong": wrong,
                "correct": correct,
                "source_materials": sorted(materials),
                "source_type": merged.get("source_type", "llm_supplement"),
                "status": merged.get("status", "candidate"),
                "hit_count": int(merged.get("hit_count", 0) or 0),
                "accepted_count": int(merged.get("accepted_count", 0) or 0),
                "rejected_count": int(merged.get("rejected_count", 0) or 0),
                "created_at": current.get("created_at") or now,
                "updated_at": now,
            })
            self._candidate_asr_mapping[wrong] = merged

    def _merge_course_profile(self, current: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
        merged = dict(current)
        for key, value in incoming.items():
            if isinstance(value, list):
                seen = list(merged.get(key, []) or [])
                for item in value:
                    if item not in seen:
                        seen.append(item)
                merged[key] = seen
            elif value:
                merged[key] = value
        return merged

    def _persist_and_refresh(self):
        self.store.save_state(
            terms=self._terms,
            asr_mapping=self._asr_mapping,
            asr_mapping_meta=self._asr_mapping_meta,
            candidate_terms=self._candidate_terms,
            candidate_asr_mapping=self._candidate_asr_mapping,
            candidate_asr_mapping_meta=self._candidate_asr_mapping_meta,
            course_profile=self._course_profile,
            materials=self._materials,
        )
        self._version += 1
        self._refresh_runtime()

    def _refresh_runtime(self):
        vector_store = get_default_vector_store(domain=self.ACTIVE_DOMAIN)
        vector_store.clear_dynamic_terms()
        vector_store.load_dynamic_terms(self._terms, self._asr_mapping)
        register_engine(self.ACTIVE_DOMAIN, vector_store)


_default_dynamic_knowledge_service: DynamicKnowledgeService | None = None


def get_dynamic_knowledge_service() -> DynamicKnowledgeService:
    global _default_dynamic_knowledge_service
    if _default_dynamic_knowledge_service is None:
        _default_dynamic_knowledge_service = DynamicKnowledgeService()
    return _default_dynamic_knowledge_service
