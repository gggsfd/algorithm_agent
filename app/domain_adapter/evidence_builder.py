from app.rag.pinyin_converter import PinyinConverter


class DynamicEvidenceBuilder:
    def __init__(self, pinyin_converter: PinyinConverter | None = None):
        self.pinyin_converter = pinyin_converter or PinyinConverter()

    def build(self, terms: list[dict], asr_map: dict[str, str]) -> dict:
        term_dict = {
            item["term"]: {
                "definition": item.get("definition", ""),
                "category": item.get("category", ""),
                "importance": item.get("importance", 1),
            }
            for item in terms
            if item.get("term")
        }
        return {
            "dict": term_dict,
            "asr_map": asr_map,
            "asr_mapping": asr_map,
            "rag": {
                term: info
                for term, info in term_dict.items()
                if int(info.get("importance", 1) or 1) >= 3
            },
            "pinyin": self.pinyin_converter.build_pinyin_index(term_dict),
        }
