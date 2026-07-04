from __future__ import annotations

from anti_tech_debt_app.contracts.events import Event, StatusSnapshot
from anti_tech_debt_app.contracts.models import MessageRecord, TurnContext, TurnState
from anti_tech_debt_app.runtime.agent_runtime import AgentRuntime
from anti_tech_debt_app.runtime.event_bus import EventBus
from anti_tech_debt_app.persistence.event_log import EventLog
from anti_tech_debt_app.persistence.sqlite_store import SQLiteStore


class TurnRunner:
    def __init__(self, store: SQLiteStore, event_log: EventLog, event_bus: EventBus, agent: AgentRuntime, model: str) -> None:
        self.store = store
        self.event_log = event_log
        self.event_bus = event_bus
        self.agent = agent
        self.model = model

    async def run(self, session_id: str, user_input: str) -> str:
        history = self.store.list_messages(session_id)
        self.store.append_message(MessageRecord(session_id=session_id, role="user", content=user_input))
        self.event_bus.publish_status(
            StatusSnapshot(session_id=session_id, turn_state=TurnState.RUNNING, model=self.model, queue_depths={})
        )
        started = Event(session_id=session_id, type="turn.started", payload={"input": user_input})
        self.event_log.append(started)
        await self.event_bus.publish(started)
        final_text = await self.agent.run(TurnContext(session_id=session_id, user_input=user_input, history=history))
        self.store.append_message(MessageRecord(session_id=session_id, role="assistant", content=final_text))
        completed = Event(session_id=session_id, type="turn.completed", payload={"output": final_text})
        self.event_log.append(completed)
        await self.event_bus.publish(completed)
        self.event_bus.publish_status(
            StatusSnapshot(session_id=session_id, turn_state=TurnState.COMPLETED, model=self.model, queue_depths={})
        )
        return final_text
