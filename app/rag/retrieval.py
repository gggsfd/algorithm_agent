from typing import Dict, List, Optional
from app.rag.vector_store import VectorStore, get_default_vector_store


class RetrievalEngine:
    def __init__(self, domain: str = "algorithm", vector_store: Optional[VectorStore] = None):
        self.domain = domain
        self.vector_store = vector_store or get_default_vector_store(domain=domain)

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        results = self.vector_store.search_by_text(query, top_k)

        return [
            {
                "term": term,
                "similarity": similarity,
                "info": info,
                "domain": self.domain,
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
                    if best_match[1] > 0.9 and best_match[0] != word:
                        errors[word] = best_match[0]

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
                    if best[1] > 0.95 and best[0] != word:
                        corrections[word] = best[0]

        return corrections


_default_engine: Optional[RetrievalEngine] = None
_domain_engines: Dict[str, RetrievalEngine] = {}


def get_default_engine(domain: str = "algorithm") -> RetrievalEngine:
    global _default_engine
    if domain == "algorithm":
        if _default_engine is None:
            _default_engine = RetrievalEngine(domain=domain)
        return _default_engine
    if domain not in _domain_engines:
        _domain_engines[domain] = RetrievalEngine(domain=domain)
    return _domain_engines[domain]


def retrieve_terms(query: str, top_k: int = 5, domain: str = "algorithm") -> List[Dict]:
    return get_default_engine(domain=domain).retrieve(query, top_k)


def find_errors(text: str, domain: str = "algorithm") -> Dict[str, str]:
    return get_default_engine(domain=domain).find_errors_in_text(text)


def get_corrections(text: str, domain: str = "algorithm") -> Dict[str, str]:
    return get_default_engine(domain=domain).get_correction_dict(text)
