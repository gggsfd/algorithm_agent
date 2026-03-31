import sys
import os
import asyncio
import pytest
sys.path.insert(0, 'd:/Mycode/算法_agent/algorithm_agent')

from app.core.task_dispatcher import TaskDispatcher, SlidingWindowDispatcher, create_chunks


def test_basic_chunking():
    print("=== 测试基础切片 ===\n")

    dispatcher = TaskDispatcher(chunk_size=5, overlap_size=2)

    items = [
        {"id": i, "text": f"字幕{i}"}
        for i in range(1, 21)
    ]

    chunks = dispatcher.create_chunks(items)

    print(f"总字幕数: {len(items)}")
    print(f"Chunk 大小: 5, 重叠: 2")
    print(f"生成 Chunk 数: {len(chunks)}\n")

    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1} ({chunk.chunk_id}):")
        print(f"  ID 范围: {chunk.start_id} - {chunk.end_id}")
        print(f"  重叠 ID: {chunk.overlap_ids}")
        print(f"  数据条数: {len(chunk.data)}")
        print()


def test_sliding_window():
    print("=== 测试滑动窗口 ===\n")

    dispatcher = SlidingWindowDispatcher(window_size=5, step_size=3)

    items = [
        {"id": i, "text": f"字幕{i}"}
        for i in range(1, 16)
    ]

    chunks = dispatcher.create_chunks(items)

    print(f"总字幕数: {len(items)}")
    print(f"窗口大小: 5, 步长: 3")
    print(f"生成 Chunk 数: {len(chunks)}\n")

    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1} ({chunk.chunk_id}):")
        print(f"  ID 范围: {chunk.start_id} - {chunk.end_id}")
        print(f"  重叠 ID: {chunk.overlap_ids}")
        print()


def test_sync_processing():
    print("=== 测试同步处理 ===\n")

    dispatcher = TaskDispatcher(chunk_size=5, overlap_size=2)

    items = [
        {"id": i, "text": f"原始字幕{i}"}
        for i in range(1, 11)
    ]

    def processor(data: list) -> list:
        return [
            {"id": item["id"], "text": f"处理后{item['text']}"}
            for item in data
        ]

    result, success = dispatcher.process_chunks_sync(items, processor)

    print(f"原始数据条数: {len(items)}")
    print(f"处理后数据条数: {len(result)}")
    print(f"处理成功: {success}\n")

    print("处理结果:")
    for item in result:
        print(f"  ID {item['id']}: {item['text']}")


@pytest.mark.asyncio
async def test_async_processing():
    print("\n=== 测试异步处理 ===\n")

    dispatcher = TaskDispatcher(chunk_size=5, overlap_size=2, max_concurrency=3)

    items = [
        {"id": i, "text": f"字幕{i}"}
        for i in range(1, 11)
    ]

    async def async_processor(data: list) -> list:
        await asyncio.sleep(0.1)
        return [
            {"id": item["id"], "text": f"异步处理{item['text']}"}
            for item in data
        ]

    result, success = await dispatcher.process_chunks_async(items, async_processor)

    print(f"原始数据条数: {len(items)}")
    print(f"处理后数据条数: {len(result)}")
    print(f"处理成功: {success}\n")

    print("处理结果:")
    for item in result:
        print(f"  ID {item['id']}: {item['text']}")


def test_merge_results():
    print("\n=== 测试结果合并 ===\n")

    dispatcher = TaskDispatcher(chunk_size=5, overlap_size=2)

    original_items = [
        {"id": i, "text": f"原始{i}"}
        for i in range(1, 11)
    ]

    from app.core.task_dispatcher import Chunk

    chunk1 = Chunk(
        chunk_id="chunk_001",
        data=[{"id": 1, "text": "原始1"}, {"id": 2, "text": "原始2"}],
        start_id=1,
        end_id=2,
        overlap_ids=[]
    )

    processed1 = [
        {"id": 1, "text": "修正1"},
        {"id": 2, "text": "修正2"},
    ]

    processed_chunks = [(chunk1, processed1)]

    merged = dispatcher.merge_results(original_items, processed_chunks)

    print("合并结果:")
    for item in merged:
        print(f"  ID {item['id']}: {item['text']}")


if __name__ == "__main__":
    import asyncio

    print("="*60)
    print("滑动窗口切片测试")
    print("="*60)

    try:
        test_basic_chunking()
        test_sliding_window()
        test_sync_processing()
        asyncio.run(test_async_processing())
        test_merge_results()

        print("\n" + "="*60)
        print("✅ 滑动窗口切片测试完成！")
        print("="*60)

    except ImportError as e:
        print(f"\n❌ 缺少依赖: {e}")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
