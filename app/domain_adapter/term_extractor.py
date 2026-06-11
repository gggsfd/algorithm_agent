import json
from typing import Any


ATE_PROMPT = """你是专业术语提取专家。请从以下教材内容中提取专业术语。

要求：
1. 提取专有名词、技术术语、核心概念、算法名称、理论名词
2. 对每个术语提供：定义（50字内）、类别（算法/数据结构/理论/工具）、重要性（1-5分）
3. 按重要性降序排列

输出格式（严格 JSON 对象，terms 字段为数组）：
{{
  "terms": [
    {{"term": "动态规划", "definition": "通过分解子问题求解最优解的算法范式", "category": "algorithm", "importance": 5}}
  ]
}}

教材内容：
{text}
"""


class TermExtractor:
    def __init__(self, llm_client: Any):
        self.llm = llm_client

    def extract(self, text: str, model: str = "deepseek-chat") -> list[dict]:
        all_terms = []
        for chunk in self._chunk_text(text, chunk_size=8000):
            prompt = ATE_PROMPT.format(text=chunk)
            response = self.llm.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是专业术语提取专家。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            terms = self._parse_json(response.choices[0].message.content)
            if terms:
                all_terms.extend(terms)
        return self._deduplicate(all_terms)

    def _parse_json(self, response_text: str) -> list[dict] | None:
        try:
            data = json.loads(response_text.strip())
        except (json.JSONDecodeError, AttributeError):
            return None
        if isinstance(data, dict) and isinstance(data.get("terms"), list):
            return [item for item in data["terms"] if isinstance(item, dict) and item.get("term")]
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict) and item.get("term")]
        return None

    def _chunk_text(self, text: str, chunk_size: int = 8000) -> list[str]:
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size) if text[i:i + chunk_size].strip()]

    def _deduplicate(self, terms: list[dict]) -> list[dict]:
        seen = set()
        result = []
        for item in terms:
            term = str(item.get("term", "")).strip()
            if not term or term in seen:
                continue
            seen.add(term)
            result.append({
                "term": term,
                "definition": item.get("definition", ""),
                "category": item.get("category", ""),
                "importance": int(item.get("importance", 1) or 1),
            })
        return result
