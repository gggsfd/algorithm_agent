import asyncio
import random
from typing import List, Dict, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum


class ChunkStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    DEGRADED = "degraded"


@dataclass
class ChunkResult:
    chunk_id: str
    status: ChunkStatus
    data: List[Dict]
    attempts: int
    error: str = ""
    degraded: bool = False


@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 10.0
    exponential_base: float = 2.0
    jitter: bool = True


class RetryableChunkProcessor:

    def __init__(
        self,
        processor: Callable[[List[Dict]], Awaitable[List[Dict]]],
        config: RetryConfig = None
    ):
        self.processor = processor
        self.config = config or RetryConfig()

    def _calculate_delay(self, attempt: int) -> float:
        delay = self.config.base_delay * (self.config.exponential_base ** attempt)
        delay = min(delay, self.config.max_delay)

        if self.config.jitter:
            delay *= (0.5 + random.random() * 0.5)

        return delay

    async def process_with_retry(
        self,
        chunk_data: List[Dict],
        chunk_id: str
    ) -> ChunkResult:
        last_error = ""
        last_data = chunk_data

        for attempt in range(self.config.max_retries + 1):
            try:
                result = await self.processor(chunk_data)

                if attempt > 0:
                    print(f"Chunk {chunk_id} 在第 {attempt + 1} 次尝试成功")

                return ChunkResult(
                    chunk_id=chunk_id,
                    status=ChunkStatus.SUCCESS,
                    data=result,
                    attempts=attempt + 1
                )

            except Exception as e:
                last_error = str(e)
                last_data = chunk_data

                if attempt < self.config.max_retries:
                    delay = self._calculate_delay(attempt)
                    print(f"Chunk {chunk_id} 第 {attempt + 1} 次失败，{delay:.2f}s 后重试: {e}")
                    await asyncio.sleep(delay)
                else:
                    print(f"Chunk {chunk_id} 达到最大重试次数 {self.config.max_retries + 1}，降级处理")

        return ChunkResult(
            chunk_id=chunk_id,
            status=ChunkStatus.DEGRADED,
            data=last_data,
            attempts=self.config.max_retries + 1,
            error=last_error,
            degraded=True
        )