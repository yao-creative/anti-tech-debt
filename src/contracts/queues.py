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
    """Typed wrapper over ``asyncio.Queue`` with named envelopes.

    Owns:
        One queue instance and its queue name.

    Mutates:
        Queue occupancy and completion bookkeeping.

    Observes:
        Payload values flowing between runtime actors.

    Functional framing:
        A bounded asynchronous channel carrying values of one logical type.

    Category-theoretic framing:
        A process boundary object whose arrows sequence producers and
        consumers in the asynchronous effect category.
    """

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
