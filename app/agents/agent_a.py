import json
import re
from typing import Dict, List
from app.core.exceptions import AgentExecutionError


PROMPT_AGENT_A = """你是一个专业的计算机算法术语识别专家。
以下是从视频字幕中提取的文本，可能存在 ASR（语音识别）错误。

请识别以下可疑的算法术语错误：
- 发音相似导致的错误（如"分制"应为"分治"，"动态鬼话"应为"动态规划"）
- 专业术语识别错误（如"O(n log n)"识别为"欧根老根"）
- 常见的算法术语错误

字幕内容：
{caption_text}

请以 JSON 格式返回可疑词和候选正确词的映射：
{{"可疑词1": "正确词1", "可疑词2": "正确词2"}}

如果没有发现明显错误，返回空字典 {{}}。
"""


class AgentA:

    def __init__(self, llm_client=None, model_name: str = "deepseek-chat"):
        self.llm_client = llm_client
        self.model_name = model_name

    async def analyze(self, caption_text: str) -> Dict[str, str]:
        if not caption_text or not caption_text.strip():
            return {}

        prompt = PROMPT_AGENT_A.format(caption_text=caption_text)

        if self.llm_client is None:
            return self._rule_based_fallback(caption_text)

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
            raise AgentExecutionError(f"Agent A 执行失败: {str(e)}")

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
        common_asr_errors = {
            "欧根老根": "O(n log n)",
            "动态鬼话": "动态规划",
            "分制": "分治",
            "分制法": "分治法",
            "递归": "递归",
            "算法": "算法",
        }

        found = {}
        for error_term, correct_term in common_asr_errors.items():
            if error_term in caption_text and error_term != correct_term:
                found[error_term] = correct_term

        return found

    async def batch_analyze(self, caption_items: List[Dict]) -> Dict[str, str]:
        combined_text = " ".join([item.get("text", "") for item in caption_items])
        return await self.analyze(combined_text)
