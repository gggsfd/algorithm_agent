import json
import re
import logging
import unicodedata
from typing import Dict, List, Tuple, Optional
from app.agents.agent_b import AgentB
from app.core.exceptions import AgentExecutionError

logger = logging.getLogger(__name__)


PROMPT_ENHANCED_AGENT_B = """你是一个精确的字幕纠错系统。

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


class EnhancedAgentB(AgentB):
    def __init__(self, llm_client=None, model_name: str = "deepseek-chat"):
        super().__init__(llm_client=llm_client, model_name=model_name)

    async def correct(
        self,
        subtitle_items: List[Dict],
        replacement_dict: Dict[str, str],
    ) -> List[Dict]:
        if not replacement_dict:
            return [{"id": item["id"], "text": item["text"]} for item in subtitle_items]

        if self.llm_client is None:
            corrected = self._rule_based_correction(subtitle_items, replacement_dict)
            validated = self._validate_corrections(subtitle_items, corrected, replacement_dict)
            return validated if validated is not None else corrected

        prompt = PROMPT_ENHANCED_AGENT_B.format(
            replacement_dict=json.dumps(replacement_dict, ensure_ascii=False),
            subtitle_items=json.dumps(subtitle_items, ensure_ascii=False, indent=2),
        )

        try:
            response = await self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个精确的字幕纠错助手，严格遵守替换规则。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            result = self._parse_json_response(
                response.choices[0].message.content,
                len(subtitle_items),
            )
            if result is None:
                logger.warning("EnhancedAgentB JSON解析失败，使用规则纠错")
                return self._rule_based_correction(subtitle_items, replacement_dict)
            validated = self._validate_corrections(subtitle_items, result, replacement_dict)
            return validated if validated is not None else result
        except Exception as e:
            logger.warning(f"EnhancedAgentB 执行异常: {str(e)}，使用规则纠错")
            return self._rule_based_correction(subtitle_items, replacement_dict)

    def _validate_corrections(
        self,
        original_items: List[Dict],
        corrected_items: List[Dict],
        replacement_dict: Dict[str, str],
    ) -> Optional[List[Dict]]:
        if len(original_items) != len(corrected_items):
            logger.warning(f"纠错结果长度不匹配: 期望 {len(original_items)}, 实际 {len(corrected_items)}")
            if len(corrected_items) > 0 and len(corrected_items) < len(original_items):
                corrected_map = {item["id"]: item["text"] for item in corrected_items}
                result = []
                for orig in original_items:
                    if orig["id"] in corrected_map:
                        result.append({"id": orig["id"], "text": corrected_map[orig["id"]]})
                    else:
                        result.append({"id": orig["id"], "text": orig["text"]})
                logger.warning(f"已补全缺失条目: {len(result)}")
                return result
            raise AgentExecutionError("纠错结果长度不匹配")

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
