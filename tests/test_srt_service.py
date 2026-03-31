import sys
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

from app.services.srt_service import SRTService


def test_process_srt():
    service = SRTService()

    with open('d:/Mycode/算法_agent/algorithm_agent/tests/test_sample.srt', 'r', encoding='utf-8') as f:
        content = f.read()

    print("=== 原始 SRT ===")
    print(content)

    print("=== 处理结果 ===")
    final_srt, success = service.process_srt(content)
    print(f"是否成功: {success}")
    print(final_srt)

    print("=== 时间轴信息 ===")
    timeline = service.get_timeline(content)
    for item in timeline:
        print(f"ID {item['id']}: {item['timestamp_start']} --> {item['timestamp_end']}")
        print(f"   文本: {item['text']}")


def test_rule_based_corrections():
    service = SRTService()

    test_texts = [
        "下面讲一个欧根老根的问题",
        "动态鬼话是常用技巧",
        "介绍一种分制策略",
    ]

    print("=== 规则引擎纠错测试 ===")
    for text in test_texts:
        corrected = service._apply_corrections(text)
        print(f"原文: {text}")
        print(f"纠错: {corrected}")
        print()


if __name__ == "__main__":
    test_process_srt()
    print()
    test_rule_based_corrections()
