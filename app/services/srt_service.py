import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from app.core.srt_parser import SRTParser, SRTParseResult
from app.core.constraint_checker import ConstraintChecker
from app.core.exceptions import ConstraintCheckError, AgentExecutionError
from app.core.task_dispatcher import TaskDispatcher
from app.agents.pipeline import CorrectionPipeline
from app.agents.term_agent import TermAgent
from app.agents.correction_agent import CorrectionAgent
from app.core.llm_config import LLMConfig, LLMClientFactory
from app.rag.retrieval import get_default_engine
from app.schemas.domain import Domain, is_supported_domain
from app.schemas.correction_mode import CorrectionMode
from app.agents.evidence_collector import EvidenceCollector


logger = logging.getLogger(__name__)


class SRTService:
    TERM_AGENT_MIN_CONFIDENCE = 0.65


    def __init__(self, llm_client=None, use_agent: bool = False, default_domain: str = Domain.ALGORITHM.value):
        self.parser = SRTParser()
        self.use_agent = use_agent
        self.llm_client = llm_client
        self.default_domain = default_domain
        self.llm_config = LLMConfig.from_env()
        self._pipeline = None
        self._correction_pipeline = None
        self.agent_available = bool(self.llm_config.agent_a_api_key and self.llm_config.agent_b_api_key)
        if use_agent and self.agent_available:
            self._pipeline = self._create_agent_pipeline()

    def _create_agent_pipeline(self) -> CorrectionPipeline:
        term_agent, correction_agent = self._build_agents()
        return CorrectionPipeline(
            term_agent=term_agent,
            correction_agent=correction_agent,
            domain=self.default_domain,
            use_evidence=False,
        )

    def _build_agents(self) -> Tuple[TermAgent, CorrectionAgent]:
        term_client, correction_client = LLMClientFactory.create_clients()
        term_agent = TermAgent(
            llm_client=term_client,
            model_name=self.llm_config.agent_a_model,
            domain=self.default_domain,
            min_confidence=self.TERM_AGENT_MIN_CONFIDENCE,
        )
        correction_agent = CorrectionAgent(
            llm_client=correction_client,
            model_name=self.llm_config.agent_b_model,
            validate=True,
        )
        return term_agent, correction_agent

    def parse_srt(self, srt_content: str) -> SRTParseResult:
        return self.parser.parse(srt_content)

    def correct_subtitles(self, items: List[Dict], domain: Optional[str] = None) -> List[Dict]:
        mode = CorrectionMode.HYBRID if self.use_agent else CorrectionMode.RULE
        corrected, _, _ = self._correct_items_by_mode_sync(items, mode=mode, domain=domain)
        return corrected

    async def correct_subtitles_async(self, items: List[Dict], domain: Optional[str] = None) -> List[Dict]:
        mode = CorrectionMode.HYBRID if self.use_agent else CorrectionMode.RULE
        corrected, _, _ = await self._correct_items_by_mode_async(items, mode=mode, domain=domain)
        return corrected

    def _normalize_mode(self, mode: str | CorrectionMode) -> CorrectionMode:
        if isinstance(mode, CorrectionMode):
            return mode
        try:
            return CorrectionMode(mode)
        except ValueError as exc:
            raise ValueError(f"Unsupported correction mode: {mode}") from exc

    def _ensure_pipeline(self) -> CorrectionPipeline:
        if self._pipeline:
            return self._pipeline
        if not self.agent_available:
            raise ValueError("Agent mode unavailable: missing api key")
        self._pipeline = self._create_agent_pipeline()
        return self._pipeline

    def _correct_by_rule(self, items: List[Dict], domain: Optional[str] = None) -> List[Dict]:
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

    def _correct_by_agent_sync(self, items: List[Dict]) -> List[Dict]:
        pipeline = self._ensure_pipeline()
        corrected, _, _ = asyncio.run(pipeline.process_async(items))
        return corrected

    async def _correct_by_agent_async(self, items: List[Dict]) -> List[Dict]:
        pipeline = self._ensure_pipeline()
        corrected, _, _ = await pipeline.process_async(items)
        return corrected

    def _ensure_correction_pipeline(self) -> CorrectionPipeline:
        if self._correction_pipeline:
            return self._correction_pipeline
        if not self.agent_available:
            raise ValueError("Hybrid mode unavailable: missing api key")

        term_agent, correction_agent = self._build_agents()
        self._correction_pipeline = CorrectionPipeline(
            term_agent=term_agent,
            correction_agent=correction_agent,
            domain=self.default_domain,
            use_evidence=True,
        )
        return self._correction_pipeline

    def _correct_by_hybrid_sync(self, items: List[Dict]) -> Tuple[List[Dict], str, bool]:
        pipeline = self._ensure_correction_pipeline()
        corrected, effective_mode, degraded = asyncio.run(pipeline.process_async(items))
        return corrected, effective_mode, degraded

    async def _correct_by_hybrid_async(self, items: List[Dict]) -> Tuple[List[Dict], str, bool]:
        pipeline = self._ensure_correction_pipeline()
        corrected, effective_mode, degraded = await pipeline.process_async(items)
        return corrected, effective_mode, degraded

    def _correct_items_by_mode_sync(
        self,
        items: List[Dict],
        mode: str | CorrectionMode = CorrectionMode.RULE,
        domain: Optional[str] = None
    ) -> Tuple[List[Dict], str, bool]:
        normalized_mode = self._normalize_mode(mode)
        if normalized_mode == CorrectionMode.RULE:
            return self._correct_by_rule(items, domain), CorrectionMode.RULE.value, False
        if normalized_mode == CorrectionMode.AGENT:
            try:
                return self._correct_by_agent_sync(items), CorrectionMode.AGENT.value, False
            except (RuntimeError, TimeoutError, AgentExecutionError, ValueError) as e:
                logger.warning(f"Agent mode failed: {e}, fallback to rule mode")
                return self._correct_by_rule(items, domain), CorrectionMode.RULE.value, True
        if normalized_mode in (CorrectionMode.HYBRID, CorrectionMode.HYBRID_AUTO):
            try:
                return self._correct_by_hybrid_sync(items)
            except (RuntimeError, TimeoutError, AgentExecutionError, ValueError) as e:
                logger.warning(f"Hybrid mode failed: {e}, fallback to rule mode")
                return self._correct_by_rule(items, domain), CorrectionMode.RULE.value, True
        raise ValueError(f"Unsupported correction mode: {normalized_mode}")

    async def _correct_items_by_mode_async(
        self,
        items: List[Dict],
        mode: str | CorrectionMode = CorrectionMode.RULE,
        domain: Optional[str] = None
    ) -> Tuple[List[Dict], str, bool]:
        normalized_mode = self._normalize_mode(mode)
        if normalized_mode == CorrectionMode.RULE:
            return self._correct_by_rule(items, domain), CorrectionMode.RULE.value, False
        if normalized_mode == CorrectionMode.AGENT:
            try:
                return await self._correct_by_agent_async(items), CorrectionMode.AGENT.value, False
            except (RuntimeError, TimeoutError, AgentExecutionError, ValueError) as e:
                logger.warning(f"Agent mode failed: {e}, fallback to rule mode")
                return self._correct_by_rule(items, domain), CorrectionMode.RULE.value, True
        if normalized_mode in (CorrectionMode.HYBRID, CorrectionMode.HYBRID_AUTO):
            try:
                return await self._correct_by_hybrid_async(items)
            except (RuntimeError, TimeoutError, AgentExecutionError, ValueError) as e:
                logger.warning(f"Hybrid mode failed: {e}, fallback to rule mode")
                return self._correct_by_rule(items, domain), CorrectionMode.RULE.value, True
        raise ValueError(f"Unsupported correction mode: {normalized_mode}")

    def _resolve_domain(self, domain: Optional[str]) -> str:
        target_domain = domain or self.default_domain
        if not is_supported_domain(target_domain):
            raise ValueError(f"Unsupported domain: {target_domain}")
        return target_domain

    def _apply_corrections(self, text: str, domain: Optional[str] = None) -> str:
        target_domain = self._resolve_domain(domain)
        correction_map = get_default_engine(domain=target_domain).get_correction_dict(text)
        result = text
        for wrong, correct in EvidenceCollector.RULE_BASED_CORRECTIONS.items():
            if wrong in result:
                result = result.replace(wrong, correct)
        for wrong, correct in sorted(correction_map.items(), key=lambda item: len(item[0]), reverse=True):
            if wrong in result:
                result = result.replace(wrong, correct)
        return result

    def process_srt(
        self,
        srt_content: str,
        domain: Optional[str] = None,
        correction_mode: str | CorrectionMode = CorrectionMode.RULE
    ) -> tuple[str, bool, Dict]:
        original_result = self.parser.parse(srt_content)

        checker = ConstraintChecker(original_result.items)

        normalized_mode = self._normalize_mode(correction_mode)
        corrected_items, effective_mode, degraded = self._correct_items_by_mode_sync(
            original_result.items,
            mode=normalized_mode,
            domain=domain
        )

        try:
            checker.validate(corrected_items)
            final_srt = checker.restore_srt(corrected_items)
            return final_srt, True, {
                "correction_mode": normalized_mode.value,
                "effective_mode": effective_mode,
                "degraded": degraded,
            }
        except ConstraintCheckError:
            fallback_srt = checker.get_fallback_srt()
            return fallback_srt, False, {
                "correction_mode": normalized_mode.value,
                "effective_mode": effective_mode,
                "degraded": degraded,
            }

    async def process_srt_async(
        self,
        srt_content: str,
        domain: Optional[str] = None,
        correction_mode: str | CorrectionMode = CorrectionMode.RULE
    ) -> tuple[str, bool, Dict]:
        original_result = self.parser.parse(srt_content)

        checker = ConstraintChecker(original_result.items)

        normalized_mode = self._normalize_mode(correction_mode)
        corrected_items, effective_mode, degraded = await self._correct_items_by_mode_async(
            original_result.items,
            mode=normalized_mode,
            domain=domain
        )

        try:
            checker.validate(corrected_items)
            final_srt = checker.restore_srt(corrected_items)
            return final_srt, True, {
                "correction_mode": normalized_mode.value,
                "effective_mode": effective_mode,
                "degraded": degraded,
            }
        except ConstraintCheckError:
            fallback_srt = checker.get_fallback_srt()
            return fallback_srt, False, {
                "correction_mode": normalized_mode.value,
                "effective_mode": effective_mode,
                "degraded": degraded,
            }

    async def process_srt_batch(
        self,
        srt_content: str,
        chunk_size: int = 20,
        overlap: int = 5,
        domain: Optional[str] = None,
        correction_mode: str | CorrectionMode = CorrectionMode.RULE
    ) -> tuple[str, bool, Dict]:
        original_result = self.parser.parse(srt_content)
        checker = ConstraintChecker(original_result.items)
        normalized_mode = self._normalize_mode(correction_mode)
        degraded_in_chunks = False
        effective_mode = normalized_mode.value

        dispatcher = TaskDispatcher(
            chunk_size=chunk_size,
            overlap_size=overlap,
            max_concurrency=5
        )

        async def process_chunk_handler(items: List[Dict]) -> List[Dict]:
            nonlocal degraded_in_chunks, effective_mode
            corrected, chunk_effective_mode, chunk_degraded = await self._correct_items_by_mode_async(
                items,
                mode=normalized_mode,
                domain=domain
            )
            if chunk_degraded:
                degraded_in_chunks = True
            effective_mode = self._merge_effective_mode(effective_mode, chunk_effective_mode)
            return corrected

        corrected_items, success = await dispatcher.process_chunks_async(
            original_result.items,
            process_chunk_handler
        )

        try:
            checker.validate(corrected_items)
            final_srt = checker.restore_srt(corrected_items)
            return final_srt, success, {
                "correction_mode": normalized_mode.value,
                "effective_mode": effective_mode,
                "degraded": degraded_in_chunks,
            }
        except ConstraintCheckError:
            fallback_srt = checker.get_fallback_srt()
            return fallback_srt, False, {
                "correction_mode": normalized_mode.value,
                "effective_mode": effective_mode,
                "degraded": degraded_in_chunks,
            }

    def get_timeline(self, srt_content: str) -> List[Dict]:
        return self.parser.parse_to_timeline(srt_content)

    def _merge_effective_mode(self, current: str, incoming: str) -> str:
        if current == CorrectionMode.RULE.value:
            return current
        if incoming == CorrectionMode.RULE.value:
            return incoming
        if incoming == "partial" and current != CorrectionMode.RULE.value:
            return "partial"
        return current

    async def process_srt_robust(
        self,
        srt_content: str,
        chunk_size: int = 20,
        overlap: int = 5,
        max_retries: int = 3,
        domain: Optional[str] = None,
        correction_mode: str | CorrectionMode = CorrectionMode.RULE
    ) -> tuple[str, bool, Dict, Dict]:
        from app.core.task_dispatcher import EnhancedTaskDispatcher
        from app.core.retry_handler import RetryConfig
        from app.core.circuit_breaker import CircuitBreakerConfig

        original_result = self.parser.parse(srt_content)
        checker = ConstraintChecker(original_result.items)
        normalized_mode = self._normalize_mode(correction_mode)
        degraded_in_chunks = False
        effective_mode = normalized_mode.value

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
            nonlocal degraded_in_chunks, effective_mode
            corrected, chunk_effective_mode, chunk_degraded = await self._correct_items_by_mode_async(
                items,
                mode=normalized_mode,
                domain=domain
            )
            if chunk_degraded:
                degraded_in_chunks = True
            effective_mode = self._merge_effective_mode(effective_mode, chunk_effective_mode)
            return corrected

        corrected_items, success, stats = await dispatcher.process_chunks_with_retry(
            original_result.items,
            process_chunk_handler
        )

        try:
            checker.validate(corrected_items)
            final_srt = checker.restore_srt(corrected_items)
            return final_srt, success, stats, {
                "correction_mode": normalized_mode.value,
                "effective_mode": effective_mode,
                "degraded": degraded_in_chunks,
            }
        except ConstraintCheckError:
            fallback_srt = checker.get_fallback_srt()
            return fallback_srt, False, stats, {
                "correction_mode": normalized_mode.value,
                "effective_mode": effective_mode,
                "degraded": degraded_in_chunks,
            }
