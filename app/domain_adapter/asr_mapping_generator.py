from app.rag.pinyin_converter import PinyinConverter


class PinyinASRVariantGenerator:
    def __init__(self, pinyin_converter: PinyinConverter | None = None):
        self.pinyin = pinyin_converter or PinyinConverter()

    def generate(self, term: str) -> set[str]:
        errors: set[str] = set()
        if len(term) >= 3:
            errors.add(term[:-1])
        if term.endswith("算法") and len(term) > 2:
            errors.add(term[:-2])
        if term.endswith("法") and len(term) > 2:
            errors.add(term[:-1])
        if term.endswith("树") and len(term) > 2:
            errors.add(term[:-1] + "数")
        if term.endswith("图") and len(term) > 2:
            errors.add(term[:-1] + "途")
        return errors


class MixedLanguageVariantGenerator:
    ABBREVIATION_READINGS = {
        "DP": ["地皮", "低配"],
        "DFS": ["低艾弗艾斯", "深度优先"],
        "BFS": ["比艾弗艾斯", "广度优先"],
        "API": ["诶皮艾", "接口"],
        "SQL": ["四口", "数据库查询语言"],
        "CPU": ["西皮优"],
        "GPU": ["鸡皮优"],
    }

    def generate(self, term: str) -> set[str]:
        variants: set[str] = set()
        upper_term = term.upper()
        for abbr, readings in self.ABBREVIATION_READINGS.items():
            if abbr in upper_term:
                variants.update(readings)
                variants.update(term.replace(abbr, readings[0]) for _ in [abbr])
        return variants


class LLMASRVariantGenerator:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def generate(self, terms: list[str], context: str = "", model: str = "deepseek-chat") -> dict[str, str]:
        if not self.llm_client or not terms:
            return {}
        prompt = self._build_prompt(terms, context)
        try:
            response = self.llm_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是 ASR 误识别词生成专家。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            return self._parse_response(response.choices[0].message.content)
        except Exception:
            return {}

    def _build_prompt(self, terms: list[str], context: str) -> str:
        return (
            "请基于课程上下文，为专业术语生成高质量 ASR 误识别映射。\n"
            "要求：wrong 和 correct 不能相同；不要把普通词强行映射为专业词；"
            "每个术语最多 3 个高可能误听。\n"
            "输出严格 JSON：{\"mappings\":[{\"wrong\":\"...\",\"correct\":\"...\"}]}\n\n"
            f"术语：{terms[:80]}\n\n课程上下文节选：{context[:3000]}"
        )

    def _parse_response(self, response_text: str) -> dict[str, str]:
        import json

        try:
            data = json.loads(response_text.strip())
        except (json.JSONDecodeError, AttributeError):
            return {}
        mappings = data.get("mappings", []) if isinstance(data, dict) else data
        result: dict[str, str] = {}
        if not isinstance(mappings, list):
            return result
        for item in mappings:
            if not isinstance(item, dict):
                continue
            wrong = str(item.get("wrong", "")).strip()
            correct = str(item.get("correct", "")).strip()
            if wrong and correct and wrong != correct:
                result[wrong] = correct
        return result


class ASRMappingGenerator:
    def __init__(self, pinyin_converter: PinyinConverter | None = None, llm_client=None):
        self.pinyin_strategy = PinyinASRVariantGenerator(pinyin_converter)
        self.mixed_strategy = MixedLanguageVariantGenerator()
        self.llm_strategy = LLMASRVariantGenerator(llm_client)

    def generate(self, terms: list[str], context: str = "", model: str = "deepseek-chat") -> dict[str, str]:
        mapping: dict[str, str] = {}
        for term in terms:
            for error in self._phonetic_errors(term):
                if error and error != term:
                    mapping[error] = term
            for error in self.mixed_strategy.generate(term):
                if error and error != term:
                    mapping[error] = term
        mapping.update({
            wrong: correct
            for wrong, correct in self.llm_strategy.generate(terms, context=context, model=model).items()
            if wrong and correct and wrong != correct
        })
        return mapping

    def _phonetic_errors(self, term: str) -> set[str]:
        return self.pinyin_strategy.generate(term)
