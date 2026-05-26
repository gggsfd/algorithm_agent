import sys
import time
import asyncio
import logging
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

from dotenv import load_dotenv
load_dotenv('d:/Mycode/算法_agent/algorithm_agent/.env')

logging.basicConfig(level=logging.INFO)

from app.agents.pipeline import CorrectionPipeline
from app.agents.term_agent import TermAgent
from app.agents.correction_agent import CorrectionAgent
from app.core.llm_config import LLMConfig
from openai import AsyncOpenAI


def parse_srt_simple(content: str):
    blocks = content.strip().split('\n\n')
    items = []
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            try:
                idx = int(lines[0])
                text = ' '.join(lines[2:])
                items.append({"id": idx, "text": text})
            except ValueError:
                continue
    return items


async def test_concurrency_bottleneck():
    print("=== 并发瓶颈分析测试 ===\n")

    SRT_FILE_PATH = r'd:\Mycode\算法_agent\str_file\4.3\4月11日 (1)(1).srt'
    with open(SRT_FILE_PATH, 'r', encoding='utf-8') as f:
        srt_content = f.read()

    items = parse_srt_simple(srt_content)
    print(f"总字幕数: {len(items)}")

    llm_config = LLMConfig.from_env()
    client = AsyncOpenAI(
        api_key=llm_config.agent_a_api_key,
        base_url=llm_config.base_url,
    )

    term_agent = TermAgent(
        llm_client=client,
        model_name=llm_config.agent_a_model,
        domain="algorithm",
        min_confidence=0.35,
    )

    correction_agent = CorrectionAgent(
        llm_client=client,
        model_name=llm_config.agent_b_model,
        validate=True,
    )

    pipeline = CorrectionPipeline(
        term_agent=term_agent,
        correction_agent=correction_agent,
        domain="algorithm",
        use_evidence=False,
    )

    print(f"\n当前配置:")
    print(f"  MAX_TEXT_LENGTH: {pipeline.MAX_TEXT_LENGTH}")
    print(f"  MAX_ITEMS_PER_GROUP: {pipeline.MAX_ITEMS_PER_GROUP}")
    print(f"  MAX_CONCURRENT_GROUPS: {pipeline.MAX_CONCURRENT_GROUPS}")

    combined_text = " ".join([item["text"] for item in items])
    groups = pipeline._split_into_groups(items, pipeline.MAX_TEXT_LENGTH)
    print(f"  分组数: {len(groups)}")
    print(f"  平均每组: {len(items) / len(groups):.1f} 条")

    print(f"\n开始测试并发处理...")
    start = time.time()
    corrected, mode, degraded = await pipeline.process_async(items)
    elapsed = time.time() - start

    print(f"总耗时: {elapsed:.2f} 秒")
    print(f"平均每组耗时: {elapsed / len(groups):.2f} 秒")
    print(f"理论串行耗时: {elapsed / len(groups) * len(groups):.2f} 秒")
    print(f"并发加速比: {len(groups) * (elapsed / len(groups)) / elapsed:.2f}x")

    print("\n=== 分析结论 ===")
    if len(groups) <= 1:
        print("  字幕数量较少，未触发并发分组")
    else:
        print(f"  共 {len(groups)} 组，最多 {pipeline.MAX_CONCURRENT_GROUPS} 组并发")
        print(f"  如果 MAX_CONCURRENT_GROUPS 太小，会导致大量等待时间")


if __name__ == "__main__":
    asyncio.run(test_concurrency_bottleneck())
