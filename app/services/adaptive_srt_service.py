from app.agents.correction_agent import CorrectionAgent
from app.agents.evidence_collector import EvidenceCollector
from app.agents.pipeline import CorrectionPipeline
from app.agents.term_agent import TermAgent
from app.ahcc.calibrator import HierarchicalCalibrator
from app.ahcc.feedback_store import FeedbackStore
from app.ahcc.threshold_adaptor import ThresholdAdaptor
from app.core.constraint_checker import ConstraintChecker
from app.core.llm_config import LLMClientFactory, LLMConfig
from app.rag.dynamic_knowledge_store import DynamicKnowledgeStore
from app.services.dynamic_knowledge_service import DynamicKnowledgeService, get_dynamic_knowledge_service
from app.services.srt_service import SRTService
import tempfile


class AdaptiveSRTService:
    def __init__(
        self,
        srt_service: SRTService | None = None,
        knowledge_service: DynamicKnowledgeService | None = None,
    ):
        self.srt_service = srt_service or SRTService(use_agent=True)
        self.knowledge_service = knowledge_service or get_dynamic_knowledge_service()
        self.llm_config = LLMConfig.from_env()
        self.feedback_store = FeedbackStore()
        self.calibrator = HierarchicalCalibrator(self.feedback_store)
        self.threshold_adaptor = ThresholdAdaptor(
            initial_threshold=self.srt_service.TERM_AGENT_MIN_CONFIDENCE
        )

    async def correct_current(self, srt_content: str) -> dict:
        context = self.knowledge_service.get_runtime_context()
        dynamic_domain = context["domain"]
        calibrated_weights = {
            source: self.calibrator.calibrate(source, raw_score)
            for source, raw_score in EvidenceCollector.CONFIDENCE_WEIGHTS.items()
        }

        if self.llm_config.agent_a_api_key and self.llm_config.agent_b_api_key:
            term_client, correction_client = LLMClientFactory.create_clients()
        else:
            term_client, correction_client = None, None
        term_agent = TermAgent(
            llm_client=term_client,
            model_name=self.llm_config.agent_a_model,
            domain=dynamic_domain,
            min_confidence=self.threshold_adaptor.threshold,
        )
        correction_agent = CorrectionAgent(
            llm_client=correction_client,
            model_name=self.llm_config.agent_b_model,
            validate=True,
        )
        collector = EvidenceCollector(
            domain=dynamic_domain,
            confidence_weights=calibrated_weights,
            candidate_terms=context.get("candidate_terms", {}),
            candidate_asr_mapping=context.get("candidate_asr_mapping", {}),
        )
        pipeline = CorrectionPipeline(
            term_agent=term_agent,
            correction_agent=correction_agent,
            domain=dynamic_domain,
            use_evidence=True,
            evidence_collector=collector,
        )

        parse_result = self.srt_service.parser.parse(srt_content)
        checker = ConstraintChecker(parse_result.items)
        corrected_items, effective_mode, degraded = await pipeline.process_async(parse_result.items)
        try:
            checker.validate(corrected_items)
            corrected_srt = checker.restore_srt(corrected_items)
            success = True
        except Exception:
            corrected_srt = checker.get_fallback_srt()
            success = False

        return {
            "success": success,
            "corrected_srt": corrected_srt,
            "domain": dynamic_domain,
            "meta": {
                "effective_mode": effective_mode,
                "degraded": degraded,
                "threshold": self.threshold_adaptor.threshold,
                "confidence_weights": calibrated_weights,
                "dynamic_term_count": context["term_count"],
                "dynamic_asr_mapping_count": context["asr_mapping_count"],
                "candidate_term_count": context.get("candidate_term_count", 0),
                "candidate_asr_mapping_count": context.get("candidate_asr_mapping_count", 0),
                "knowledge_version": context["version"],
            },
        }

    async def correct_with_pdf(self, srt_content: str, pdf_path: str | None = None) -> dict:
        if pdf_path:
            result = self.knowledge_service.upload_material(pdf_path, "temporary.pdf")
            corrected = await self.correct_current(srt_content)
            corrected["meta"]["material_upload"] = result
            return corrected
        return await self.correct_current(srt_content)

    async def correct_with_material(
        self,
        srt_content: str,
        material_path: str,
        filename: str,
        append_to_current: bool = False,
    ) -> dict:
        if append_to_current:
            upload = self.knowledge_service.upload_material(material_path, filename)
            corrected = await self.correct_current(srt_content)
            corrected["meta"]["material_upload"] = upload
            corrected["meta"]["append_to_current"] = True
            return corrected

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_service = DynamicKnowledgeService(
                store=DynamicKnowledgeStore(base_path=f"{tmpdir}/current")
            )
            temp_service.llm_config = self.llm_config
            upload = temp_service.upload_material(material_path, filename)
            temp_adaptive = AdaptiveSRTService(
                srt_service=self.srt_service,
                knowledge_service=temp_service,
            )
            temp_adaptive.calibrator = self.calibrator
            temp_adaptive.threshold_adaptor = self.threshold_adaptor
            corrected = await temp_adaptive.correct_current(srt_content)
            corrected["meta"]["material_upload"] = upload
            corrected["meta"]["append_to_current"] = False
            return corrected

    def submit_feedback(self, source: str, raw_score: float, calibrated_score: float, accepted: bool):
        self.calibrator.update(source, raw_score, calibrated_score, accepted)
        self.threshold_adaptor.adapt([accepted])
