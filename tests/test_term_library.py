import sys
import os
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

from scripts.import_terms import TermLibrary, get_term_library, search_similar_terms


def test_term_library():
    print("=== 测试术语库 ===\n")

    library = TermLibrary()

    print(f"术语库总数: {len(library.get_all_terms())}")
    print(f"ASR 错误映射数: {len(library.get_asr_mapping())}")

    categories = set()
    for term, info in library.terms.items():
        categories.add(info.get("category", "未分类"))

    print(f"\n分类统计:")
    for cat in sorted(categories):
        count = len(library.get_terms_by_category(cat))
        print(f"  {cat}: {count}")


def test_asr_mapping():
    print("\n=== 测试 ASR 错误映射 ===\n")

    library = get_term_library()

    test_cases = [
        "分制",
        "动态鬼话",
        "贪心",
        "快排",
        "深度优化搜索",
    ]

    print("ASR 错误词 → 正确词:")
    for wrong in test_cases:
        correct = library.find_correct_term(wrong)
        if correct:
            print(f"  ✅ {wrong} → {correct}")
        else:
            print(f"  ❌ {wrong} → 未找到")


def test_pinyin_search():
    print("\n=== 测试拼音检索 ===\n")

    library = get_term_library()

    queries = [
        "分制",
        "动态鬼话",
        "贪心算法",
        "快排",
    ]

    for query in queries:
        print(f"查询 '{query}':")
        results = library.search_by_pinyin(query, top_k=3)
        if results:
            for term, similarity, en in results:
                print(f"  → {term} (相似度: {similarity:.2f}, 英文: {en})")
        else:
            print(f"  未找到匹配项")
        print()


def test_term_details():
    print("=== 测试术语详情 ===\n")

    library = get_term_library()

    terms_to_check = ["分治", "动态规划", "快速排序"]

    for term in terms_to_check:
        info = library.get_term(term)
        if info:
            print(f"{term}:")
            print(f"  英文: {info.get('en', 'N/A')}")
            print(f"  分类: {info.get('category', 'N/A')}")
            print(f"  标签: {', '.join(info.get('tags', []))}")
            print()


def test_export():
    print("=== 测试导出功能 ===\n")

    library = get_term_library()
    json_str = library.export_to_json()

    print(f"导出 JSON 长度: {len(json_str)} 字符")
    print("前 500 字符预览:")
    print(json_str[:500] + "...")


if __name__ == "__main__":
    print("="*60)
    print("术语库测试")
    print("="*60)

    try:
        test_term_library()
        test_asr_mapping()
        test_pinyin_search()
        test_term_details()
        test_export()

        print("\n" + "="*60)
        print("✅ 术语库测试完成！")
        print("="*60)

    except ImportError as e:
        print(f"\n❌ 缺少依赖: {e}")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
