import sys
import time
import asyncio
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

from dotenv import load_dotenv
load_dotenv('d:/Mycode/算法_agent/algorithm_agent/.env')

from app.services.srt_service import SRTService
from app.schemas.correction_mode import CorrectionMode

SRT_FILE_PATH = r'd:\Mycode\算法_agent\str_file\4.3\4月11日 (1)(1).srt'


def test_hybrid_performance():
    print("=== Hybrid 模式性能分析测试 ===\n")

    with open(SRT_FILE_PATH, 'r', encoding='utf-8') as f:
        srt_content = f.read()

    print(f"文件大小: {len(srt_content)} 字符")
    print(f"字幕块数: {srt_content.count(chr(10)+chr(10)) + 1}\n")

    service = SRTService()

    print("开始计时 (HYBRID 模式)...\n")
    start_time = time.time()

    final_srt, success, mode_meta = service.process_srt(
        srt_content,
        correction_mode=CorrectionMode.HYBRID,
        domain="algorithm"
    )

    elapsed = time.time() - start_time

    print(f"\n总耗时: {elapsed:.2f} 秒")
    print(f"Success: {success}")
    print(f"Effective mode: {mode_meta['effective_mode']}")
    print(f"Degraded: {mode_meta['degraded']}")
    print(f"输出大小: {len(final_srt)} 字符")

    print("\n=== 性能分析完成 ===")


if __name__ == "__main__":
    test_hybrid_performance()
