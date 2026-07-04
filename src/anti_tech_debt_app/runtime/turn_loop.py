from __future__ import annotations

from anti_tech_debt_app.contracts.commands import TurnOp
from anti_tech_debt_app.contracts.events import Event, RuntimeState
from anti_tech_debt_app.contracts.models import MessageRecord, SessionState, TurnContext, TurnState
from anti_tech_debt_app.persistence.event_log import EventLog
from anti_tech_debt_app.persistence.sqlite_store import SQLiteStore
from anti_tech_debt_app.providers.base import ProviderAdapter
from anti_tech_debt_app.runtime.event_bus import EventBus
from anti_tech_debt_app.runtime.subagent_runtime import SubagentRuntime
from anti_tech_debt_app.runtime.tool_router import ToolRouter
from anti_tech_debt_app.tools.registry import ToolCall


class TurnLoop:
    """Canonical turn execution loop for the local coding runtime.

    Owns:
        The single end-to-end turn lifecycle: history load, provider stream,
        tool execution, delegated subagent work, persistence, and event
        emission.

    Mutates:
        SQLiteStore, EventLog, and EventBus status/event streams.

    Observes:
        TurnOp values, stored message history, ProviderEvent values, tool
        results, and subagent results.

    Functional framing:
        A single effectful interpreter for turn execution.

    Category-theoretic framing:
        A Kleisli arrow from turn operations into persisted session updates
        and streamed runtime events.
    """

    def __init__(
        self,
        store: SQLiteStore,
        event_log: EventLog,
        event_bus: EventBus,
        provider: ProviderAdapter,
        tool_router: ToolRouter,
        subagent_runtime: SubagentRuntime,
        model: str,
    ) -> None:
        self.store = store
        self.event_log = event_log
        self.event_bus = event_bus
        self.provider = provider
        self.tool_router = tool_router
        self.subagent_runtime = subagent_runtime
        self.model = model

    async def run(self, op: TurnOp, *, queue_depths: dict[str, int] | None = None) -> str:
        history = self.store.list_messages(op.session_id)
        self.store.append_message(MessageRecord(session_id=op.session_id, role="user", content=op.user_input))
        self._publish_status(op.session_id, TurnState.RUNNING, queue_depths)
        await self._record_and_publish(op.session_id, "turn.started", {"input": op.user_input})

        final_text = ""
        async for provider_event in self.provider.stream(
            TurnContext(session_id=op.session_id, user_input=op.user_input, history=history)
        ):
            if provider_event.type == "text_delta":
                await self.event_bus.publish(
                    Event(session_id=op.session_id, type="assistant.delta", payload={"text": provider_event.payload["text"]})
                )
                continue

            if provider_event.type == "tool_call":
                self._publish_status(op.session_id, TurnState.WAITING_TOOL, queue_depths)
                await self.tool_router.execute(
                    op.session_id,
                    ToolCall(name=provider_event.payload["tool"], arguments={"input": provider_event.payload["input"]}),
                )
                self._publish_status(op.session_id, TurnState.RUNNING, queue_depths)
                continue

            if provider_event.type == "delegate":
                self._publish_status(op.session_id, TurnState.WAITING_SUBAGENT, queue_depths)
                result = await self.subagent_runtime.run(op.session_id, provider_event.payload["task"])
                await self.event_bus.publish(
                    Event(session_id=op.session_id, type="assistant.note", payload={"text": result})
                )
                self._publish_status(op.session_id, TurnState.RUNNING, queue_depths)
                continue

            if provider_event.type == "final":
                final_text = provider_event.payload["text"]

        self.store.append_message(MessageRecord(session_id=op.session_id, role="assistant", content=final_text))
        await self._record_and_publish(op.session_id, "turn.completed", {"output": final_text})
        self._publish_status(op.session_id, TurnState.COMPLETED, queue_depths)
        return final_text

    async def publish_failure(
        self,
        session_id: str,
        error: Exception,
        *,
        queue_depths: dict[str, int] | None = None,
    ) -> None:
        await self._record_and_publish(session_id, "turn.failed", {"error": str(error)})
        self._publish_status(session_id, TurnState.FAILED, queue_depths)

    async def _record_and_publish(self, session_id: str, event_type: str, payload: dict[str, str]) -> None:
        event = Event(session_id=session_id, type=event_type, payload=payload)
        self.event_log.append(event)
        await self.event_bus.publish(event)

    def _publish_status(
        self,
        session_id: str,
        turn_state: TurnState,
        queue_depths: dict[str, int] | None,
    ) -> None:
        self.event_bus.publish_status(
            RuntimeState(
                session_id=session_id,
                session_state=SessionState.ACTIVE,
                turn_state=turn_state,
                model=self.model,
                queue_depths=queue_depths or {},
            )
        )
