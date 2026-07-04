from __future__ import annotations

from anti_tech_debt_app.contracts.events import Event
from anti_tech_debt_app.contracts.queues import TypedQueue


class SubagentRuntime:
    def __init__(self, event_bridge: TypedQueue[Event]) -> None:
        self.event_bridge = event_bridge

    async def run(self, session_id: str, task: str) -> str:
        await self.event_bridge.put(
            Event(session_id=session_id, type="subagent.started", payload={"task": task})
        )
        result = f"Subagent reviewed delegated task: {task}"
        await self.event_bridge.put(
            Event(session_id=session_id, type="subagent.completed", payload={"result": result})
        )
        return result
