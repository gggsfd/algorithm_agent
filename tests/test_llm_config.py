import sys
import os
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

from dotenv import load_dotenv
load_dotenv('d:/Mycode/算法_agent/algorithm_agent/.env.example')

from app.core.llm_config import LLMConfig, LLMClientFactory, LLM_PROVIDERS


def test_llm_config():
    print("=== 测试 LLM 配置 ===")

    print(f"\n当前 Provider: {os.getenv('LLM_PROVIDER', 'deepseek')}")
    print(f"DeepSeek API Key: {os.getenv('DEEPSEEK_API_KEY', 'NOT SET')[:10]}..." if os.getenv('DEEPSEEK_API_KEY') else "DeepSeek API Key: NOT SET")
    print(f"OpenAI API Key: {os.getenv('OPENAI_API_KEY', 'NOT SET')[:10]}..." if os.getenv('OPENAI_API_KEY') else "OpenAI API Key: NOT SET")

    config = LLMConfig.from_env()
    print(f"\n解析后的配置:")
    print(f"  Provider: {config.provider}")
    print(f"  Base URL: {config.base_url}")
    print(f"  Agent A Model: {config.agent_a_model}")
    print(f"  Agent B Model: {config.agent_b_model}")


def test_llm_client_creation():
    print("\n=== 测试 LLM 客户端创建 ===")

    try:
        config = LLMConfig.from_env()
        client = LLMClientFactory.create_client()
        print(f"✅ LLM 客户端创建成功")
        print(f"   Base URL: {client.base_url}")
    except Exception as e:
        print(f"❌ LLM 客户端创建失败: {e}")


async def test_llm_api_call():
    print("\n=== 测试 LLM API 调用 ===")

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key or api_key == "your_deepseek_api_key_here":
        print("⚠️  请先在 .env 文件中设置有效的 DEEPSEEK_API_KEY")
        print("   或创建 .env 文件并填入你的 API Key")
        return

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "user", "content": "请回复'测试成功'，只需回复这四个字"}
            ],
            max_tokens=50,
            temperature=0.1
        )

        result = response.choices[0].message.content
        print(f"✅ LLM API 调用成功!")
        print(f"   模型: deepseek-chat")
        print(f"   响应: {result}")

    except Exception as e:
        print(f"❌ LLM API 调用失败: {e}")


def show_usage_guide():
    print("\n" + "="*60)
    print("📖 LLM 配置使用指南")
    print("="*60)

    print("\n1. 创建 .env 文件:")
    print("   复制 .env.example 为 .env")
    print("   cp .env.example .env")

    print("\n2. 选择 LLM 提供商并配置:")
    print("   - DeepSeek (推荐): 设置 DEEPSEEK_API_KEY")
    print("   - OpenAI: 设置 OPENAI_API_KEY")
    print("   - 硅基流动: 设置 SILICONFLOW_API_KEY")

    print("\n3. 在 .env 中设置:")
    print("   LLM_PROVIDER=deepseek  # 或 openai / siliconflow")
    print("   DEEPSEEK_API_KEY=your_actual_api_key_here")

    print("\n4. 可用模型列表:")
    for provider, info in LLM_PROVIDERS.items():
        print(f"   {provider}: {info['name']}")
        print(f"     Agent A: {info['models']['agent_a']}")
        print(f"     Agent B: {info['models']['agent_b']}")

    print("\n" + "="*60)


if __name__ == "__main__":
    import asyncio

    test_llm_config()
    test_llm_client_creation()
    asyncio.run(test_llm_api_call())
    show_usage_guide()
