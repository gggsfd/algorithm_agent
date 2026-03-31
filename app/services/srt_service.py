from typing import List, Dict, Optional
from app.core.srt_parser import SRTParser, SRTParseResult
from app.core.constraint_checker import ConstraintChecker
from app.core.exceptions import SRTParseError, ConstraintCheckError
from app.core.task_dispatcher import TaskDispatcher
from app.agents.pipeline import AgentPipeline


RULE_BASED_CORRECTIONS = {
    "欧根老根": "O(n log n)",
    "动态鬼话": "动态规划",
    "分制": "分治",
    "分制法": "分治法",
}


class SRTService:

    def __init__(self, llm_client=None, use_agent: bool = False):
        self.parser = SRTParser()
        self.use_agent = use_agent
        self.llm_client = llm_client
        if use_agent and llm_client:
            self.pipeline = AgentPipeline(llm_client)
        else:
            self.pipeline = None

    def parse_srt(self, srt_content: str) -> SRTParseResult:
        return self.parser.parse(srt_content)

    def correct_subtitles(self, items: List[Dict]) -> List[Dict]:
        if self.pipeline:
            corrected, _ = self.pipeline.correct_subtitles_sync(items)
            return corrected
        corrected = []
        for item in items:
            original_text = item["text"]
            corrected_text = self._apply_corrections(original_text)
            corrected.append({
                "id": item["id"],
                "text": corrected_text
            })
        return corrected

    async def correct_subtitles_async(self, items: List[Dict]) -> List[Dict]:
        if self.pipeline:
            corrected, _ = await self.pipeline.correct_subtitles(items)
            return corrected
        corrected = []
        for item in items:
            original_text = item["text"]
            corrected_text = self._apply_corrections(original_text)
            corrected.append({
                "id": item["id"],
                "text": corrected_text
            })
        return corrected

    def _apply_corrections(self, text: str) -> str:
        result = text
        for wrong, correct in RULE_BASED_CORRECTIONS.items():
            if wrong in result:
                result = result.replace(wrong, correct)
        return result

    def process_srt(self, srt_content: str) -> tuple[str, bool]:
        original_result = self.parser.parse(srt_content)

        checker = ConstraintChecker(original_result.items)

        corrected_items = self.correct_subtitles(original_result.items)

        try:
            checker.validate(corrected_items)
            final_srt = checker.restore_srt(corrected_items)
            return final_srt, True
        except ConstraintCheckError:
            fallback_srt = checker.get_fallback_srt()
            return fallback_srt, False

    async def process_srt_async(self, srt_content: str) -> tuple[str, bool]:
        original_result = self.parser.parse(srt_content)

        checker = ConstraintChecker(original_result.items)

        corrected_items = await self.correct_subtitles_async(original_result.items)

        try:
            checker.validate(corrected_items)
            final_srt = checker.restore_srt(corrected_items)
            return final_srt, True
        except ConstraintCheckError:
            fallback_srt = checker.get_fallback_srt()
            return fallback_srt, False

    async def process_srt_batch(
        self,
        srt_content: str,
        chunk_size: int = 20,
        overlap: int = 5
    ) -> tuple[str, bool]:
        original_result = self.parser.parse(srt_content)
        checker = ConstraintChecker(original_result.items)

        dispatcher = TaskDispatcher(
            chunk_size=chunk_size,
            overlap_size=overlap,
            max_concurrency=5
        )

        async def process_chunk_handler(items: List[Dict]) -> List[Dict]:
            return await self.correct_subtitles_async(items)

        corrected_items, success = await dispatcher.process_chunks_async(
            original_result.items,
            process_chunk_handler
        )

        try:
            checker.validate(corrected_items)
            final_srt = checker.restore_srt(corrected_items)
            return final_srt, success
        except ConstraintCheckError:
            fallback_srt = checker.get_fallback_srt()
            return fallback_srt, False

    def get_timeline(self, srt_content: str) -> List[Dict]:
        return self.parser.parse_to_timeline(srt_content)

    async def process_srt_robust(
        self,
        srt_content: str,
        chunk_size: int = 20,
        overlap: int = 5,
        max_retries: int = 3
    ) -> tuple[str, bool, Dict]:
        from app.core.task_dispatcher import EnhancedTaskDispatcher
        from app.core.retry_handler import RetryConfig
        from app.core.circuit_breaker import CircuitBreakerConfig

        original_result = self.parser.parse(srt_content)
        checker = ConstraintChecker(original_result.items)

        dispatcher = EnhancedTaskDispatcher(
            chunk_size=chunk_size,
            overlap_size=overlap,
            max_concurrency=5,
            retry_config=RetryConfig(max_retries=max_retries),
            circuit_breaker_config=CircuitBreakerConfig(
                failure_threshold=5,
                reset_timeout=60.0
            )
        )

        async def process_chunk_handler(items: List[Dict]) -> List[Dict]:
            return await self.correct_subtitles_async(items)

        corrected_items, success, stats = await dispatcher.process_chunks_with_retry(
            original_result.items,
            process_chunk_handler
        )

        try:
            checker.validate(corrected_items)
            final_srt = checker.restore_srt(corrected_items)
            return final_srt, success, stats
        except ConstraintCheckError:
            fallback_srt = checker.get_fallback_srt()
            return fallback_srt, False, stats
