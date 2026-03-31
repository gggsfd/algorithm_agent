import sys
import os
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

from app.rag.vector_store import VectorStore, get_default_vector_store
from app.rag.retrieval import RetrievalEngine, get_default_engine, retrieve_terms


def test_vector_store():
    print("=== 测试向量存储 ===\n")

    store = VectorStore(persist_dir="./data/test_vector_store")
    store.build_index()

    print(f"索引术语数量: {store.get_term_count()}")
    print(f"拼音索引数量: {len(store.get_all_pinyins())}")

    index_path = store.save_index()
    print(f"索引保存至: {index_path}")


def test_vector_search():
    print("\n=== 测试向量检索 ===\n")

    store = get_default_vector_store()

    test_queries = [
        "分制",
        "动态鬼话",
        "贪心",
        "快排",
        "深度优先搜索",
    ]

    print("拼音检索测试:")
    for query in test_queries:
        results = store.search_by_pinyin(query, top_k=3)
        print(f"\n查询 '{query}':")
        if results:
            for term, similarity, info in results:
                print(f"  → {term} (相似度: {similarity:.2f}, 英文: {info.get('en', 'N/A')})")
        else:
            print(f"  未找到匹配项")


def test_text_search():
    print("\n=== 测试文本检索 ===\n")

    store = get_default_vector_store()

    test_texts = [
        "这是一个分制问题",
        "动态鬼话算法",
        "使用快排排序",
    ]

    print("文本检索测试:")
    for text in test_texts:
        errors = store.find_asr_errors(text)
        print(f"\n文本: '{text}'")
        if errors:
            for wrong, correct in errors.items():
                print(f"  发现错误: {wrong} → {correct}")
        else:
            print(f"  未发现错误")


def test_retrieval_engine():
    print("\n=== 测试检索引擎 ===\n")

    engine = get_default_engine()

    test_text = "下面讲一个分制问题，动态鬼话是常用技巧"

    print(f"输入文本: {test_text}")

    corrections = engine.get_correction_dict(test_text)
    print(f"纠错字典: {corrections}")

    errors = engine.find_errors_in_text(test_text)
    print(f"发现的错误: {errors}")


def test_batch_retrieve():
    print("\n=== 测试批量检索 ===\n")

    engine = get_default_engine()

    queries = ["分制", "动态鬼话", "贪心"]

    results = engine.batch_retrieve(queries, top_k=3)

    print("批量检索结果:")
    for query, items in results.items():
        print(f"\n查询 '{query}':")
        for item in items:
            print(f"  → {item['term']} (相似度: {item['similarity']:.2f})")


def test_rag_pipeline():
    print("\n=== 测试 RAG Pipeline ===\n")

    from app.agents.agent_a import AgentA

    print("模拟 Agent A + RAG 检索的协作流程:")
    print("1. Agent A 分析文本...")
    print("2. RAG 检索补充...")

    engine = get_default_engine()

    test_text = "这是一个分制问题，需要使用动态鬼话来解决"

    print(f"\n原始文本: {test_text}")

    rag_corrections = engine.get_correction_dict(test_text)
    print(f"RAG 纠错: {rag_corrections}")

    final_corrections = {}
    final_corrections.update(rag_corrections)

    print(f"\n合并后纠错: {final_corrections}")


if __name__ == "__main__":
    print("="*60)
    print("向量存储与检索测试")
    print("="*60)

    try:
        test_vector_store()
        test_vector_search()
        test_text_search()
        test_retrieval_engine()
        test_batch_retrieve()
        test_rag_pipeline()

        print("\n" + "="*60)
        print("✅ 向量存储与检索测试完成！")
        print("="*60)

    except ImportError as e:
        print(f"\n❌ 缺少依赖: {e}")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
