import sys
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

from dotenv import load_dotenv
load_dotenv('d:/Mycode/算法_agent/algorithm_agent/.env')

import logging
logging.basicConfig(level=logging.DEBUG)

from app.services.srt_service import SRTService
from app.schemas.correction_mode import CorrectionMode

SRT_FILE_PATH = r'd:\Mycode\算法_agent\str_file\4.3\4月11日 (1)(1).srt'

def test_hybrid_mode_real_file():
    print("=== 使用 Hybrid 模式测试真实 SRT 文件 ===")
    print("File path: {}\n".format(SRT_FILE_PATH))

    with open(SRT_FILE_PATH, 'r', encoding='utf-8') as f:
        srt_content = f.read()

    print("File size: {} characters".format(len(srt_content)))
    print("Subtitle blocks: {}\n".format(srt_content.count('\n\n') + 1))

    service = SRTService()

    print("Agent available: {}".format(service.agent_available))
    print("LLM config agent_a_api_key: {}".format(service.llm_config.agent_a_api_key[:15] if service.llm_config.agent_a_api_key else "None"))
    print("LLM config agent_b_api_key: {}".format(service.llm_config.agent_b_api_key[:15] if service.llm_config.agent_b_api_key else "None"))
    print("Base URL: {}".format(service.llm_config.base_url))

    print("\nStarting processing (HYBRID mode)...")
    try:
        final_srt, success, mode_meta = service.process_srt(
            srt_content,
            correction_mode=CorrectionMode.HYBRID,
            domain="algorithm"
        )

        print("\nProcessing result:")
        print("  Success: {}".format(success))
        print("  Requested mode: {}".format(mode_meta['correction_mode']))
        print("  Effective mode: {}".format(mode_meta['effective_mode']))
        print("  Degraded: {}".format(mode_meta['degraded']))

        if mode_meta.get('stats'):
            print("  Statistics:")
            for key, value in mode_meta['stats'].items():
                print("    {}: {}".format(key, value))

        output_path = SRT_FILE_PATH.replace('.srt', '_corrected.srt')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_srt)
        print("\nCorrected file saved to: {}".format(output_path))

        return final_srt, success, mode_meta
    except Exception as e:
        print("\n[ERROR] Exception: {}".format(e))
        import traceback
        traceback.print_exc()
        return None, False, {}


if __name__ == "__main__":
    try:
        final_srt, success, mode_meta = test_hybrid_mode_real_file()
        if success:
            print("\n[OK] Test passed!")
        else:
            print("\n[FAIL] Test failed!")
    except Exception as e:
        print("\n[ERROR] Test exception: {}".format(e))
        import traceback
        traceback.print_exc()
