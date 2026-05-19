import sys
import os
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

from dotenv import load_dotenv
load_dotenv('d:/Mycode/算法_agent/algorithm_agent/.env')

import asyncio
from openai import AsyncOpenAI


async def test_deepseek_connection():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    print(f"=== 测试 DeepSeek API 连接 ===")
    print(f"API Key: {api_key[:15]}...")

    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )

    print("\n正在调用 DeepSeek API...")

    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": "请回复'API连接成功'，只需回复这四个字"}
        ],
        max_tokens=50,
        temperature=0.1
    )

    result = response.choices[0].message.content
    print(f"\n✅ API 调用成功!")
    print(f"   模型: deepseek-chat")
    print(f"   响应: {result}")
    print(f"   Tokens: {response.usage.total_tokens}")

    return client


async def test_term_agent(client):
    print("\n" + "="*50)
    print("=== 测试 TermAgent（侦察）- DeepSeek ===")
    print("="*50)

    from app.agents.term_agent import TermAgent

    term_agent = TermAgent(llm_client=client, model_name="deepseek-chat")

    test_text = "下面讲一个欧根老根的问题，动态鬼话是常用技巧"

    print(f"\n输入文本: {test_text}")
    context = {"caption_text": test_text, "candidates": {}}
    result = await term_agent.execute(context)
    print(f"TermAgent 发现: {result}")

    return result


async def test_correction_agent(client):
    print("\n" + "="*50)
    print("=== 测试 CorrectionAgent（主刀）- DeepSeek ===")
    print("="*50)

    from app.agents.correction_agent import CorrectionAgent

    correction_agent = CorrectionAgent(llm_client=client, model_name="deepseek-chat")

    subtitle_items = [
        {"id": 1, "text": "下面讲一个欧根老根的问题"},
        {"id": 2, "text": "动态鬼话是常用技巧"},
    ]

    replacement_dict = {
        "欧根老根": "O(n log n)",
        "动态鬼话": "动态规划",
    }

    print(f"\n输入字幕: {subtitle_items}")
    print(f"替换规则: {replacement_dict}")

    context = {
        "subtitle_items": subtitle_items,
        "replacement_dict": replacement_dict
    }
    result = await correction_agent.execute(context)
    print(f"CorrectionAgent 输出: {result}")

    return result


async def test_full_pipeline(client):
    print("\n" + "="*50)
    print("=== 测试完整 CorrectionPipeline - DeepSeek ===")
    print("="*50)

    from app.agents.term_agent import TermAgent
    from app.agents.correction_agent import CorrectionAgent
    from app.agents.pipeline import CorrectionPipeline

    term_agent = TermAgent(llm_client=client, model_name="deepseek-chat")
    correction_agent = CorrectionAgent(llm_client=client, model_name="deepseek-chat")

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
        client = asyncio.run(test_deepseek_connection())
        asyncio.run(test_term_agent(client))
        asyncio.run(test_correction_agent(client))
        asyncio.run(test_full_pipeline(client))
        print("\n" + "="*50)
        print("✅ 所有 DeepSeek 测试完成！")
        print("="*50)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
