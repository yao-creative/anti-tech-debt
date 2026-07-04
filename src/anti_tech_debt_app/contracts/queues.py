from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class QueueEnvelope(Generic[T]):
    name: str
    payload: T


class TypedQueue(Generic[T]):
    def __init__(self, name: str, maxsize: int = 0) -> None:
        self.name = name
        self._queue: asyncio.Queue[QueueEnvelope[T]] = asyncio.Queue(maxsize=maxsize)

    async def put(self, payload: T) -> None:
        await self._queue.put(QueueEnvelope(name=self.name, payload=payload))

    async def get(self) -> T:
        envelope = await self._queue.get()
        return envelope.payload

    def get_nowait(self) -> T:
        envelope = self._queue.get_nowait()
        return envelope.payload

    def task_done(self) -> None:
        self._queue.task_done()

    def qsize(self) -> int:
        return self._queue.qsize()
