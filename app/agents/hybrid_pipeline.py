import asyncio
import logging
import sys
from typing import Dict, List, Optional, Tuple
from openai import AsyncOpenAI
from app.agents.evidence_collector import EvidenceCollector
from app.agents.enhanced_agent_a import EnhancedAgentA
from app.agents.enhanced_agent_b import EnhancedAgentB
from app.core.exceptions import AgentExecutionError
from app.core.llm_config import LLMConfig
from app.schemas.candidate import EvidenceReport
from app.schemas.domain import Domain


logger = logging.getLogger(__name__)


class HybridPipeline:
    MAX_TEXT_LENGTH = 2000
    MAX_CONCURRENT_GROUPS = 3

    def __init__(
        self,
        llm_config: Optional[LLMConfig] = None,
        domain: str = Domain.ALGORITHM.value,
        min_confidence: float = 0.50,
        enable_partial_fallback: bool = True,
        max_text_length: int = 2000,
    ):
        self.config = llm_config or LLMConfig.from_env()
        self.domain = domain
        self.min_confidence = min_confidence
        self.enable_partial_fallback = enable_partial_fallback
        self.max_text_length = max_text_length
        self._collector = EvidenceCollector(domain=domain)
        self.llm_available = bool(self.config.agent_a_api_key and self.config.agent_b_api_key)
        self._progress_enabled = True
        self._processed_groups = 0
        self._total_groups = 0

        client_a = None
        client_b = None
        if self.llm_available:
            client_a = AsyncOpenAI(
                api_key=self.config.agent_a_api_key,
                base_url=self.config.base_url,
            )
            client_b = AsyncOpenAI(
                api_key=self.config.agent_b_api_key,
                base_url=self.config.base_url,
            )

        self.agent_a = EnhancedAgentA(
            llm_client=client_a,
            model_name=self.config.agent_a_model,
            domain=domain,
            min_confidence=min_confidence,
        )
        self.agent_b = EnhancedAgentB(
            llm_client=client_b,
            model_name=self.config.agent_b_model,
        )

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

    async def process_chunk(
        self,
        subtitle_items: List[Dict],
    ) -> Tuple[List[Dict], str, bool]:
        if not subtitle_items:
            return [], "hybrid", False

        combined_text = " ".join([item.get("text", "") for item in subtitle_items])

        if len(combined_text) <= self.max_text_length:
            return await self._process_short_text_hybrid(subtitle_items, combined_text)

        return await self._process_long_text(subtitle_items, combined_text)

    async def _process_short_text_hybrid(
        self,
        subtitle_items: List[Dict],
        combined_text: str,
    ) -> Tuple[List[Dict], str, bool]:
        self._print_progress(
            0, 1, "Hybrid", f"处理 {len(subtitle_items)} 条字幕，字符数: {len(combined_text)}"
        )

        evidence = await self.agent_a.analyze_with_evidence(combined_text)
        if not evidence.candidates:
            self._print_progress(1, 1, "Hybrid", "无候选纠错")
            return self._clone_items(subtitle_items), "hybrid", False

        try:
            if not self.llm_available:
                self._print_progress(1, 1, "Hybrid", "LLM不可用，使用partial模式")
                return self._partial_fallback(subtitle_items, evidence), "partial", True

            replacement_dict = await self.agent_a.analyze(combined_text)
            if not replacement_dict:
                self._print_progress(1, 1, "Hybrid", "无纠错结果")
                return self._clone_items(subtitle_items), "hybrid", False

            corrected = await self.agent_b.correct(subtitle_items, replacement_dict)
            self._print_progress(1, 1, "Hybrid", "纠错完成")
            return corrected, "hybrid", False
        except Exception as e:
            logger.warning(f"Hybrid 处理异常: {str(e)}")
            self._print_progress(1, 1, "Hybrid", f"异常:{str(e)[:30]}，使用partial模式")
            return self._partial_fallback(subtitle_items, evidence), "partial", True

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
        evidence = await self.agent_a.analyze_with_evidence(group_text)

        if not evidence.candidates:
            return [{"id": item["id"], "text": item["text"]} for item in group], False

        try:
            if not self.llm_available:
                corrected = self._partial_fallback(group, evidence)
                return corrected, True

            replacement_dict = await self.agent_a.analyze(group_text)
            if not replacement_dict:
                return [{"id": item["id"], "text": item["text"]} for item in group], False

            corrected = await self.agent_b.correct(group, replacement_dict)
            return corrected, False
        except AgentExecutionError:
            corrected = self._partial_fallback(group, evidence)
            return corrected, True

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
            if current_length + item_length > max_length and current_group:
                groups.append(current_group)
                current_group = [item]
                current_length = item_length
            else:
                current_group.append(item)
                current_length += item_length

        if current_group:
            groups.append(current_group)

        return groups

    def _partial_fallback_from_text(self, text: str, evidence: EvidenceReport) -> str:
        high_conf_dict = {
            wrong: candidate.correct
            for wrong, candidate in evidence.candidates.items()
            if candidate.confidence >= 0.90
        }
        sorted_replacements = sorted(
            high_conf_dict.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        )
        result = text
        for wrong, correct in sorted_replacements:
            if wrong in result:
                result = result.replace(wrong, correct)
        return result

    def _merge_group_results(
        self,
        groups_results: List[List[Dict]],
    ) -> List[Dict]:
        merged = []
        for group in groups_results:
            merged.extend(group)
        return merged

    def process_chunk_sync(
        self,
        subtitle_items: List[Dict],
    ) -> Tuple[List[Dict], str, bool]:
        if not subtitle_items:
            return [], "hybrid", False

        combined_text = " ".join([item.get("text", "") for item in subtitle_items])
        evidence = EvidenceReport(
            candidates=self._collector.collect(combined_text),
            original_text=combined_text,
            domain=self.domain,
        )
        if not evidence.candidates:
            return self._clone_items(subtitle_items), "hybrid", False
        corrected = self._partial_fallback(subtitle_items, evidence)
        return corrected, "partial", True

    async def correct_subtitles(
        self,
        subtitle_items: List[Dict],
    ) -> Tuple[List[Dict], str, bool]:
        return await self.process_chunk(subtitle_items)

    def correct_subtitles_sync(
        self,
        subtitle_items: List[Dict],
    ) -> Tuple[List[Dict], str, bool]:
        return self.process_chunk_sync(subtitle_items)

    def _partial_fallback(
        self,
        subtitle_items: List[Dict],
        evidence: EvidenceReport,
    ) -> List[Dict]:
        high_conf_dict = {
            wrong: candidate.correct
            for wrong, candidate in evidence.candidates.items()
            if candidate.confidence >= 0.90
        }
        sorted_replacements = sorted(
            high_conf_dict.items(),
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

    def _clone_items(self, subtitle_items: List[Dict]) -> List[Dict]:
        return [{"id": item["id"], "text": item["text"]} for item in subtitle_items]
