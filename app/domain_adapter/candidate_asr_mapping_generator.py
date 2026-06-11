from typing import Any


class CandidateASRMappingGenerator:
    def generate(self, candidate_terms: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        mappings: dict[str, dict[str, Any]] = {}
        for item in candidate_terms:
            term = str(item.get("term", "")).strip()
            if not term:
                continue
            for confusion in item.get("likely_asr_confusions", []) or []:
                wrong = str(confusion.get("wrong", "")).strip()
                if self._is_valid_mapping(wrong, term):
                    mappings[wrong] = {
                        "wrong": wrong,
                        "correct": term,
                        "confidence": min(float(confusion.get("confidence", 0.55) or 0.55), 0.7),
                        "reason": str(confusion.get("reason", "")).strip(),
                        "source_term": term,
                        "source_type": "llm_supplement",
                        "status": "candidate",
                    }
            for wrong in self._simple_variants(term):
                if self._is_valid_mapping(wrong, term) and wrong not in mappings:
                    mappings[wrong] = {
                        "wrong": wrong,
                        "correct": term,
                        "confidence": min(float(item.get("confidence", 0.55) or 0.55), 0.62),
                        "reason": "候选术语的近似听写或截断表达",
                        "source_term": term,
                        "source_type": "local_candidate_rule",
                        "status": "candidate",
                    }
        return mappings

    def _simple_variants(self, term: str) -> set[str]:
        variants: set[str] = set()
        if len(term) >= 3:
            variants.add(term[:-1])
        replacements = {
            "树": "数",
            "图": "途",
            "式": "是",
            "法": "发",
            "界": "届",
        }
        for src, dst in replacements.items():
            if term.endswith(src) and len(term) > 2:
                variants.add(term[:-1] + dst)
        return variants

    def _is_valid_mapping(self, wrong: str, correct: str) -> bool:
        if not wrong or not correct or wrong == correct:
            return False
        if len(wrong) < 2 and not wrong.isupper():
            return False
        return True
