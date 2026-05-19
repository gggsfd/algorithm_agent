import json
import re
import logging
import unicodedata
from typing import Dict, List, Any, Optional, Tuple
from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError

logger = logging.getLogger(__name__)


PROMPT_TEMPLATE = """你是一个精确的字幕纠错系统。

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


def normalize_text_for_comparison(text: str) -> str:
    if not text:
        return text

    normalized = text
    normalized = unicodedata.normalize('NFKC', normalized)
    normalized = normalized.replace('\u00A0', ' ')
    normalized = normalized.replace('\u3000', ' ')
    normalized = normalized.replace('\t', ' ')
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = normalized.strip()

    return normalized


def validate_modification_safety(
    original_text: str,
    corrected_text: str,
    replacement_dict: Dict[str, str],
) -> Tuple[bool, str]:
    if original_text == corrected_text:
        return True, "无修改"

    orig_norm = normalize_text_for_comparison(original_text)
    corr_norm = normalize_text_for_comparison(corrected_text)

    if orig_norm == corr_norm:
        return True, "仅空白字符规范化"

    sorted_replacements = sorted(
        replacement_dict.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )

    expected_norm = orig_norm
    for wrong, right in sorted_replacements:
        if wrong in expected_norm:
            expected_norm = expected_norm.replace(wrong, right)

    expected_norm = normalize_text_for_comparison(expected_norm)

    if expected_norm == corr_norm:
        return True, "规则替换匹配"

    if len(corr_norm) < len(orig_norm) - 5 or len(corr_norm) > len(orig_norm) + 5:
        return False, f"长度变化过大: {len(orig_norm)} -> {len(corr_norm)}"

    orig_chars = set(orig_norm.replace(' ', ''))
    corr_chars = set(corr_norm.replace(' ', ''))

    if corr_chars - orig_chars:
        added_chars = corr_chars - orig_chars
        if len(added_chars) > 3:
            return False, f"检测到新增字符: {added_chars}"

    removed_chars = orig_chars - corr_chars
    if removed_chars:
        for char in removed_chars:
            if not char.isspace() and char not in '，。！？、：；""''（）':
                if len(removed_chars) > 3:
                    return False, f"检测到删除关键字符: {removed_chars}"

    return True, "允许的微调"


class CorrectionAgent(BaseAgent):
    def __init__(
        self,
        llm_client=None,
        model_name: str = "deepseek-chat",
        validate: bool = True,
    ):
        self.llm_client = llm_client
        self.model_name = model_name
        self.validate = validate

    @property
    def name(self) -> str:
        return "CorrectionAgent"

    async def execute(self, context: Dict[str, Any]) -> List[Dict]:
        subtitle_items = context.get("subtitle_items", [])
        replacement_dict = context.get("replacement_dict", {})

        if not replacement_dict:
            return [{"id": item["id"], "text": item["text"]} for item in subtitle_items]

        prompt = PROMPT_TEMPLATE.format(
            replacement_dict=json.dumps(replacement_dict, ensure_ascii=False),
            subtitle_items=json.dumps(subtitle_items, ensure_ascii=False, indent=2)
        )

        if self.llm_client is None:
            result = self._rule_based_correction(subtitle_items, replacement_dict)
        else:
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
                    result = parsed
                else:
                    raise AgentExecutionError("CorrectionAgent JSON 解析失败，期望 {} 条，实际 {}".format(
                        len(subtitle_items), parsed))

            except Exception as e:
                raise AgentExecutionError(f"CorrectionAgent 执行异常: {str(e)}")

        if self.validate:
            validated = self._validate_corrections(subtitle_items, result, replacement_dict)
            if validated is not None:
                result = validated

        return result

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
                    logger.warning(f"CorrectionAgent JSON 解析失败: 无法提取有效 JSON")
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
                logger.warning(f"CorrectionAgent 返回数量不匹配: 期望 {expected_length}, 实际 {len(validated_items)}")
                return None

            return validated_items

        except Exception as e:
            logger.warning(f"CorrectionAgent JSON 解析失败: {str(e)}, 原始响应: {response_text[:200]}...")
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

    def _rule_based_correction(
        self,
        subtitle_items: List[Dict],
        replacement_dict: Dict[str, str],
    ) -> List[Dict]:
        sorted_replacements = sorted(
            replacement_dict.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        )
        corrected = []
        for item in subtitle_items:
            text = item["text"]
            for wrong, correct in sorted_replacements:
                if wrong in text:
                    text = text.replace(wrong, correct)
            corrected.append({"id": item["id"], "text": text})
        return corrected

    def _validate_corrections(
        self,
        original_items: List[Dict],
        corrected_items: List[Dict],
        replacement_dict: Dict[str, str],
    ) -> Optional[List[Dict]]:
        if len(original_items) != len(corrected_items):
            logger.warning(f"纠错结果长度不匹配: 期望 {len(original_items)}, 实际 {len(corrected_items)}")
            raise AgentExecutionError(f"纠错结果长度不匹配: 期望 {len(original_items)}, 实际 {len(corrected_items)}")

        for original, corrected in zip(original_items, corrected_items):
            if original["id"] != corrected["id"]:
                logger.warning(f"ID 不匹配: {original['id']} vs {corrected['id']}")
                continue

            original_text = original["text"]
            corrected_text = corrected["text"]

            if original_text == corrected_text:
                continue

            is_safe, reason = validate_modification_safety(
                original_text,
                corrected_text,
                replacement_dict,
            )

            if not is_safe:
                logger.warning(f"ID {original['id']}: 检测到非授权修改 - {reason}, 还原为原文")
                corrected["text"] = original_text

        return corrected_items