"""批量测试 test 目录下所有 SRT 文件的 Hybrid 模式纠错"""
import sys
import os
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

from app.services.srt_service import SRTService
from app.schemas.correction_mode import CorrectionMode

TEST_DIR = Path(r"d:\Mycode\算法_agent\str_file\test")
OUTPUT_DIR = TEST_DIR / "corrected"


def process_file(service: SRTService, srt_path: Path) -> dict:
    """处理单个 SRT 文件"""
    print(f"\n{'='*60}")
    print(f"[处理] {srt_path.name}")
    print(f"{'='*60}")

    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()

    block_count = srt_content.count("\n\n") + 1
    print(f"  文件大小: {len(srt_content)} 字符, 字幕块: {block_count}")

    start = time.perf_counter()
    try:
        final_srt, success, mode_meta = service.process_srt(
            srt_content,
            correction_mode=CorrectionMode.HYBRID,
            domain="algorithm",
        )
        elapsed = time.perf_counter() - start

        result = {
            "file": srt_path.name,
            "success": success,
            "elapsed": round(elapsed, 2),
            "effective_mode": mode_meta.get("effective_mode", "N/A"),
            "degraded": mode_meta.get("degraded", False),
            "stats": mode_meta.get("stats", {}),
        }

        if success and final_srt:
            output_path = OUTPUT_DIR / srt_path.name.replace(".srt", "_corrected.srt")
            output_path.write_text(final_srt, encoding="utf-8")
            result["output"] = str(output_path)
            print(f"  [OK] 成功, 耗时 {elapsed:.1f}s, 模式={result['effective_mode']}")
            print(f"  输出: {output_path}")
        else:
            print(f"  [FAIL] 失败, 耗时 {elapsed:.1f}s")

        return result

    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"  [ERROR] 异常: {e}, 耗时 {elapsed:.1f}s")
        import traceback
        traceback.print_exc()
        return {
            "file": srt_path.name,
            "success": False,
            "elapsed": round(elapsed, 2),
            "error": str(e),
        }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    srt_files = sorted(TEST_DIR.glob("*.srt"))
    if not srt_files:
        print(f"[ERROR] 未在 {TEST_DIR} 找到 .srt 文件")
        return

    print(f"找到 {len(srt_files)} 个 SRT 文件:\n")
    for f in srt_files:
        print(f"  - {f.name}")

    service = SRTService()
    print(f"\nAgent 可用: {service.agent_available}")
    print(f"Agent A Key: {service.llm_config.agent_a_api_key[:15]}...")
    print(f"Agent B Key: {service.llm_config.agent_b_api_key[:15]}...")
    print(f"Agent A Model: {service.llm_config.agent_a_model}")
    print(f"Base URL: {service.llm_config.base_url}")

    results = []
    total_start = time.perf_counter()

    for srt_path in srt_files:
        result = process_file(service, srt_path)
        results.append(result)

    total_elapsed = time.perf_counter() - total_start

    # 汇总报告
    print(f"\n{'='*60}")
    print(f"汇总报告")
    print(f"{'='*60}")
    success_count = sum(1 for r in results if r.get("success"))
    print(f"  成功: {success_count}/{len(results)}")
    print(f"  总耗时: {total_elapsed:.1f}s")
    print()
    for r in results:
        status = "OK" if r.get("success") else "FAIL"
        elapsed = r.get("elapsed", "N/A")
        mode = r.get("effective_mode", "N/A")
        print(f"  [{status}] {r['file']} | {elapsed}s | mode={mode}")

    if success_count == len(results):
        print(f"\n[全部通过] 所有文件纠错成功!")
    else:
        print(f"\n[部分失败] {len(results) - success_count} 个文件处理失败")


if __name__ == "__main__":
    main()
