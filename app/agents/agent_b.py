import json
import re
import logging
from typing import Dict, List, Optional
from app.core.exceptions import AgentExecutionError

logger = logging.getLogger(__name__)


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

请返回 JSON 对象，包含 items 数组字段：
{{"items": [
    {{"id": 1, "text": "纠错后的文本"}},
    {{"id": 2, "text": "纠错后的文本"}}
]}}
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
            )

            result_text = response.choices[0].message.content
            parsed = self._parse_json_response(result_text, len(subtitle_items))
            if parsed is not None:
                return parsed
            logger.warning("Agent B JSON 解析失败，使用规则纠错")
            return self._rule_based_correction(subtitle_items, replacement_dict)

        except Exception as e:
            logger.warning(f"Agent B 执行异常: {str(e)}，使用规则纠错")
            return self._rule_based_correction(subtitle_items, replacement_dict)

    def _parse_json_response(self, response_text: str, expected_length: int) -> Optional[List[Dict]]:
        try:
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            try:
                result = json.loads(cleaned)
            except json.JSONDecodeError:
                result = self._extract_json_flexible(cleaned, expected_length)
                if result is None:
                    logger.warning(f"Agent B JSON 解析失败: 无法提取有效 JSON")
                    return None

            if isinstance(result, list):
                items = result
            elif isinstance(result, dict):
                if "items" in result:
                    items = result["items"]
                elif "corrections" in result:
                    items = result["corrections"]
                elif "results" in result:
                    items = result["results"]
                else:
                    items = list(result.values()) if all(isinstance(v, dict) for v in result.values()) else []
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
                logger.warning(f"Agent B 返回数量不匹配: 期望 {expected_length}, 实际 {len(validated_items)}")
                if expected_length > 0 and validated_items:
                    return validated_items[:expected_length]
                return None

            return validated_items

        except Exception as e:
            logger.warning(f"Agent B JSON 解析失败: {str(e)}, 原始响应: {response_text[:200]}...")
            return None

    def _extract_json_flexible(self, text: str, expected_length: int):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        patterns = [
            r'"items"\s*:\s*\[(.*?)\]\s*\}',
            r'"corrections"\s*:\s*\[(.*?)\]\s*\}',
            r'"results"\s*:\s*\[(.*?)\]\s*\}',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                bracket_content = match.group(1)
                try:
                    return json.loads("[" + bracket_content + "]")
                except json.JSONDecodeError:
                    pass

        id_text_pairs = re.findall(r'"id"\s*:\s*(\d+).*?"text"\s*:\s*"([^"]*)"', text, re.DOTALL)
        if id_text_pairs:
            items = [{"id": int(id_val), "text": text_val} for id_val, text_val in id_text_pairs]
            return items

        return None

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
