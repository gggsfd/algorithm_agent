import re
from typing import List, Dict
from app.core.exceptions import SRTParseError


class SRTParseResult:
    def __init__(self, items: List[Dict], original_length: int):
        self.items = items
        self.original_length = original_length

    def __len__(self):
        return len(self.items)

    def to_json(self) -> List[Dict]:
        return self.items


class SRTParser:
    BLOCK_PATTERN = re.compile(
        r'(\d+)\s*\r?\n'
        r'(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*'
        r'(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*\r?\n'
        r'((?:.*?\r?\n)*?)(?=\r?\n\d+\s*\r?\n|\Z)',
        re.MULTILINE
    )
    TIMELINE_PATTERN = re.compile(r'\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,\.]\d{3}')

    @staticmethod
    def _normalize_newlines(srt_content: str) -> str:
        return srt_content.replace('\r\n', '\n').replace('\r', '\n')

    def parse(self, srt_content: str) -> SRTParseResult:
        if not srt_content or not srt_content.strip():
            raise SRTParseError("SRT content is empty")

        normalized_content = self._normalize_newlines(srt_content)
        items = []
        matches = self.BLOCK_PATTERN.findall(normalized_content)

        if not matches:
            raise SRTParseError("Invalid SRT format: no valid subtitle blocks found")

        for match in matches:
            subtitle_id = int(match[0])
            timestamp_start = match[1]
            timestamp_end = match[2]
            text_lines = [line.strip() for line in match[3].strip().split('\n') if line.strip()]

            if not text_lines:
                continue

            items.append({
                "id": subtitle_id,
                "text": " ".join(text_lines),
                "_timestamp_start": timestamp_start,
                "_timestamp_end": timestamp_end,
            })

        if not items:
            raise SRTParseError("Invalid SRT format: no valid subtitle blocks found")

        if len(items) == 1:
            timeline_count = len(self.TIMELINE_PATTERN.findall(normalized_content))
            if timeline_count >= 2:
                raise SRTParseError("Invalid SRT format: block split failed")

        return SRTParseResult(items=items, original_length=len(items))

    def parse_to_timeline(self, srt_content: str) -> List[Dict]:
        items = self.parse(srt_content)
        result = []
        for item in items.items:
            result.append({
                "id": item["id"],
                "timestamp_start": item["_timestamp_start"],
                "timestamp_end": item["_timestamp_end"],
                "text": item["text"]
            })
        return result
