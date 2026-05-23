import json
import re
from typing import Dict, Any
from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError
from app.schemas.domain import DOMAIN_LABELS


PROMPT_DEFAULT = """你是一个专业领域字幕纠错专家。

【当前领域】
{domain_context}

以下是从视频字幕中提取的文本，可能存在 ASR（语音识别）错误。

请识别以下可疑的算法术语错误：
- 发音相似导致的错误（如"分制"应为"分治"，"动态鬼话"应为"动态规划"）
- 专业术语识别错误（如"O(n log n)"识别为"欧根老根"）
- 常见的算法术语错误
- 如果某个词在当前上下文中本身通顺、且没有充分证据，不要为了贴近术语库而强行替换
- 不要把普通中文词误改成算法术语，例如在语义不明确时，不要把"数"改成"树"

字幕内容：
{caption_text}

请以 JSON 格式返回可疑词和候选正确词的映射：
{{"可疑词1": "正确词1", "可疑词2": "正确词2"}}

如果没有发现明显错误，返回空字典 {{}}。
"""

PROMPT_ENHANCED = """你是一个精确的字幕纠错裁判。

【当前领域】
{domain_context}

【背景知识】
以下是从专业算法领域词典中预检索到的候选纠错列表（按置信度排序）：

{candidate_list}

【字幕原文】
{original_text}

【你的任务】
1. 结合上述候选纠错列表，判断每个候选是否应该采纳
2. 忽略置信度过低（< 0.5）或明显错误的候选
3. 如果候选列表遗漏了明显错误（如常见的音近错误），可以补充
4. 只返回确认需要替换的词对
5. 如果原文在当前语境下已经通顺，不要过度纠错，不要把普通词硬改成专业术语

【输出格式】JSON:
{{"需要替换的词1": "正确词1", "需要替换的词2": "正确词2"}}

如果没有需要替换的，返回空字典 {{}}。
"""


class TermAgent(BaseAgent):
    RULE_BASED_CORRECTIONS = {
        "欧根老根": "O(n log n)",
        "动态鬼话": "动态规划",
        "分制": "分治",
        "分制法": "分治法",
    }

    def __init__(
        self,
        llm_client=None,
        model_name: str = "deepseek-chat",
        domain: str = "algorithm",
        min_confidence: float = 0.35,
    ):
        self.llm_client = llm_client
        self.model_name = model_name
        self.domain = domain
        self.min_confidence = min_confidence

    @property
    def name(self) -> str:
        return "TermAgent"

    async def execute(self, context: Dict[str, Any]) -> Dict[str, str]:
        caption_text = context.get("caption_text", "")
        candidates = context.get("candidates", {})

        if not caption_text or not caption_text.strip():
            return {}

        if candidates and self.llm_client:
            return await self._enhanced_analyze(caption_text, candidates)

        if self.llm_client:
            return await self._default_analyze(caption_text)

        return self._rule_based_fallback(caption_text)

    async def _default_analyze(self, caption_text: str) -> Dict[str, str]:
        prompt = PROMPT_DEFAULT.format(
            caption_text=caption_text,
            domain_context=self._get_domain_context(),
        )

        try:
            response = await self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个专业的算法术语识别专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result_text = response.choices[0].message.content
            return self._parse_json_response(result_text)

        except Exception as e:
            raise AgentExecutionError(f"TermAgent 执行失败: {str(e)}")

    async def _enhanced_analyze(self, caption_text: str, candidates: Dict[str, Any]) -> Dict[str, str]:
        from app.schemas.candidate import EvidenceReport

        evidence = EvidenceReport(
            candidates=candidates,
            original_text=caption_text,
            domain=self.domain,
        )

        prompt = PROMPT_ENHANCED.format(
            candidate_list=evidence.to_prompt_text(),
            original_text=caption_text,
            domain_context=self._get_domain_context(),
        )

        try:
            response = await self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个精确的字幕纠错裁判。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result = self._parse_json_response(response.choices[0].message.content)
            if not result:
                return self._evidence_rule_based_fallback(candidates)
            return self._filter_by_confidence(result, candidates)

        except Exception as e:
            return self._evidence_rule_based_fallback(candidates)

    def _parse_json_response(self, response_text: str) -> Dict[str, str]:
        try:
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            result = json.loads(cleaned)

            if not isinstance(result, dict):
                return {}

            return {k: v for k, v in result.items() if k and v}

        except json.JSONDecodeError:
            return self._parse_text_based_response(response_text)

    def _parse_text_based_response(self, response_text: str) -> Dict[str, str]:
        pattern = r'"([^"]+)"\s*:\s*"([^"]+)"'
        matches = re.findall(pattern, response_text)
        return {k: v for k, v in matches}

    def _rule_based_fallback(self, caption_text: str) -> Dict[str, str]:
        found = {}
        for error_term, correct_term in self.RULE_BASED_CORRECTIONS.items():
            if error_term in caption_text and error_term != correct_term:
                found[error_term] = correct_term
        return found

    def _evidence_rule_based_fallback(self, candidates: Dict[str, Any]) -> Dict[str, str]:
        from app.schemas.candidate import CandidateCorrection
        result = {}
        for wrong, candidate in candidates.items():
            if isinstance(candidate, CandidateCorrection):
                if candidate.confidence >= 0.90:
                    result[wrong] = candidate.correct
            elif isinstance(candidate, dict):
                if candidate.get("confidence", 0) >= 0.90:
                    result[wrong] = candidate.get("correct", "")
        return result

    def _filter_by_confidence(
        self,
        llm_result: Dict[str, str],
        candidates: Dict[str, Any],
    ) -> Dict[str, str]:
        from app.schemas.candidate import CandidateCorrection
        result = {}
        for wrong, correct in llm_result.items():
            if wrong in candidates:
                candidate = candidates[wrong]
                if isinstance(candidate, CandidateCorrection):
                    confidence = candidate.confidence
                elif isinstance(candidate, dict):
                    confidence = candidate.get("confidence", 0)
                else:
                    confidence = 0

                if confidence >= self.min_confidence:
                    result[wrong] = correct
            else:
                result[wrong] = correct
        return result

    async def batch_execute(self, caption_items: list) -> Dict[str, str]:
        combined_text = " ".join([item.get("text", "") for item in caption_items])
        return await self.execute({"caption_text": combined_text, "candidates": {}})

    def _get_domain_context(self) -> str:
        domain_label = DOMAIN_LABELS.get(self.domain, self.domain)
        domain_notes = {
            "algorithm": "聚焦算法与数据结构语境，谨慎区分“数/树”“序/树”“回溯/回溯算法”等易混表达。",
            "medical": "聚焦医学语境，优先保持症状、药品、诊疗术语的准确性。",
            "legal": "聚焦法律语境，优先保持法条、案由、程序性表达的准确性。",
            "finance": "聚焦金融语境，优先保持指标、产品、交易术语的准确性。",
        }
        note = domain_notes.get(self.domain, "优先保持当前领域术语准确，避免脱离语境的过度纠错。")
        return f"{domain_label}。{note}"
