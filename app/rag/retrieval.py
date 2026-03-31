from typing import Dict, List, Optional, Tuple
from app.rag.vector_store import VectorStore, get_default_vector_store
from app.rag.pinyin_converter import PinyinConverter


class RetrievalEngine:
    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.vector_store = vector_store or get_default_vector_store()
        self.pinyin_converter = PinyinConverter()

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        results = self.vector_store.search_by_text(query, top_k)

        return [
            {
                "term": term,
                "similarity": similarity,
                "info": info
            }
            for term, similarity, info in results
        ]

    def batch_retrieve(self, queries: List[str], top_k: int = 5) -> Dict[str, List[Dict]]:
        results = {}
        for query in queries:
            results[query] = self.retrieve(query, top_k)
        return results

    def find_errors_in_text(self, text: str) -> Dict[str, str]:
        return self.vector_store.find_asr_errors(text)

    def process_subtitle_text(self, text: str) -> Dict[str, str]:
        errors = self.find_errors_in_text(text)

        words = text.split()
        for word in words:
            if word not in errors:
                results = self.vector_store.search_by_text(word, top_k=1)
                if results:
                    best_match = results[0]
                    if best_match["similarity"] > 0.9 and best_match["term"] != word:
                        errors[word] = best_match["term"]

        return errors

    def get_correction_dict(self, text: str) -> Dict[str, str]:
        corrections = {}

        corrections.update(self.find_errors_in_text(text))

        words = text.split()
        for word in words:
            if word not in corrections:
                results = self.vector_store.search_by_text(word, top_k=1)
                if results:
                    best = results[0]
                    if best["similarity"] > 0.95 and best["term"] != word:
                        corrections[word] = best["term"]

        return corrections


_default_engine: Optional[RetrievalEngine] = None


def get_default_engine() -> RetrievalEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = RetrievalEngine()
    return _default_engine


def retrieve_terms(query: str, top_k: int = 5) -> List[Dict]:
    return get_default_engine().retrieve(query, top_k)


def find_errors(text: str) -> Dict[str, str]:
    return get_default_engine().find_errors_in_text(text)


def get_corrections(text: str) -> Dict[str, str]:
    return get_default_engine().get_correction_dict(text)
