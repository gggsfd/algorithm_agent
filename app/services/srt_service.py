from typing import List, Dict, Optional
from app.core.srt_parser import SRTParser, SRTParseResult
from app.core.constraint_checker import ConstraintChecker
from app.core.exceptions import ConstraintCheckError
from app.core.task_dispatcher import TaskDispatcher
from app.agents.pipeline import AgentPipeline
from app.rag.retrieval import get_default_engine
from app.schemas.domain import Domain, is_supported_domain


RULE_BASED_CORRECTIONS = {
    "欧根老根": "O(n log n)",
    "动态鬼话": "动态规划",
    "分制": "分治",
    "分制法": "分治法",
}


class SRTService:

    def __init__(self, llm_client=None, use_agent: bool = False, default_domain: str = Domain.ALGORITHM.value):
        self.parser = SRTParser()
        self.use_agent = use_agent
        self.llm_client = llm_client
        self.default_domain = default_domain
        if use_agent and llm_client:
            self.pipeline = AgentPipeline(llm_client)
        else:
            self.pipeline = None

    def parse_srt(self, srt_content: str) -> SRTParseResult:
        return self.parser.parse(srt_content)

    def correct_subtitles(self, items: List[Dict], domain: Optional[str] = None) -> List[Dict]:
        if self.pipeline:
            corrected, _ = self.pipeline.correct_subtitles_sync(items)
            return corrected
        corrected = []
        target_domain = self._resolve_domain(domain)
        for item in items:
            original_text = item["text"]
            corrected_text = self._apply_corrections(original_text, target_domain)
            corrected.append({
                "id": item["id"],
                "text": corrected_text
            })
        return corrected

    async def correct_subtitles_async(self, items: List[Dict], domain: Optional[str] = None) -> List[Dict]:
        if self.pipeline:
            corrected, _ = await self.pipeline.correct_subtitles(items)
            return corrected
        corrected = []
        target_domain = self._resolve_domain(domain)
        for item in items:
            original_text = item["text"]
            corrected_text = self._apply_corrections(original_text, target_domain)
            corrected.append({
                "id": item["id"],
                "text": corrected_text
            })
        return corrected

    def _resolve_domain(self, domain: Optional[str]) -> str:
        target_domain = domain or self.default_domain
        if not is_supported_domain(target_domain):
            raise ValueError(f"Unsupported domain: {target_domain}")
        return target_domain

    def _apply_corrections(self, text: str, domain: Optional[str] = None) -> str:
        target_domain = self._resolve_domain(domain)
        correction_map = get_default_engine(domain=target_domain).get_correction_dict(text)
        result = text
        for wrong, correct in RULE_BASED_CORRECTIONS.items():
            if wrong in result:
                result = result.replace(wrong, correct)
        for wrong, correct in sorted(correction_map.items(), key=lambda item: len(item[0]), reverse=True):
            if wrong in result:
                result = result.replace(wrong, correct)
        return result

    def process_srt(self, srt_content: str, domain: Optional[str] = None) -> tuple[str, bool]:
        original_result = self.parser.parse(srt_content)

        checker = ConstraintChecker(original_result.items)

        corrected_items = self.correct_subtitles(original_result.items, domain=domain)

        try:
            checker.validate(corrected_items)
            final_srt = checker.restore_srt(corrected_items)
            return final_srt, True
        except ConstraintCheckError:
            fallback_srt = checker.get_fallback_srt()
            return fallback_srt, False

    async def process_srt_async(self, srt_content: str, domain: Optional[str] = None) -> tuple[str, bool]:
        original_result = self.parser.parse(srt_content)

        checker = ConstraintChecker(original_result.items)

        corrected_items = await self.correct_subtitles_async(original_result.items, domain=domain)

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
        overlap: int = 5,
        domain: Optional[str] = None
    ) -> tuple[str, bool]:
        original_result = self.parser.parse(srt_content)
        checker = ConstraintChecker(original_result.items)

        dispatcher = TaskDispatcher(
            chunk_size=chunk_size,
            overlap_size=overlap,
            max_concurrency=5
        )

        async def process_chunk_handler(items: List[Dict]) -> List[Dict]:
            return await self.correct_subtitles_async(items, domain=domain)

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
        max_retries: int = 3,
        domain: Optional[str] = None
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
            return await self.correct_subtitles_async(items, domain=domain)

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
