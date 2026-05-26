import sys
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

from dotenv import load_dotenv
load_dotenv('d:/Mycode/算法_agent/algorithm_agent/.env')

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

from app.services.srt_service import SRTService
from app.schemas.correction_mode import CorrectionMode

SRT_FILE_PATH = r'd:\Mycode\算法_agent\str_file\5.3\5月8日.srt'


def test_hybrid_mode_5月8日():
    print("=" * 60)
    print("=== Hybrid 模式测试: 5月8日.srt ===")
    print("=" * 60)
    print(f"文件路径: {SRT_FILE_PATH}\n")

    with open(SRT_FILE_PATH, 'r', encoding='utf-8') as f:
        srt_content = f.read()

    print(f"文件大小: {len(srt_content)} 字符")
    print(f"预估字幕块数: {srt_content.count('\n\n') + 1}\n")

    service = SRTService()

    print(f"Agent 可用: {service.agent_available}")
    print(f"LLM Provider: {service.llm_config.provider}")
    print(f"Agent A Model: {service.llm_config.agent_a_model}")
    print(f"Agent B Model: {service.llm_config.agent_b_model}")
    print(f"Base URL: {service.llm_config.base_url}\n")

    print("开始处理（HYBRID 模式）...\n")
    try:
        final_srt, success, mode_meta = service.process_srt(
            srt_content,
            correction_mode=CorrectionMode.HYBRID,
            domain="algorithm"
        )

        print("\n" + "=" * 60)
        print("处理结果")
        print("=" * 60)
        print(f"  成功: {success}")
        print(f"  请求模式: {mode_meta.get('correction_mode', 'N/A')}")
        print(f"  生效模式: {mode_meta.get('effective_mode', 'N/A')}")
        print(f"  降级处理: {mode_meta.get('degraded', False)}")

        if mode_meta.get('stats'):
            print("  统计信息:")
            for key, value in mode_meta['stats'].items():
                print(f"    {key}: {value}")

        output_path = SRT_FILE_PATH.replace('.srt', '_corrected_hybrid.srt')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_srt)
        print(f"\n纠错结果已保存至: {output_path}")

        return final_srt, success, mode_meta

    except Exception as e:
        print(f"\n[ERROR] 异常: {e}")
        import traceback
        traceback.print_exc()
        return None, False, {}


if __name__ == "__main__":
    try:
        final_srt, success, mode_meta = test_hybrid_mode_5月8日()
        if success:
            print("\n[OK] 测试通过！")
        else:
            print("\n[FAIL] 测试失败！")
    except Exception as e:
        print(f"\n[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
