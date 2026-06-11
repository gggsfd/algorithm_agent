import asyncio
import logging
import sys
from typing import Dict, List, Optional, Tuple
from app.agents.term_agent import TermAgent
from app.agents.correction_agent import CorrectionAgent
from app.agents.evidence_collector import EvidenceCollector
from app.core.llm_config import LLMConfig
from app.schemas.domain import Domain


logger = logging.getLogger(__name__)


class CorrectionPipeline:
    MAX_TEXT_LENGTH = 3000
    MAX_ITEMS_PER_GROUP = 50
    MAX_CONCURRENT_GROUPS = 6

    def __init__(
        self,
        term_agent: TermAgent,
        correction_agent: CorrectionAgent,
        domain: str = Domain.ALGORITHM.value,
        use_evidence: bool = True,
        max_text_length: Optional[int] = None,
        evidence_collector: Optional[EvidenceCollector] = None,
    ):
        self.term_agent = term_agent
        self.correction_agent = correction_agent
        self.domain = domain
        self.use_evidence = use_evidence
        self.max_text_length = max_text_length or self.MAX_TEXT_LENGTH
        self._collector = evidence_collector if use_evidence else None
        if use_evidence and self._collector is None:
            self._collector = EvidenceCollector(domain=domain)
        self._progress_enabled = True
        self._processed_groups = 0
        self._total_groups = 0

    def _print_progress(self, current: int, total: int, stage: str, message: str):
        if not self._progress_enabled:
            return
        percent = int(current / total * 100) if total > 0 else 0
        bar_len = 30
        filled = int(bar_len * current / total) if total > 0 else 0
        bar = "#" * filled + "-" * (bar_len - filled)
        try:
            sys.stdout.write(f"\r[{bar}] {percent}% | {stage} | {message}")
            sys.stdout.flush()
        except UnicodeEncodeError:
            sys.stdout.write(f"\r[{stage}] {percent}% | {message}")
            sys.stdout.flush()
        if current >= total:
            print()

    async def process(
        self,
        subtitle_items: List[Dict],
    ) -> Tuple[List[Dict], str, bool]:
        if not subtitle_items:
            return [], "hybrid", False

        combined_text = " ".join([item.get("text", "") for item in subtitle_items])

        if len(combined_text) <= self.max_text_length:
            return await self._process_short_text(subtitle_items, combined_text)

        return await self._process_long_text(subtitle_items, combined_text)

    async def _process_short_text(
        self,
        subtitle_items: List[Dict],
        combined_text: str,
    ) -> Tuple[List[Dict], str, bool]:
        self._print_progress(
            0, 1, "Pipeline", f"处理 {len(subtitle_items)} 条字幕，字符数: {len(combined_text)}"
        )

        candidates = {}
        if self._collector:
            evidence = self._collector.collect(combined_text)
            candidates = {
                k: v for k, v in evidence.items()
                if self._passes_collection_threshold(v)
            }

        context = {"caption_text": combined_text, "candidates": candidates}
        try:
            replacements = await self.term_agent.execute(context)
        except Exception as e:
            logger.warning(f"TermAgent 执行异常: {str(e)}")
            if self._collector:
                return self._fallback_by_evidence(subtitle_items, candidates), "partial", True
            raise

        if not replacements:
            self._print_progress(1, 1, "Pipeline", "无纠错结果")
            return self._clone_items(subtitle_items), "hybrid", False

        corrected = await self.correction_agent.execute({
            "subtitle_items": subtitle_items,
            "replacement_dict": replacements,
        })

        self._print_progress(1, 1, "Pipeline", "纠错完成")
        return corrected, "hybrid", False

    async def _process_long_text(
        self,
        subtitle_items: List[Dict],
        combined_text: str,
    ) -> Tuple[List[Dict], str, bool]:
        groups = self._split_into_groups(subtitle_items, self.max_text_length)
        self._total_groups = len(groups)
        self._processed_groups = 0

        self._print_progress(0, self._total_groups, "分组", f"共 {self._total_groups} 组")

        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_GROUPS)

        async def process_group_with_semaphore(group, group_idx):
            async with semaphore:
                result = await self._process_single_group(group, group_idx)
                self._processed_groups += 1
                self._print_progress(
                    self._processed_groups,
                    self._total_groups,
                    "处理中",
                    f"完成 {self._processed_groups}/{self._total_groups} 组"
                )
                return result

        tasks = [
            process_group_with_semaphore(group, idx)
            for idx, group in enumerate(groups)
        ]

        group_results = await asyncio.gather(*tasks, return_exceptions=True)

        all_results = []
        any_partial = False

        for result in group_results:
            if isinstance(result, Exception):
                logger.error(f"Group processing failed: {result}")
                any_partial = True
                continue
            results, was_partial = result
            all_results.extend(results)
            any_partial = any_partial or was_partial

        mode = "partial" if any_partial else "hybrid"
        self._print_progress(self._total_groups, self._total_groups, "完成", "处理完毕")
        return all_results, mode, any_partial

    async def _process_single_group(
        self,
        group: List[Dict],
        group_idx: int,
    ) -> Tuple[List[Dict], bool]:
        group_text = " ".join([item["text"] for item in group])

        candidates = {}
        if self._collector:
            evidence = self._collector.collect(group_text)
            candidates = {
                k: v for k, v in evidence.items()
                if self._passes_collection_threshold(v)
            }

        context = {"caption_text": group_text, "candidates": candidates}
        try:
            replacements = await self.term_agent.execute(context)
            if not replacements:
                return [{"id": item["id"], "text": item["text"]} for item in group], False

            corrected = await self.correction_agent.execute({
                "subtitle_items": group,
                "replacement_dict": replacements,
            })
            return corrected, False
        except Exception as e:
            logger.warning(f"Group {group_idx} processing failed: {str(e)}")
            if self._collector:
                return self._fallback_by_evidence(group, candidates), True
            return [{"id": item["id"], "text": item["text"]} for item in group], True

    def _split_into_groups(
        self,
        subtitle_items: List[Dict],
        max_length: int,
    ) -> List[List[Dict]]:
        groups = []
        current_group = []
        current_length = 0

        for item in subtitle_items:
            item_length = len(item["text"])
            if (current_length + item_length > max_length or len(current_group) >= self.MAX_ITEMS_PER_GROUP) and current_group:
                groups.append(current_group)
                current_group = [item]
                current_length = item_length
            else:
                current_group.append(item)
                current_length += item_length

        if current_group:
            groups.append(current_group)

        return groups

    def _fallback_by_evidence(
        self,
        subtitle_items: List[Dict],
        candidates: Dict,
    ) -> List[Dict]:
        high_conf = {
            k: v.correct if hasattr(v, 'correct') else v.get('correct', '')
            for k, v in candidates.items()
            if hasattr(v, 'confidence') and v.confidence >= self._get_candidate_confidence_threshold()
        }
        sorted_replacements = sorted(high_conf.items(), key=lambda x: len(x[0]), reverse=True)

        corrected = []
        for item in subtitle_items:
            text = item["text"]
            for wrong, correct in sorted_replacements:
                if wrong in text:
                    text = text.replace(wrong, correct)
            corrected.append({"id": item["id"], "text": text})
        return corrected

    def _get_candidate_confidence_threshold(self) -> float:
        return getattr(self.term_agent, "min_confidence", 0.9)

    def _passes_collection_threshold(self, candidate) -> bool:
        confidence = getattr(candidate, "confidence", 0.0)
        source = str(getattr(candidate, "source", ""))
        threshold = self._get_candidate_confidence_threshold()
        if source.startswith("candidate_"):
            return confidence >= min(threshold, 0.35)
        return confidence >= threshold

    def set_min_confidence(self, value: float):
        self.term_agent.min_confidence = value

    def _clone_items(self, subtitle_items: List[Dict]) -> List[Dict]:
        return [{"id": item["id"], "text": item["text"]} for item in subtitle_items]

    async def process_async(
        self,
        subtitle_items: List[Dict],
    ) -> Tuple[List[Dict], str, bool]:
        return await self.process(subtitle_items)

    def process_sync(self, subtitle_items: List[Dict]) -> Tuple[List[Dict], str, bool]:
        if not subtitle_items:
            return [], "hybrid", False

        combined_text = " ".join([item.get("text", "") for item in subtitle_items])

        candidates = {}
        if self._collector:
            evidence = self._collector.collect(combined_text)
            candidates = {
                k: v for k, v in evidence.items()
                if self._passes_collection_threshold(v)
            }

        high_conf = {
            k: v.correct
            for k, v in candidates.items()
            if v.confidence >= self._get_candidate_confidence_threshold()
        }
        sorted_replacements = sorted(high_conf.items(), key=lambda x: len(x[0]), reverse=True)

        corrected = []
        for item in subtitle_items:
            text = item["text"]
            for wrong, correct in sorted_replacements:
                if wrong in text:
                    text = text.replace(wrong, correct)
            corrected.append({"id": item["id"], "text": text})

        if not candidates:
            return self._clone_items(subtitle_items), "hybrid", False
        return corrected, "partial", True
