import json
from typing import Any


class SupplementTermGenerator:
    GENERIC_STOP_TERMS = {
        "方法", "过程", "问题", "结果", "内容", "情况", "系统", "数据", "模型", "结构",
        "分析", "证明", "算法", "课程", "章节", "例子", "概念",
    }

    def __init__(self, llm_client: Any | None = None):
        self.llm = llm_client

    def generate(
        self,
        course_profile: dict[str, Any],
        explicit_terms: list[dict],
        existing_terms: dict[str, Any] | None = None,
        existing_candidates: dict[str, Any] | None = None,
        limit: int = 30,
        model: str = "deepseek-chat",
    ) -> list[dict[str, Any]]:
        if not self.llm or limit <= 0:
            return []
        existing_names = set(existing_terms or {}) | set(existing_candidates or {})
        explicit_names = {
            str(item.get("term", "")).strip()
            for item in explicit_terms
            if item.get("term")
        }
        prompt = self._build_prompt(course_profile, sorted(explicit_names), sorted(existing_names), limit)
        try:
            response = self.llm.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是课程 ASR 纠错候选术语生成器，只输出 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            data = json.loads(response.choices[0].message.content.strip())
        except Exception:
            return []
        candidates = data.get("candidate_terms", []) if isinstance(data, dict) else []
        return self._normalize(candidates, existing_names | explicit_names, limit)

    def _build_prompt(
        self,
        course_profile: dict[str, Any],
        explicit_terms: list[str],
        existing_names: list[str],
        limit: int,
    ) -> str:
        return (
            "请基于当前课程画像和已显式抽取术语，补充可能被 ASR 识别错误的专业术语候选。\n"
            "要求：\n"
            "1. 只补充与当前课程材料强相关的术语。\n"
            "2. 不要生成普通词、泛化词或课程外知识。\n"
            "3. 不要重复已有术语。\n"
            "4. 每个术语给出 definition, category, confidence, reason, related_terms。\n"
            "5. confidence 范围为 0 到 1，候选词通常不要超过 0.75。\n"
            "6. 每个术语可给出 likely_asr_confusions，最多 3 个。\n"
            f"7. 最多输出 {limit} 个候选。\n\n"
            "严格输出 JSON：\n"
            '{"candidate_terms":[{"term":"...","definition":"...","category":"...",'
            '"confidence":0.62,"reason":"...","related_terms":["..."],'
            '"likely_asr_confusions":[{"wrong":"...","reason":"...","confidence":0.55}]}]}\n\n'
            f"课程画像：{json.dumps(course_profile, ensure_ascii=False)[:3000]}\n"
            f"显式术语：{explicit_terms[:120]}\n"
            f"已有正式/候选术语：{existing_names[:120]}"
        )

    def _normalize(
        self,
        candidates: Any,
        blocked_names: set[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        if not isinstance(candidates, list):
            return []
        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in candidates:
            if not isinstance(item, dict):
                continue
            term = str(item.get("term", "")).strip()
            if not self._is_valid_term(term, blocked_names, seen):
                continue
            confidence = self._clamp_float(item.get("confidence", 0.6), 0.0, 0.75)
            related_terms = [
                str(value).strip()
                for value in item.get("related_terms", [])
                if str(value).strip()
            ][:8]
            result.append({
                "term": term,
                "definition": str(item.get("definition", "")).strip(),
                "category": str(item.get("category", "")).strip() or "other",
                "confidence": confidence,
                "reason": str(item.get("reason", "")).strip(),
                "related_terms": related_terms,
                "likely_asr_confusions": self._normalize_confusions(item.get("likely_asr_confusions", [])),
                "source_type": "llm_supplement",
                "status": "candidate",
            })
            seen.add(term)
            if len(result) >= limit:
                break
        return result

    def _is_valid_term(self, term: str, blocked_names: set[str], seen: set[str]) -> bool:
        if not term or term in blocked_names or term in seen:
            return False
        if term in self.GENERIC_STOP_TERMS:
            return False
        if len(term) < 2 and not term.isupper():
            return False
        return True

    def _normalize_confusions(self, confusions: Any) -> list[dict[str, Any]]:
        if not isinstance(confusions, list):
            return []
        result = []
        for item in confusions[:3]:
            if not isinstance(item, dict):
                continue
            wrong = str(item.get("wrong", "")).strip()
            if not wrong:
                continue
            result.append({
                "wrong": wrong,
                "reason": str(item.get("reason", "")).strip(),
                "confidence": self._clamp_float(item.get("confidence", 0.55), 0.0, 0.7),
            })
        return result

    def _clamp_float(self, value: Any, low: float, high: float) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            parsed = low
        return max(low, min(high, parsed))
