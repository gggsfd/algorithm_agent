import sys
import os
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

from app.rag.pinyin_converter import PinyinConverter, text_to_pinyin


def test_basic_conversion():
    print("=== 测试基础拼音转换 ===\n")

    converter = PinyinConverter()

    test_cases = [
        ("分治", "fen zhi"),
        ("动态规划", "dong tai gui hua"),
        ("欧根老根", "ou gen lao gen"),
        ("分治法", "fen zhi fa"),
        ("算法", "suan fa"),
        ("数据结构", "shu ju jie gou"),
    ]

    print("中文 → 拼音:")
    all_pass = True
    for text, expected in test_cases:
        result = converter.convert(text)
        status = "✅" if result == expected else "❌"
        if result != expected:
            all_pass = False
        print(f"  {status} '{text}' → '{result}' (期望: '{expected}')")

    return all_pass


def test_asr_error_simulation():
    print("\n=== 测试 ASR 错误模拟 ===\n")

    converter = PinyinConverter()

    asr_errors = [
        ("分制", "fen zhi", "分治"),
        ("动态鬼话", "dong tai gui hua", "动态规划"),
        ("欧根老根", "ou gen lao gen", "O(n log n)"),
    ]

    print("ASR 错误词 → 正确词 (拼音对比):")
    for wrong, wrong_py, correct in asr_errors:
        correct_py = converter.convert(correct)
        match = "✅ 拼音相同" if wrong_py == correct_py else f"❌ 拼音不同 (相似度: {converter._calculate_pinyin_similarity(wrong_py, correct_py):.2f})"
        print(f"  {wrong} ({wrong_py}) → {correct} ({correct_py})")
        print(f"    {match}\n")


def test_batch_convert():
    print("=== 测试批量转换 ===\n")

    converter = PinyinConverter()

    terms = ["分治", "动态规划", "欧拉回路", "贪心算法", "回溯法"]
    results = converter.batch_convert(terms)

    print("批量转换结果:")
    for term, pinyin in zip(terms, results):
        print(f"  {term} → {pinyin}")


def test_pinyin_index():
    print("\n=== 测试拼音索引构建 ===\n")

    converter = PinyinConverter()

    terms = {
        "分治": {"en": "Divide and Conquer", "category": "算法"},
        "动态规划": {"en": "Dynamic Programming", "category": "算法"},
        "O(n log n)": {"en": "O(n log n)", "category": "复杂度"},
    }

    index = converter.build_pinyin_index(terms)

    print("术语库拼音索引:")
    for term, data in index.items():
        print(f"  {term}:")
        print(f"    拼音: {data['pinyin']}")
        print(f"    首字母: {data['first_letters']}")
        print(f"    英文: {data['info'].get('en', 'N/A')}")


def test_similarity_search():
    print("\n=== 测试拼音相似度搜索 ===\n")

    converter = PinyinConverter()

    term_dict = {
        "分治": {"pinyin": "fen zhi", "info": {"en": "Divide and Conquer"}},
        "动态规划": {"pinyin": "dong tai gui hua", "info": {"en": "Dynamic Programming"}},
        "分治法": {"pinyin": "fen zhi fa", "info": {"en": "Divide and Conquer Method"}},
        "贪心算法": {"pinyin": "tan xin suan fa", "info": {"en": "Greedy Algorithm"}},
    }

    queries = ["分制", "动态鬼话", "贪心"]

    for query in queries:
        results = converter.find_similar_by_pinyin(query, term_dict, top_k=3)
        print(f"查询 '{query}' 的结果:")
        if results:
            for term, similarity, en in results:
                print(f"  → {term} (相似度: {similarity:.2f}, 英文: {en})")
        else:
            print(f"  未找到匹配项")
        print()


def test_extract_first_letters():
    print("=== 测试首字母提取 ===\n")

    converter = PinyinConverter()

    terms = ["分治", "动态规划", "欧拉回路", "深度优先搜索"]

    print("首字母提取:")
    for term in terms:
        letters = converter.extract_first_letters(term)
        print(f"  {term} → {letters}")


if __name__ == "__main__":
    print("="*60)
    print("拼音转换器测试")
    print("="*60)

    try:
        test_basic_conversion()
        test_asr_error_simulation()
        test_batch_convert()
        test_pinyin_index()
        test_similarity_search()
        test_extract_first_letters()

        print("\n" + "="*60)
        print("✅ 拼音转换器测试完成！")
        print("="*60)

    except ImportError as e:
        print(f"\n❌ 缺少依赖: {e}")
        print("请先安装: pip install pypinyin")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
