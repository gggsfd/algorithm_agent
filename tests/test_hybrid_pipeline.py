import sys
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

import pytest
from app.agents.term_agent import TermAgent
from app.agents.correction_agent import CorrectionAgent
from app.agents.pipeline import CorrectionPipeline
from app.core.llm_config import LLMConfig
from app.schemas.candidate import CandidateCorrection


def build_empty_llm_config() -> LLMConfig:
    config = LLMConfig()
    config.agent_a_api_key = ""
    config.agent_b_api_key = ""
    config.agent_a_model = "deepseek-chat"
    config.agent_b_model = "deepseek-chat"
    config.base_url = "https://api.deepseek.com"
    return config


class DummyTermAgent:
    def __init__(self, min_confidence: float):
        self.min_confidence = min_confidence
        self.captured_context = None

    async def execute(self, context):
        self.captured_context = context
        return {"字典序": "字典树"}


class DummyCorrectionAgent:
    async def execute(self, context):
        return context["subtitle_items"]


def test_correction_pipeline_sync_partial_fallback():
    """测试 CorrectionPipeline 同步 partial fallback"""
    config = build_empty_llm_config()
    term_agent = TermAgent(llm_client=None, model_name=config.agent_a_model, domain="algorithm")
    correction_agent = CorrectionAgent(llm_client=None, model_name=config.agent_b_model, validate=False)

    pipeline = CorrectionPipeline(
        term_agent=term_agent,
        correction_agent=correction_agent,
        domain="algorithm",
        use_evidence=True,
    )

    items = [{"id": 1, "text": "动态鬼话和欧根老根"}]
    corrected, effective_mode, degraded = pipeline.process_sync(items)
    assert effective_mode == "partial"
    assert degraded is True
    assert "动态规划" in corrected[0]["text"]


@pytest.mark.asyncio
async def test_correction_pipeline_async_partial_fallback():
    """测试 CorrectionPipeline 在无 LLM 时仍可通过规则链路完成纠错"""
    config = build_empty_llm_config()
    term_agent = TermAgent(llm_client=None, model_name=config.agent_a_model, domain="algorithm")
    correction_agent = CorrectionAgent(llm_client=None, model_name=config.agent_b_model, validate=False)

    pipeline = CorrectionPipeline(
        term_agent=term_agent,
        correction_agent=correction_agent,
        domain="algorithm",
        use_evidence=True,
    )

    items = [{"id": 1, "text": "分制法是经典方法"}]
    corrected, effective_mode, degraded = await pipeline.process_async(items)
    assert effective_mode == "hybrid"
    assert degraded is False
    assert "分治法" in corrected[0]["text"]


@pytest.mark.asyncio
async def test_correction_pipeline_without_evidence():
    """测试 CorrectionPipeline 不使用 evidence 模式"""
    config = build_empty_llm_config()
    term_agent = TermAgent(llm_client=None, model_name=config.agent_a_model, domain="algorithm")
    correction_agent = CorrectionAgent(llm_client=None, model_name=config.agent_b_model, validate=False)

    pipeline = CorrectionPipeline(
        term_agent=term_agent,
        correction_agent=correction_agent,
        domain="algorithm",
        use_evidence=False,
    )

    items = [{"id": 1, "text": "动态鬼话和欧根老根"}]
    corrected, effective_mode, degraded = await pipeline.process_async(items)
    assert effective_mode == "hybrid"
    assert degraded is False


@pytest.mark.asyncio
async def test_correction_pipeline_uses_term_agent_threshold_for_candidates():
    term_agent = DummyTermAgent(min_confidence=0.65)
    correction_agent = DummyCorrectionAgent()

    pipeline = CorrectionPipeline(
        term_agent=term_agent,
        correction_agent=correction_agent,
        domain="algorithm",
        use_evidence=True,
    )

    pipeline._collector.collect = lambda _: {
        "字典序": CandidateCorrection(
            correct="字典树",
            source="pinyin",
            confidence=0.70,
            method="pinyin_similarity",
        ),
        "分制法": CandidateCorrection(
            correct="分治法",
            source="dict",
            confidence=0.60,
            method="hardcoded_mapping",
        ),
    }

    items = [{"id": 1, "text": "我们定义一个字典序"}]
    await pipeline.process_async(items)

    assert term_agent.captured_context is not None
    assert "字典序" in term_agent.captured_context["candidates"]
    assert "分制法" not in term_agent.captured_context["candidates"]


def test_correction_pipeline_uses_updated_default_limits():
    config = build_empty_llm_config()
    term_agent = TermAgent(llm_client=None, model_name=config.agent_a_model, domain="algorithm")
    correction_agent = CorrectionAgent(llm_client=None, model_name=config.agent_b_model, validate=False)

    pipeline = CorrectionPipeline(
        term_agent=term_agent,
        correction_agent=correction_agent,
        domain="algorithm",
        use_evidence=False,
    )

    assert pipeline.max_text_length == 3000
    assert pipeline.MAX_CONCURRENT_GROUPS == 6
