import sys
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

import pytest
from app.agents.enhanced_agent_a import EnhancedAgentA
from app.agents.enhanced_agent_b import EnhancedAgentB
from app.core.exceptions import AgentExecutionError


@pytest.mark.asyncio
async def test_enhanced_agent_a_fallback():
    agent = EnhancedAgentA(llm_client=None, domain="algorithm")
    result = await agent.analyze("动态鬼话和欧根老根是常见错误")
    assert result.get("动态鬼话") == "动态规划"
    assert result.get("欧根老根") == "O(n log n)"


@pytest.mark.asyncio
async def test_enhanced_agent_b_validation():
    agent = EnhancedAgentB(llm_client=None)
    items = [{"id": 1, "text": "下面讲动态鬼话"}]
    replacement_dict = {"动态鬼话": "动态规划"}
    corrected = await agent.correct(items, replacement_dict)
    assert corrected[0]["text"] == "下面讲动态规划"

    with pytest.raises(AgentExecutionError):
        agent._validate_corrections(
            items,
            [{"id": 1, "text": "下面讲动态规划并且新增"}],
            replacement_dict,
        )
