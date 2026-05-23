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
    }

    def __init__(
        self,
        domain: str = Domain.ALGORITHM.value,
        rag_threshold: float = 0.85,
        pinyin_threshold: float = 0.75,
    ):
        self.domain = domain
        self.rag_threshold = rag_threshold
        self.pinyin_threshold = pinyin_threshold
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
                    confidence=self.CONFIDENCE_WEIGHTS["dict"],
                    method="hardcoded_mapping",
                )

        for wrong, correct in self._engine.get_correction_dict(text).items():
            if wrong not in candidates and wrong != correct:
                candidates[wrong] = CandidateCorrection(
                    correct=correct,
                    source="dict",
                    confidence=self.CONFIDENCE_WEIGHTS["dict"],
                    method="hardcoded_mapping",
                )

        asr_errors = self._vector_store.find_asr_errors(text)
        for wrong, correct in asr_errors.items():
            if wrong not in candidates and wrong != correct:
                candidates[wrong] = CandidateCorrection(
                    correct=correct,
                    source="asr_mapping",
                    confidence=self.CONFIDENCE_WEIGHTS["asr_mapping"],
                    method="asr_error_mapping",
                )

        rag_corrections = self._engine.find_errors_in_text(text)
        for wrong, correct in rag_corrections.items():
            if wrong not in candidates and wrong != correct:
                candidates[wrong] = CandidateCorrection(
                    correct=correct,
                    source="rag",
                    confidence=self.CONFIDENCE_WEIGHTS["rag"],
                    method="vector_search",
                )

        pinyin_corrections = self._collect_by_pinyin(text)
        for wrong, info in pinyin_corrections.items():
            if wrong not in candidates and wrong != info["correct"]:
                candidates[wrong] = CandidateCorrection(
                    correct=info["correct"],
                    source="pinyin",
                    confidence=info["similarity"] * self.CONFIDENCE_WEIGHTS["pinyin"],
                    method=f"pinyin_{info['method']}",
                )

        return candidates

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
