import asyncio
from typing import List, Dict, Tuple, Optional, Callable, Awaitable
from dataclasses import dataclass
import uuid


@dataclass
class Chunk:
    chunk_id: str
    data: List[Dict]
    start_id: int
    end_id: int
    overlap_ids: List[int]

    def to_dict(self) -> Dict:
        return {
            "chunk_id": self.chunk_id,
            "data": self.data,
            "start_id": self.start_id,
            "end_id": self.end_id,
            "overlap_ids": self.overlap_ids
        }


class TaskDispatcher:
    def __init__(
        self,
        chunk_size: int = 20,
        overlap_size: int = 5,
        max_concurrency: int = 5
    ):
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.max_concurrency = max_concurrency

    def create_chunks(self, items: List[Dict]) -> List[Chunk]:
        if not items:
            return []

        chunks = []
        total_items = len(items)

        for i in range(0, total_items, self.chunk_size):
            chunk_start = i
            chunk_end = min(i + self.chunk_size, total_items)

            chunk_items = items[chunk_start:chunk_end]

            if i == 0:
                overlap_ids = []
            else:
                prev_start = max(0, i - self.overlap_size)
                overlap_ids = [items[j]["id"] for j in range(prev_start, chunk_start)]

            chunk = Chunk(
                chunk_id=f"chunk_{uuid.uuid4().hex[:8]}",
                data=chunk_items,
                start_id=chunk_items[0]["id"] if chunk_items else 0,
                end_id=chunk_items[-1]["id"] if chunk_items else 0,
                overlap_ids=overlap_ids
            )
            chunks.append(chunk)

        return chunks

    def merge_results(
        self,
        original_items: List[Dict],
        processed_chunks: List[Tuple[Chunk, List[Dict]]]
    ) -> List[Dict]:
        item_map = {}

        for item in original_items:
            item_map[item["id"]] = item.copy()

        for chunk, corrected_items in processed_chunks:
            for corrected in corrected_items:
                item_id = corrected.get("id")
                if item_id in item_map:
                    item_map[item_id]["text"] = corrected.get("text", item_map[item_id].get("text"))

        result = []
        for item in original_items:
            result.append(item_map[item["id"]])

        return result

    async def process_chunks_async(
        self,
        items: List[Dict],
        processor: Callable[[List[Dict]], Awaitable[List[Dict]]]
    ) -> Tuple[List[Dict], bool]:
        if not items:
            return [], True

        chunks = self.create_chunks(items)

        if not chunks:
            return items, True

        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def process_with_semaphore(chunk: Chunk) -> Tuple[Chunk, List[Dict], bool]:
            async with semaphore:
                try:
                    processed = await processor(chunk.data)
                    return chunk, processed, True
                except Exception as e:
                    print(f"Chunk {chunk.chunk_id} 处理失败: {e}")
                    return chunk, chunk.data, False

        tasks = [process_with_semaphore(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_chunks = []
        overall_success = True

        for result in results:
            if isinstance(result, Exception):
                overall_success = False
                continue
            chunk, corrected, success = result
            if not success:
                overall_success = False
            processed_chunks.append((chunk, corrected))

        merged = self.merge_results(items, processed_chunks)

        return merged, overall_success

    def process_chunks_sync(
        self,
        items: List[Dict],
        processor: Callable[[List[Dict]], List[Dict]]
    ) -> Tuple[List[Dict], bool]:
        if not items:
            return [], True

        chunks = self.create_chunks(items)

        processed_chunks = []
        for chunk in chunks:
            try:
                processed = processor(chunk.data)
                processed_chunks.append((chunk, processed))
            except Exception as e:
                print(f"Chunk {chunk.chunk_id} 处理失败: {e}")
                processed_chunks.append((chunk, chunk.data))

        merged = self.merge_results(items, processed_chunks)

        return merged, True


class SlidingWindowDispatcher(TaskDispatcher):
    def __init__(
        self,
        window_size: int = 20,
        step_size: int = 15,
        max_concurrency: int = 5
    ):
        super().__init__(chunk_size=window_size, overlap_size=window_size - step_size, max_concurrency=max_concurrency)
        self.window_size = window_size
        self.step_size = step_size

    def create_chunks(self, items: List[Dict]) -> List[Chunk]:
        if not items:
            return []

        chunks = []
        total_items = len(items)

        for i in range(0, total_items, self.step_size):
            window_start = i
            window_end = min(i + self.window_size, total_items)

            window_items = items[window_start:window_end]

            if i == 0:
                overlap_ids = []
            else:
                prev_start = max(0, i - (self.window_size - self.step_size))
                overlap_ids = [items[j]["id"] for j in range(prev_start, window_start)]

            chunk = Chunk(
                chunk_id=f"sw_{uuid.uuid4().hex[:8]}",
                data=window_items,
                start_id=window_items[0]["id"] if window_items else 0,
                end_id=window_items[-1]["id"] if window_items else 0,
                overlap_ids=overlap_ids
            )
            chunks.append(chunk)

            if window_end >= total_items:
                break

        return chunks


_default_dispatcher: Optional[TaskDispatcher] = None


def get_default_dispatcher() -> TaskDispatcher:
    global _default_dispatcher
    if _default_dispatcher is None:
        _default_dispatcher = TaskDispatcher()
    return _default_dispatcher


def create_chunks(items: List[Dict], chunk_size: int = 20, overlap_size: int = 5) -> List[Chunk]:
    dispatcher = TaskDispatcher(chunk_size=chunk_size, overlap_size=overlap_size)
    return dispatcher.create_chunks(items)


def process_parallel(
    items: List[Dict],
    processor: Callable[[List[Dict]], List[Dict]],
    chunk_size: int = 20,
    overlap_size: int = 5
) -> Tuple[List[Dict], bool]:
    dispatcher = TaskDispatcher(chunk_size=chunk_size, overlap_size=overlap_size)
    return dispatcher.process_chunks_sync(items, processor)


from app.core.retry_handler import (
    RetryableChunkProcessor,
    RetryConfig,
    ChunkResult,
    ChunkStatus
)
from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig


class EnhancedTaskDispatcher(TaskDispatcher):

    def __init__(
        self,
        chunk_size: int = 20,
        overlap_size: int = 5,
        max_concurrency: int = 5,
        retry_config: RetryConfig = None,
        circuit_breaker_config: CircuitBreakerConfig = None
    ):
        super().__init__(chunk_size, overlap_size, max_concurrency)
        self.retry_config = retry_config or RetryConfig(max_retries=3)
        self.circuit_breaker = CircuitBreaker(
            name="LLMProcessor",
            config=circuit_breaker_config or CircuitBreakerConfig()
        )

    async def process_chunks_with_retry(
        self,
        items: List[Dict],
        processor: Callable[[List[Dict]], Awaitable[List[Dict]]]
    ) -> Tuple[List[Dict], bool, Dict]:
        if not items:
            return [], True, {"total": 0, "success": 0, "failed": 0, "degraded": 0}

        chunks = self.create_chunks(items)

        retry_processor = RetryableChunkProcessor(processor, self.retry_config)

        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def process_chunk(chunk: Chunk) -> ChunkResult:
            async with semaphore:
                if not self.circuit_breaker.can_execute():
                    print(f"CircuitBreaker 开启，快速失败 Chunk {chunk.chunk_id}")
                    return ChunkResult(
                        chunk_id=chunk.chunk_id,
                        status=ChunkStatus.DEGRADED,
                        data=chunk.data,
                        attempts=0,
                        error="Circuit breaker open",
                        degraded=True
                    )

                result = await retry_processor.process_with_retry(
                    chunk.data,
                    chunk.chunk_id
                )

                if result.status == ChunkStatus.SUCCESS:
                    self.circuit_breaker.record_success()
                else:
                    self.circuit_breaker.record_failure()

                return result

        tasks = [process_chunk(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        chunk_results = []
        stats = {"total": len(chunks), "success": 0, "failed": 0, "degraded": 0}

        for result in results:
            if isinstance(result, Exception):
                stats["failed"] += 1
                continue

            chunk_results.append((result.chunk_id, result.data, result.status))
            stats[result.status.value] += 1

        merged = self.merge_results_with_stats(items, chunk_results)

        overall_success = stats["failed"] == 0 and stats["degraded"] == 0

        return merged, overall_success, stats

    def merge_results_with_stats(
        self,
        original_items: List[Dict],
        processed: List[Tuple[str, List[Dict], ChunkStatus]]
    ) -> List[Dict]:
        item_map = {item["id"]: item.copy() for item in original_items}

        for chunk_id, corrected_items, status in processed:
            for corrected in corrected_items:
                item_id = corrected.get("id")
                if item_id in item_map:
                    item_map[item_id]["text"] = corrected.get("text", item_map[item_id]["text"])

        return [item_map[item["id"]] for item in original_items]
