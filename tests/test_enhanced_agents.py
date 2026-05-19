import sys
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

import pytest
from app.agents.term_agent import TermAgent
from app.agents.correction_agent import CorrectionAgent
from app.schemas.candidate import CandidateCorrection
from app.core.exceptions import AgentExecutionError


@pytest.mark.asyncio
async def test_term_agent_evidence_fallback():
    """测试 TermAgent 带证据的降级逻辑"""
    term_agent = TermAgent(llm_client=None, domain="algorithm")

    candidates = {
        "动态鬼话": CandidateCorrection(
            correct="动态规划",
            source="dict",
            confidence=0.95,
            method="hardcoded_mapping"
        ),
        "欧根老根": CandidateCorrection(
            correct="O(n log n)",
            source="dict",
            confidence=0.95,
            method="hardcoded_mapping"
        ),
    }

    context = {"caption_text": "动态鬼话和欧根老根是常见错误", "candidates": candidates}
    result = await term_agent.execute(context)

    assert result.get("动态鬼话") == "动态规划"
    assert result.get("欧根老根") == "O(n log n)"


@pytest.mark.asyncio
async def test_term_agent_evidence_filtering():
    """测试 TermAgent 置信度过滤"""
    term_agent = TermAgent(llm_client=None, domain="algorithm", min_confidence=0.5)

    candidates = {
        "动态鬼话": CandidateCorrection(
            correct="动态规划",
            source="dict",
            confidence=0.95,
            method="hardcoded_mapping"
        ),
        "低置信度": CandidateCorrection(
            correct="正确词",
            source="pinyin",
            confidence=0.3,
            method="pinyin_similarity"
        ),
    }

    llm_result = {"动态鬼话": "动态规划", "低置信度": "正确词"}
    filtered = term_agent._filter_by_confidence(llm_result, candidates)

    assert "动态鬼话" in filtered
    assert "低置信度" not in filtered


@pytest.mark.asyncio
async def test_correction_agent_validation():
    """测试 CorrectionAgent 校验逻辑"""
    agent = CorrectionAgent(llm_client=None, validate=True)

    items = [{"id": 1, "text": "下面讲动态鬼话"}]
    replacement_dict = {"动态鬼话": "动态规划"}

    context = {
        "subtitle_items": items,
        "replacement_dict": replacement_dict
    }
    corrected = await agent.execute(context)
    assert corrected[0]["text"] == "下面讲动态规划"


@pytest.mark.asyncio
async def test_correction_agent_validation_error():
    """测试 CorrectionAgent 校验失败"""
    agent = CorrectionAgent(llm_client=None, validate=True)

    items = [{"id": 1, "text": "下面讲动态鬼话"}]
    replacement_dict = {"动态鬼话": "动态规划"}

    with pytest.raises(AgentExecutionError):
        agent._validate_corrections(
            items,
            [{"id": 1, "text": "下面讲动态规划并且新增了一大段文字"}],
            replacement_dict,
        )


@pytest.mark.asyncio
async def test_correction_agent_validation_pass():
    """测试 CorrectionAgent 校验通过"""
    agent = CorrectionAgent(llm_client=None, validate=True)

    items = [{"id": 1, "text": "下面讲动态鬼话"}]
    replacement_dict = {"动态鬼话": "动态规划"}

    validated = agent._validate_corrections(
        items,
        [{"id": 1, "text": "下面讲动态规划"}],
        replacement_dict,
    )

    assert validated[0]["text"] == "下面讲动态规划"
