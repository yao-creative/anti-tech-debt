from __future__ import annotations

from contracts.events import Event
from contracts.queues import TypedQueue
from runtime.event_bus import EventBus


class SubagentRuntime:
    """Delegated worker for one sub-task in the scaffold.

    Owns:
        The delegated-task execution rule and the event bridge it writes to.

    Mutates:
        ``event_bridge`` by publishing lifecycle events.

    Observes:
        The delegated task string and thread id.

    Functional framing:
        A worker that returns a result while emitting progress events.

    Category-theoretic framing:
        A product-like arrow from task input to streamed events and a final
        result.
    """

    def __init__(self, event_sink: TypedQueue[Event] | EventBus) -> None:
        self.event_sink = event_sink

    async def run(self, thread_id: str, task: str) -> str:
        await self._emit(
            Event(thread_id=thread_id, type="subagent.started", payload={"task": task})
        )
        result = f"Subagent reviewed delegated task: {task}"
        await self._emit(
            Event(thread_id=thread_id, type="subagent.completed", payload={"result": result})
        )
        return result

    async def _emit(self, event: Event) -> None:
        if isinstance(self.event_sink, EventBus):
            await self.event_sink.publish(event)
            return
        await self.event_sink.put(event)
