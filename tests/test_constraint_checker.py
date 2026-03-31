import sys
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

from app.core.srt_parser import SRTParser
from app.core.constraint_checker import ConstraintChecker
from app.core.exceptions import ConstraintCheckError


def test_restore_srt():
    parser = SRTParser()

    with open('d:/Mycode/算法_agent/algorithm_agent/tests/test_sample.srt', 'r', encoding='utf-8') as f:
        content = f.read()

    result = parser.parse(content)
    checker = ConstraintChecker(result.items)

    corrected_items = [
        {"id": 1, "text": "今天我们介绍一种分治策略"},
        {"id": 2, "text": "它的时间复杂度是 O(n log n)"},
        {"id": 3, "text": "分治法是算法设计的重要内容"},
        {"id": 4, "text": "下面讲一个 O(n log n) 的问题"},
        {"id": 5, "text": "动态规划是常用技巧"},
    ]

    print("=== 校验通过 ===")
    srt_output = checker.restore_srt(corrected_items)
    print(srt_output)


def test_validate_fail_count():
    parser = SRTParser()

    with open('d:/Mycode/算法_agent/algorithm_agent/tests/test_sample.srt', 'r', encoding='utf-8') as f:
        content = f.read()

    result = parser.parse(content)
    checker = ConstraintChecker(result.items)

    corrected_items = [
        {"id": 1, "text": "今天我们介绍一种分治策略"},
        {"id": 2, "text": "它的时间复杂度是 O(n log n)"},
    ]

    print("=== 校验失败：数量不一致 ===")
    try:
        checker.validate(corrected_items)
    except ConstraintCheckError as e:
        print(f"✅ 正确捕获: {e}")


def test_validate_fail_id():
    parser = SRTParser()

    with open('d:/Mycode/算法_agent/algorithm_agent/tests/test_sample.srt', 'r', encoding='utf-8') as f:
        content = f.read()

    result = parser.parse(content)
    checker = ConstraintChecker(result.items)

    corrected_items = [
        {"id": 1, "text": "今天我们介绍一种分治策略"},
        {"id": 2, "text": "它的时间复杂度是 O(n log n)"},
        {"id": 99, "text": "这是一个错误的ID"},
        {"id": 4, "text": "下面讲一个 O(n log n) 的问题"},
        {"id": 5, "text": "动态规划是常用技巧"},
    ]

    print("=== 校验失败：ID不匹配 ===")
    try:
        checker.validate(corrected_items)
    except ConstraintCheckError as e:
        print(f"✅ 正确捕获: {e}")


def test_validate_fail_empty_text():
    parser = SRTParser()

    with open('d:/Mycode/算法_agent/algorithm_agent/tests/test_sample.srt', 'r', encoding='utf-8') as f:
        content = f.read()

    result = parser.parse(content)
    checker = ConstraintChecker(result.items)

    corrected_items = [
        {"id": 1, "text": ""},
        {"id": 2, "text": "它的时间复杂度是 O(n log n)"},
        {"id": 3, "text": "分治法是算法设计的重要内容"},
        {"id": 4, "text": "下面讲一个 O(n log n) 的问题"},
        {"id": 5, "text": "动态规划是常用技巧"},
    ]

    print("=== 校验失败：空文本 ===")
    try:
        checker.validate(corrected_items)
    except ConstraintCheckError as e:
        print(f"✅ 正确捕获: {e}")


def test_fallback():
    parser = SRTParser()

    with open('d:/Mycode/算法_agent/algorithm_agent/tests/test_sample.srt', 'r', encoding='utf-8') as f:
        content = f.read()

    result = parser.parse(content)
    checker = ConstraintChecker(result.items)

    print("=== 降级方案：保留原始字幕 ===")
    fallback_srt = checker.get_fallback_srt()
    print(fallback_srt)


if __name__ == "__main__":
    test_restore_srt()
    print()
    test_validate_fail_count()
    print()
    test_validate_fail_id()
    print()
    test_validate_fail_empty_text()
    print()
    test_fallback()
