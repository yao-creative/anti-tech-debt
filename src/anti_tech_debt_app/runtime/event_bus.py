from __future__ import annotations

import asyncio

from anti_tech_debt_app.contracts.events import Event, StatusSnapshot


class EventBus:
    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[Event]] = []
        self._status: StatusSnapshot | None = None

    def subscribe(self) -> asyncio.Queue[Event]:
        queue: asyncio.Queue[Event] = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    async def publish(self, event: Event) -> None:
        for queue in self._subscribers:
            await queue.put(event)

    def publish_status(self, status: StatusSnapshot) -> None:
        self._status = status

    @property
    def status(self) -> StatusSnapshot | None:
        return self._status
