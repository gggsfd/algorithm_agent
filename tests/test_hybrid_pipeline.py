import sys
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

import pytest
from app.agents.hybrid_pipeline import HybridPipeline
from app.core.llm_config import LLMConfig


def build_empty_llm_config() -> LLMConfig:
    config = LLMConfig()
    config.agent_a_api_key = ""
    config.agent_b_api_key = ""
    config.agent_a_model = "deepseek-chat"
    config.agent_b_model = "deepseek-chat"
    config.base_url = "https://api.deepseek.com"
    return config


def test_hybrid_pipeline_sync_partial_fallback():
    pipeline = HybridPipeline(llm_config=build_empty_llm_config(), domain="algorithm")
    items = [{"id": 1, "text": "动态鬼话和欧根老根"}]
    corrected, effective_mode, degraded = pipeline.process_chunk_sync(items)
    assert effective_mode == "partial"
    assert degraded is True
    assert "动态规划" in corrected[0]["text"]


@pytest.mark.asyncio
async def test_hybrid_pipeline_async_partial_fallback():
    pipeline = HybridPipeline(llm_config=build_empty_llm_config(), domain="algorithm")
    items = [{"id": 1, "text": "分制法是经典方法"}]
    corrected, effective_mode, degraded = await pipeline.process_chunk(items)
    assert effective_mode == "partial"
    assert degraded is True
    assert "分治法" in corrected[0]["text"]
