import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class CourseProfileBuilder:
    def __init__(self, llm_client: Any | None = None):
        self.llm = llm_client

    def build(
        self,
        filename: str,
        text: str,
        explicit_terms: list[dict],
        existing_profile: dict[str, Any] | None = None,
        model: str = "deepseek-chat",
    ) -> dict[str, Any]:
        existing_profile = existing_profile or {}
        profile = self._build_with_llm(filename, text, explicit_terms, existing_profile, model)
        if not profile:
            profile = self._fallback_profile(filename, explicit_terms, existing_profile)
        return self._merge_profile(existing_profile, profile)

    def _build_with_llm(
        self,
        filename: str,
        text: str,
        explicit_terms: list[dict],
        existing_profile: dict[str, Any],
        model: str,
    ) -> dict[str, Any]:
        if not self.llm:
            return {}
        terms = [str(item.get("term", "")).strip() for item in explicit_terms if item.get("term")]
        prompt = (
            "你是课程知识库画像生成器。请基于文件名、材料节选、已抽取术语和已有画像，"
            "生成当前课程的结构化画像。只描述材料强相关范围，不要泛化到过大的学科。\n\n"
            "严格输出 JSON 对象，字段包括：course_domain, chapters, core_topics, term_style, "
            "language_patterns, possible_topics。\n\n"
            f"文件名：{filename}\n"
            f"已有画像：{json.dumps(existing_profile, ensure_ascii=False)[:2000]}\n"
            f"已抽取术语：{terms[:120]}\n"
            f"材料节选：{text[:4000]}"
        )
        try:
            response = self.llm.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是严谨的课程画像生成器，只输出 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            data = json.loads(response.choices[0].message.content.strip())
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    def _fallback_profile(
        self,
        filename: str,
        explicit_terms: list[dict],
        existing_profile: dict[str, Any],
    ) -> dict[str, Any]:
        stem = Path(filename).stem
        terms = [str(item.get("term", "")).strip() for item in explicit_terms if item.get("term")]
        chapters = list(existing_profile.get("chapters", []))
        if stem and stem not in chapters:
            chapters.append(stem)
        return {
            "course_domain": existing_profile.get("course_domain") or "当前课程",
            "chapters": chapters,
            "core_topics": terms[:50],
            "term_style": existing_profile.get("term_style", ["中文术语", "英文缩写", "数学符号"]),
            "language_patterns": existing_profile.get("language_patterns", []),
            "possible_topics": [],
        }

    def _merge_profile(self, existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
        merged = dict(existing)
        for key in ["chapters", "core_topics", "term_style", "language_patterns", "possible_topics"]:
            merged[key] = self._merge_list(existing.get(key, []), incoming.get(key, []))
        merged["course_domain"] = incoming.get("course_domain") or existing.get("course_domain") or "当前课程"
        merged["updated_at"] = datetime.now(timezone.utc).isoformat()
        return merged

    def _merge_list(self, left: Any, right: Any) -> list[str]:
        result: list[str] = []
        for value in list(left or []) + list(right or []):
            text = str(value).strip()
            if text and text not in result:
                result.append(text)
        return result
