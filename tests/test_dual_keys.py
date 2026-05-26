import sys
import os
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

from dotenv import load_dotenv
load_dotenv('d:/Mycode/算法_agent/algorithm_agent/.env')

import asyncio
from openai import AsyncOpenAI


async def test_dual_api_keys():
    print("=== 测试双 API Key 配置 ===\n")

    agent_a_key = os.getenv("AGENT_A_API_KEY")
    agent_b_key = os.getenv("AGENT_B_API_KEY")

    print(f"Agent A API Key: {agent_a_key[:15]}...")
    print(f"Agent B API Key: {agent_b_key[:15]}...")

    client_a = AsyncOpenAI(api_key=agent_a_key, base_url="https://api.deepseek.com")
    client_b = AsyncOpenAI(api_key=agent_b_key, base_url="https://api.deepseek.com")

    print("\n--- 测试 TermAgent (侦察) ---")
    response_a = await client_a.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": "请回复'Agent A 测试成功'，只需回复这六个字"}
        ],
        max_tokens=50,
        temperature=0.1
    )
    result_a = response_a.choices[0].message.content
    print(f"Agent A 响应: {result_a}")
    print(f"Agent A Tokens: {response_a.usage.total_tokens}")

    print("\n--- 测试 CorrectionAgent (主刀) ---")
    response_b = await client_b.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": "请回复'Agent B 测试成功'，只需回复这六个字"}
        ],
        max_tokens=50,
        temperature=0.1
    )
    result_b = response_b.choices[0].message.content
    print(f"Agent B 响应: {result_b}")
    print(f"Agent B Tokens: {response_b.usage.total_tokens}")

    return result_a, result_b


async def test_pipeline_dual_keys():
    print("\n" + "="*50)
    print("=== 测试 CorrectionPipeline 双 Key ===")
    print("="*50)

    from app.agents.term_agent import TermAgent
    from app.agents.correction_agent import CorrectionAgent
    from app.agents.pipeline import CorrectionPipeline
    from app.core.llm_config import LLMConfig

    config = LLMConfig.from_env()

    term_agent = TermAgent(
        llm_client=AsyncOpenAI(api_key=config.agent_a_api_key, base_url=config.base_url),
        model_name=config.agent_a_model,
        domain="algorithm",
        min_confidence=0.35,
    )
    correction_agent = CorrectionAgent(
        llm_client=AsyncOpenAI(api_key=config.agent_b_api_key, base_url=config.base_url),
        model_name=config.agent_b_model,
        validate=True,
    )

    pipeline = CorrectionPipeline(
        term_agent=term_agent,
        correction_agent=correction_agent,
        domain="algorithm",
        use_evidence=False,
    )

    subtitle_items = [
        {"id": 1, "text": "下面讲一个欧根老根的问题"},
        {"id": 2, "text": "动态鬼话是常用技巧"},
        {"id": 3, "text": "分治法是算法设计的重要内容"},
    ]

    print(f"\n输入字幕数量: {len(subtitle_items)}")

    corrected, mode, degraded = await pipeline.process_async(subtitle_items)

    print(f"\n模式: {mode}, 降级: {degraded}")
    print("纠错结果:")
    for item in corrected:
        print(f"  ID {item['id']}: {item['text']}")

    return corrected, mode, degraded


if __name__ == "__main__":
    try:
        result_a, result_b = asyncio.run(test_dual_api_keys())

        if "Agent A" in result_a and "Agent B" in result_b:
            print("\n" + "="*50)
            print("✅ 双 API Key 测试成功！")
            print("="*50)
            asyncio.run(test_pipeline_dual_keys())
        else:
            print("\n❌ API Key 测试失败")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
