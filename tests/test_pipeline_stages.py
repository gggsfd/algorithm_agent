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
from app.agents.evidence_collector import EvidenceCollector
from app.core.llm_config import LLMConfig
from openai import AsyncOpenAI

SRT_FILE_PATH = r'd:\Mycode\算法_agent\str_file\4.3\4月11日 (1)(1).srt'


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


async def test_pipeline_stages():
    print("=== Pipeline 各阶段耗时分析 ===\n")

    with open(SRT_FILE_PATH, 'r', encoding='utf-8') as f:
        srt_content = f.read()

    items = parse_srt_simple(srt_content)
    print(f"字幕条目数: {len(items)}")
    print(f"总字符数: {sum(len(item['text']) for item in items)}\n")

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
        use_evidence=True,
    )

    print("开始测试各阶段耗时...\n")

    # 测试 EvidenceCollector
    print("[1/3] 测试 EvidenceCollector...")
    combined_text = " ".join([item["text"] for item in items[:50]])
    start = time.time()
    collector = EvidenceCollector(domain="algorithm")
    evidence = collector.collect(combined_text)
    evidence_time = time.time() - start
    print(f"  耗时: {evidence_time:.2f} 秒")
    print(f"  发现候选词: {len(evidence)} 个\n")

    # 测试 TermAgent
    print("[2/3] 测试 TermAgent...")
    start = time.time()
    context = {"caption_text": combined_text, "candidates": {}}
    replacements = await term_agent.execute(context)
    term_time = time.time() - start
    print(f"  耗时: {term_time:.2f} 秒")
    print(f"  返回替换词: {len(replacements)} 个\n")

    # 测试 CorrectionAgent
    print("[3/3] 测试 CorrectionAgent...")
    start = time.time()
    corrected = await correction_agent.execute({
        "subtitle_items": items[:20],
        "replacement_dict": replacements,
    })
    correction_time = time.time() - start
    print(f"  耗时: {correction_time:.2f} 秒")
    print(f"  纠错条目: {len(corrected)} 个\n")

    print("=== 各阶段耗时汇总 ===")
    print(f"  EvidenceCollector: {evidence_time:.2f}s")
    print(f"  TermAgent (LLM):   {term_time:.2f}s")
    print(f"  CorrectionAgent (LLM): {correction_time:.2f}s")
    print(f"  LLM 总耗时:        {term_time + correction_time:.2f}s")
    print(f"  LLM 占比:          {(term_time + correction_time) / (evidence_time + term_time + correction_time) * 100:.1f}%")


if __name__ == "__main__":
    asyncio.run(test_pipeline_stages())
