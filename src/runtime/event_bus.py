from __future__ import annotations

import asyncio

from contracts.events import Event, RuntimeState


class EventBus:
    """In-memory pub-sub bus plus last-known status cell.

    Owns:
        Subscriber queues and the latest published RuntimeState.

    Mutates:
        The subscriber registry and cached status value.

    Observes:
        Published Event and RuntimeState values from runtime actors.

    Functional framing:
        Broadcast channel for events with a separate last-value register for
        status.

    Category-theoretic framing:
        A natural broadcast from one event source into a family of subscriber
        queues.
    """

    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[Event]] = []
        self._status: RuntimeState | None = None

    def subscribe(self) -> asyncio.Queue[Event]:
        queue: asyncio.Queue[Event] = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    async def publish(self, event: Event) -> None:
        for queue in self._subscribers:
            await queue.put(event)

    def publish_status(self, status: RuntimeState) -> None:
        self._status = status

    @property
    def status(self) -> RuntimeState | None:
        return self._status
