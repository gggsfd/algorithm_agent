import sys
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

import asyncio
from app.agents.agent_a import AgentA
from app.agents.agent_b import AgentB
from app.agents.pipeline import AgentPipeline


def test_agent_a_rule_based():
    print("=== 测试 Agent A（侦察）- 规则引擎 ===")
    agent_a = AgentA(llm_client=None)

    test_texts = [
        "下面讲一个欧根老根的问题",
        "动态鬼话是常用技巧",
        "介绍一种分制策略",
        "今天天气真好",
    ]

    for text in test_texts:
        result = agent_a._rule_based_fallback(text)
        print(f"原文: {text}")
        print(f"发现: {result if result else '无错误'}")
        print()


def test_agent_b_rule_based():
    print("=== 测试 Agent B（主刀）- 规则引擎 ===")
    agent_b = AgentB(llm_client=None)

    subtitle_items = [
        {"id": 1, "text": "下面讲一个欧根老根的问题"},
        {"id": 2, "text": "动态鬼话是常用技巧"},
        {"id": 3, "text": "分治法是算法设计的重要内容"},
    ]

    replacement_dict = {
        "欧根老根": "O(n log n)",
        "动态鬼话": "动态规划",
    }

    result = agent_b._rule_based_correction(subtitle_items, replacement_dict)
    print("替换规则:", replacement_dict)
    print("结果:")
    for item in result:
        print(f"  ID {item['id']}: {item['text']}")


def test_pipeline_sync():
    print("\n=== 测试 Pipeline（同步模式） ===")
    pipeline = AgentPipeline(llm_client=None)

    subtitle_items = [
        {"id": 1, "text": "下面讲一个欧根老根的问题"},
        {"id": 2, "text": "动态鬼话是常用技巧"},
        {"id": 3, "text": "分治法是算法设计的重要内容"},
        {"id": 4, "text": "今天我们介绍一种分治策略"},
        {"id": 5, "text": "它的时间复杂度是欧根老根"},
    ]

    corrected, success = pipeline.process_chunk_sync(subtitle_items)

    print(f"成功: {success}")
    print("纠错结果:")
    for item in corrected:
        print(f"  ID {item['id']}: {item['text']}")


async def test_pipeline_async():
    print("\n=== 测试 Pipeline（异步模式 - 需要 LLM） ===")
    print("提示: 异步模式需要配置 LLM client，当前使用规则引擎作为 fallback")
    pipeline = AgentPipeline(llm_client=None)

    subtitle_items = [
        {"id": 1, "text": "下面讲一个欧根老根的问题"},
        {"id": 2, "text": "动态鬼话是常用技巧"},
    ]

    corrected, success = await pipeline.process_chunk(subtitle_items)

    print(f"成功: {success}")
    print("纠错结果:")
    for item in corrected:
        print(f"  ID {item['id']}: {item['text']}")


def test_agent_a_parse():
    print("\n=== 测试 Agent A JSON 解析 ===")
    agent_a = AgentA(llm_client=None)

    test_responses = [
        '{"欧根老根": "O(n log n)", "动态鬼话": "动态规划"}',
        '{"分制": "分治", "分制法": "分治法"}',
        '{}',
        '这是一个无效的响应',
    ]

    for response in test_responses:
        result = agent_a._parse_json_response(response)
        print(f"输入: {response}")
        print(f"解析: {result}")
        print()


if __name__ == "__main__":
    test_agent_a_rule_based()
    test_agent_b_rule_based()
    test_pipeline_sync()
    asyncio.run(test_pipeline_async())
    test_agent_a_parse()

    print("\n✅ 所有 Agent 测试完成！")
