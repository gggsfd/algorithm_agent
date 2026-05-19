import sys
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

import pytest
from app.agents.term_agent import TermAgent
from app.agents.correction_agent import CorrectionAgent
from app.agents.pipeline import CorrectionPipeline
from app.core.llm_config import LLMConfig


def build_empty_llm_config() -> LLMConfig:
    config = LLMConfig()
    config.agent_a_api_key = ""
    config.agent_b_api_key = ""
    config.agent_a_model = "deepseek-chat"
    config.agent_b_model = "deepseek-chat"
    config.base_url = "https://api.deepseek.com"
    return config


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
    """测试 CorrectionPipeline 异步 partial fallback"""
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
    assert effective_mode == "partial"
    assert degraded is True
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
