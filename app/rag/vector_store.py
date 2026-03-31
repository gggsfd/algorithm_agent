import os
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from app.rag.pinyin_converter import PinyinConverter
from scripts.import_terms import get_term_library, TermLibrary


class VectorStore:
    def __init__(self, persist_dir: str = "./data/vector_store"):
        self.persist_dir = persist_dir
        self.pinyin_converter = PinyinConverter()
        self.term_library = get_term_library()
        self.term_index: Dict[str, Dict] = {}
        self.pinyin_to_term: Dict[str, List[str]] = {}
        self._ensure_dir()

    def _ensure_dir(self):
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)

    def build_index(self):
        self.term_index = self.term_library.get_pinyin_index()
        self.pinyin_to_term.clear()

        for term, data in self.term_index.items():
            pinyin = data.get("pinyin", "")
            if pinyin:
                if pinyin not in self.pinyin_to_term:
                    self.pinyin_to_term[pinyin] = []
                self.pinyin_to_term[pinyin].append(term)

        for pinyin, terms in self.pinyin_to_term.items():
            self.pinyin_to_term[pinyin] = list(set(terms))

    def save_index(self, filename: str = "pinyin_index.json"):
        index_path = os.path.join(self.persist_dir, filename)

        index_data = {
            "term_index": {},
            "pinyin_to_term": self.pinyin_to_term,
            "term_count": len(self.term_index)
        }

        for term, data in self.term_index.items():
            index_data["term_index"][term] = {
                "pinyin": data.get("pinyin", ""),
                "first_letters": data.get("first_letters", ""),
                "original": data.get("original", term),
                "info": data.get("info", {}),
                "is_asr_error": data.get("is_asr_error", False),
                "correct_term": data.get("correct_term", "")
            }

        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)

        return index_path

    def load_index(self, filename: str = "pinyin_index.json") -> bool:
        index_path = os.path.join(self.persist_dir, filename)

        if not os.path.exists(index_path):
            return False

        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)

            self.term_index.clear()
            for term, data in index_data.get("term_index", {}).items():
                self.term_index[term] = data

            self.pinyin_to_term = index_data.get("pinyin_to_term", {})

            return True
        except Exception:
            return False

    def search_by_pinyin(self, query: str, top_k: int = 5) -> List[Tuple[str, float, Dict]]:
        query_pinyin = self.pinyin_converter.convert(query)

        if not query_pinyin:
            return []

        results = []

        if query_pinyin in self.pinyin_to_term:
            for term in self.pinyin_to_term[query_pinyin]:
                data = self.term_index.get(term, {})
                if data:
                    results.append((term, 1.0, data.get("info", {})))

        similarity_threshold = 0.5
        for pinyin, terms in self.pinyin_to_term.items():
            if pinyin == query_pinyin:
                continue

            similarity = self._calculate_similarity(query_pinyin, pinyin)
            if similarity >= similarity_threshold:
                for term in terms:
                    if term not in [r[0] for r in results]:
                        data = self.term_index.get(term, {})
                        results.append((term, similarity, data.get("info", {})))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def search_by_text(self, query: str, top_k: int = 5) -> List[Tuple[str, float, Dict]]:
        asr_correct = self.term_library.find_correct_term(query)
        if asr_correct:
            data = self.term_index.get(asr_correct, {})
            if data:
                return [(asr_correct, 1.0, data.get("info", {}))]

        return self.search_by_pinyin(query, top_k)

    def find_asr_errors(self, text: str) -> Dict[str, str]:
        result = {}

        asr_mapping = self.term_library.get_asr_mapping()

        for wrong, correct in asr_mapping.items():
            if wrong in text:
                result[wrong] = correct

        return result

    def _calculate_similarity(self, p1: str, p2: str) -> float:
        words1 = p1.split()
        words2 = p2.split()

        if not words1 or not words2:
            return 0.0

        common = 0
        for w1 in words1:
            for w2 in words2:
                if w1 == w2:
                    common += 1
                    break
                elif len(w1) > 1 and len(w2) > 1 and (w1.startswith(w2) or w2.startswith(w1)):
                    common += 0.5
                    break

        max_len = max(len(words1), len(words2))
        return common / max_len if max_len > 0 else 0.0

    def get_term_count(self) -> int:
        return len(self.term_index)

    def get_all_pinyins(self) -> List[str]:
        return list(self.pinyin_to_term.keys())


_default_vector_store: Optional[VectorStore] = None


def get_default_vector_store() -> VectorStore:
    global _default_vector_store
    if _default_vector_store is None:
        _default_vector_store = VectorStore()
        _default_vector_store.build_index()
    return _default_vector_store


def search_terms(query: str, top_k: int = 5) -> List[Tuple[str, float, Dict]]:
    return get_default_vector_store().search_by_text(query, top_k)


def find_asr_errors(text: str) -> Dict[str, str]:
    return get_default_vector_store().find_asr_errors(text)
