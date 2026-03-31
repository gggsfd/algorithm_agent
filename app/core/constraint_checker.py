from typing import List, Dict
from app.core.exceptions import ConstraintCheckError


class ConstraintChecker:

    def __init__(self, original_items: List[Dict]):
        self.original_items = original_items
        self._original_by_id = {item["id"]: item for item in original_items}

    def validate(self, corrected_items: List[Dict]) -> None:
        if len(corrected_items) != len(self.original_items):
            raise ConstraintCheckError(
                f"字幕数量不一致: 原始 {len(self.original_items)} 条, "
                f"纠错后 {len(corrected_items)} 条"
            )

        for item in corrected_items:
            item_id = item.get("id")
            if item_id is None:
                raise ConstraintCheckError("存在缺少 id 字段的字幕")

            if item_id not in self._original_by_id:
                raise ConstraintCheckError(f"发现未知 ID: {item_id}")

            if not item.get("text", "").strip():
                raise ConstraintCheckError(f"ID {item_id} 的文本为空")

    def restore_srt(self, corrected_items: List[Dict]) -> str:
        self.validate(corrected_items)

        corrected_by_id = {item["id"]: item for item in corrected_items}

        srt_blocks = []
        for original_item in self.original_items:
            item_id = original_item["id"]
            corrected_text = corrected_by_id[item_id]["text"]
            timestamp_start = original_item["_timestamp_start"]
            timestamp_end = original_item["_timestamp_end"]

            srt_block = f"{item_id}\n{timestamp_start} --> {timestamp_end}\n{corrected_text}"
            srt_blocks.append(srt_block)

        return "\n\n".join(srt_blocks) + "\n"

    def get_original_text(self, item_id: int) -> str:
        return self._original_by_id[item_id]["text"]

    def get_fallback_srt(self) -> str:
        srt_blocks = []
        for item in self.original_items:
            srt_block = (
                f"{item['id']}\n"
                f"{item['_timestamp_start']} --> {item['_timestamp_end']}\n"
                f"{item['text']}"
            )
            srt_blocks.append(srt_block)
        return "\n\n".join(srt_blocks) + "\n"
