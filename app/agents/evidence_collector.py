from typing import Dict
from app.schemas.domain import Domain
from app.schemas.candidate import CandidateCorrection
from app.rag.retrieval import get_default_engine
from app.rag.pinyin_converter import PinyinConverter


class EvidenceCollector:
    RULE_BASED_CORRECTIONS = {
        "欧根老根": "O(n log n)",
        "动态鬼话": "动态规划",
        "分制": "分治",
        "分制法": "分治法",
    }

    CONFIDENCE_WEIGHTS = {
        "dict": 1.0,
        "asr_mapping": 0.95,
        "rag": 0.85,
        "pinyin": 0.70,
        "candidate_dict": 0.62,
        "candidate_asr_mapping": 0.58,
        "candidate_pinyin": 0.50,
    }

    def __init__(
        self,
        domain: str = Domain.ALGORITHM.value,
        rag_threshold: float = 0.85,
        pinyin_threshold: float = 0.75,
        confidence_weights: Dict[str, float] | None = None,
        candidate_terms: Dict[str, Dict] | None = None,
        candidate_asr_mapping: Dict[str, Dict] | None = None,
    ):
        self.domain = domain
        self.rag_threshold = rag_threshold
        self.pinyin_threshold = pinyin_threshold
        self.confidence_weights = confidence_weights or self.CONFIDENCE_WEIGHTS.copy()
        self.candidate_terms = candidate_terms or {}
        self.candidate_asr_mapping = candidate_asr_mapping or {}
        self._engine = get_default_engine(domain=domain)
        self._vector_store = self._engine.vector_store
        self._pinyin_converter = PinyinConverter()

    def collect(self, text: str) -> Dict[str, CandidateCorrection]:
        candidates: Dict[str, CandidateCorrection] = {}
        if not text:
            return candidates

        for wrong, correct in self.RULE_BASED_CORRECTIONS.items():
            if wrong in text and wrong not in candidates and wrong != correct:
                candidates[wrong] = CandidateCorrection(
                    correct=correct,
                    source="dict",
                    confidence=self._weight("dict"),
                    method="hardcoded_mapping",
                )

        asr_errors = self._vector_store.find_asr_errors(text)
        for wrong, correct in asr_errors.items():
            if wrong not in candidates and wrong != correct:
                candidates[wrong] = CandidateCorrection(
                    correct=correct,
                    source="asr_mapping",
                    confidence=self._weight("asr_mapping"),
                    method="asr_error_mapping",
                )

        for wrong, correct in self._engine.get_correction_dict(text).items():
            if wrong not in candidates and wrong != correct:
                candidates[wrong] = CandidateCorrection(
                    correct=correct,
                    source="dict",
                    confidence=self._weight("dict"),
                    method="hardcoded_mapping",
                )

        rag_corrections = self._engine.find_errors_in_text(text)
        for wrong, correct in rag_corrections.items():
            if wrong not in candidates and wrong != correct:
                candidates[wrong] = CandidateCorrection(
                    correct=correct,
                    source="rag",
                    confidence=self._weight("rag"),
                    method="vector_search",
                )

        pinyin_corrections = self._collect_by_pinyin(text)
        for wrong, info in pinyin_corrections.items():
            if wrong not in candidates and wrong != info["correct"]:
                candidates[wrong] = CandidateCorrection(
                    correct=info["correct"],
                    source="pinyin",
                    confidence=info["similarity"] * self._weight("pinyin"),
                    method=f"pinyin_{info['method']}",
                )

        candidate_asr = self._collect_candidate_asr(text)
        for wrong, info in candidate_asr.items():
            if wrong not in candidates and wrong != info["correct"]:
                candidates[wrong] = CandidateCorrection(
                    correct=info["correct"],
                    source="candidate_asr_mapping",
                    confidence=info["confidence"] * self._weight("candidate_asr_mapping"),
                    method="candidate_asr_error_mapping",
                )

        candidate_pinyin = self._collect_by_candidate_pinyin(text)
        for wrong, info in candidate_pinyin.items():
            if wrong not in candidates and wrong != info["correct"]:
                candidates[wrong] = CandidateCorrection(
                    correct=info["correct"],
                    source="candidate_pinyin",
                    confidence=info["similarity"] * self._weight("candidate_pinyin"),
                    method=f"candidate_pinyin_{info['method']}",
                )

        return candidates

    def _weight(self, source: str) -> float:
        return self.confidence_weights.get(source, self.CONFIDENCE_WEIGHTS.get(source, 0.5))

    def _collect_by_pinyin(self, text: str) -> Dict[str, Dict]:
        results: Dict[str, Dict] = {}
        term_dict = self._vector_store.term_index
        for i in range(len(text)):
            for length in [2, 3, 4]:
                if i + length > len(text):
                    continue
                segment = text[i:i + length]
                if segment in term_dict:
                    continue
                similar = self._pinyin_converter.find_similar_by_pinyin(
                    segment,
                    term_dict,
                    top_k=3,
                )
                if similar and similar[0][1] >= self.pinyin_threshold:
                    results[segment] = {
                        "correct": similar[0][0],
                        "similarity": similar[0][1],
                        "method": "pinyin_similarity",
                    }
        return results

    def _collect_candidate_asr(self, text: str) -> Dict[str, Dict]:
        results: Dict[str, Dict] = {}
        for wrong, info in self.candidate_asr_mapping.items():
            if wrong not in text:
                continue
            if isinstance(info, dict):
                correct = str(info.get("correct", "")).strip()
                confidence = float(info.get("confidence", 0.55) or 0.55)
            else:
                correct = str(info).strip()
                confidence = 0.55
            if correct and wrong != correct:
                results[wrong] = {"correct": correct, "confidence": max(0.0, min(1.0, confidence))}
        return results

    def _collect_by_candidate_pinyin(self, text: str) -> Dict[str, Dict]:
        results: Dict[str, Dict] = {}
        if not self.candidate_terms:
            return results
        term_dict = self._pinyin_converter.build_pinyin_index(self.candidate_terms)
        for i in range(len(text)):
            for length in [2, 3, 4]:
                if i + length > len(text):
                    continue
                segment = text[i:i + length]
                if segment in term_dict:
                    continue
                similar = self._pinyin_converter.find_similar_by_pinyin(
                    segment,
                    term_dict,
                    top_k=3,
                )
                if similar and similar[0][1] >= self.pinyin_threshold:
                    results[segment] = {
                        "correct": similar[0][0],
                        "similarity": similar[0][1],
                        "method": "pinyin_similarity",
                    }
        return results
