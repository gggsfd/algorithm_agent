import json
import re
from typing import Dict, List, Optional
from app.core.exceptions import AgentExecutionError


PROMPT_AGENT_B = """你是一个精确的字幕纠错系统。

【严格约束 - 必须遵守】
1. 只修改下面指定需要替换的词汇
2. 禁止修改标点符号
3. 禁止修改语序和句子结构
4. 禁止添加或删除任何内容
5. 只修改 text 字段
6. 如果没有匹配到任何需要替换的词，保持原样

【替换规则】
{replacement_dict}

【输入字幕】
{subtitle_items}

请返回 JSON 数组，只包含 id 和 text 字段，保持原始顺序：
[
    {{"id": 1, "text": "纠错后的文本"}},
    {{"id": 2, "text": "纠错后的文本"}}
]
"""


class AgentB:

    def __init__(self, llm_client=None, model_name: str = "deepseek-chat"):
        self.llm_client = llm_client
        self.model_name = model_name

    async def correct(self, subtitle_items: List[Dict], replacement_dict: Dict[str, str]) -> List[Dict]:
        if not replacement_dict:
            return [{"id": item["id"], "text": item["text"]} for item in subtitle_items]

        prompt = PROMPT_AGENT_B.format(
            replacement_dict=json.dumps(replacement_dict, ensure_ascii=False),
            subtitle_items=json.dumps(subtitle_items, ensure_ascii=False, indent=2)
        )

        if self.llm_client is None:
            return self._rule_based_correction(subtitle_items, replacement_dict)

        try:
            response = await self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个精确的字幕纠错助手，只按指定规则替换词汇。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result_text = response.choices[0].message.content
            return self._parse_json_response(result_text, len(subtitle_items))

        except Exception as e:
            raise AgentExecutionError(f"Agent B 执行失败: {str(e)}")

    def _parse_json_response(self, response_text: str, expected_length: int) -> List[Dict]:
        try:
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            result = json.loads(cleaned)

            if isinstance(result, list):
                items = result
            elif isinstance(result, dict) and "items" in result:
                items = result["items"]
            else:
                items = []

            validated_items = []
            for item in items:
                if isinstance(item, dict) and "id" in item and "text" in item:
                    validated_items.append({
                        "id": item["id"],
                        "text": str(item["text"])
                    })

            if len(validated_items) != expected_length:
                raise AgentExecutionError(
                    f"Agent B 返回数量不匹配: 期望 {expected_length}, 实际 {len(validated_items)}"
                )

            return validated_items

        except (json.JSONDecodeError, AgentExecutionError):
            raise AgentExecutionError("Agent B 返回格式无效")

    def _rule_based_correction(self, subtitle_items: List[Dict], replacement_dict: Dict[str, str]) -> List[Dict]:
        corrected = []
        for item in subtitle_items:
            text = item["text"]
            for wrong, correct in replacement_dict.items():
                if wrong in text:
                    text = text.replace(wrong, correct)
            corrected.append({"id": item["id"], "text": text})
        return corrected

    async def batch_correct(self, subtitle_items: List[Dict], replacement_dict: Dict[str, str]) -> List[Dict]:
        return await self.correct(subtitle_items, replacement_dict)
