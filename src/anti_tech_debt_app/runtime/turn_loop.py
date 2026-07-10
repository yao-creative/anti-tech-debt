from __future__ import annotations

from collections.abc import Callable

from anti_tech_debt_app.contracts.commands import TurnOp
from anti_tech_debt_app.contracts.events import Event
from anti_tech_debt_app.contracts.models import MessageRecord, TurnContext, TurnState
from anti_tech_debt_app.contracts.ports import ConversationStore, EventRecorder, ProviderAdapter, SubagentExecutor
from anti_tech_debt_app.runtime.event_bus import EventBus
from anti_tech_debt_app.runtime.tool_router import ToolRouter
from anti_tech_debt_app.tools.registry import ToolCall

StatusCallback = Callable[[str, TurnState, dict[str, int] | None], None]


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
        A Kleisli arrow from turn operations into persisted thread updates
        and streamed runtime events.
    """

    def __init__(
        self,
        store: ConversationStore,
        event_log: EventRecorder,
        event_bus: EventBus,
        provider: ProviderAdapter,
        tool_router: ToolRouter,
        subagent_runtime: SubagentExecutor,
        model: str,
    ) -> None:
        self.store = store
        self.event_log = event_log
        self.event_bus = event_bus
        self.provider = provider
        self.tool_router = tool_router
        self.subagent_runtime = subagent_runtime
        self.model = model

    async def run(
        self,
        op: TurnOp,
        *,
        queue_depths: dict[str, int] | None = None,
        status_callback: StatusCallback | None = None,
    ) -> str:
        history = self.store.list_messages(op.thread_id)
        self.store.append_message(MessageRecord(thread_id=op.thread_id, role="user", content=op.user_input))
        self._publish_turn_state(op.thread_id, TurnState.RUNNING, queue_depths, status_callback)
        await self._record_and_publish(op.thread_id, "turn.started", {"input": op.user_input})

        final_text = ""
        async for provider_event in self.provider.stream(
            TurnContext(thread_id=op.thread_id, user_input=op.user_input, history=history)
        ):
            if provider_event.type == "text_delta":
                await self.event_bus.publish(
                    Event(thread_id=op.thread_id, type="assistant.delta", payload={"text": provider_event.payload["text"]})
                )
                continue

            if provider_event.type == "tool_call":
                self._publish_turn_state(op.thread_id, TurnState.WAITING_TOOL, queue_depths, status_callback)
                await self.tool_router.execute(
                    op.thread_id,
                    ToolCall(name=provider_event.payload["tool"], arguments={"input": provider_event.payload["input"]}),
                )
                self._publish_turn_state(op.thread_id, TurnState.RUNNING, queue_depths, status_callback)
                continue

            if provider_event.type == "delegate":
                self._publish_turn_state(op.thread_id, TurnState.WAITING_SUBAGENT, queue_depths, status_callback)
                result = await self.subagent_runtime.run(op.thread_id, provider_event.payload["task"])
                await self.event_bus.publish(
                    Event(thread_id=op.thread_id, type="assistant.note", payload={"text": result})
                )
                self._publish_turn_state(op.thread_id, TurnState.RUNNING, queue_depths, status_callback)
                continue

            if provider_event.type == "final":
                final_text = provider_event.payload["text"]

        self.store.append_message(MessageRecord(thread_id=op.thread_id, role="assistant", content=final_text))
        await self._record_and_publish(op.thread_id, "turn.completed", {"output": final_text})
        self._publish_turn_state(op.thread_id, TurnState.COMPLETED, queue_depths, status_callback)
        return final_text

    async def publish_failure(
        self,
        thread_id: str,
        error: Exception,
        *,
        queue_depths: dict[str, int] | None = None,
        status_callback: StatusCallback | None = None,
    ) -> None:
        await self._record_and_publish(thread_id, "turn.failed", {"error": str(error)})
        self._publish_turn_state(thread_id, TurnState.FAILED, queue_depths, status_callback)

    async def _record_and_publish(self, thread_id: str, event_type: str, payload: dict[str, str]) -> None:
        event = Event(thread_id=thread_id, type=event_type, payload=payload)
        self.event_log.append(event)
        await self.event_bus.publish(event)

    def _publish_turn_state(
        self,
        thread_id: str,
        turn_state: TurnState,
        queue_depths: dict[str, int] | None,
        status_callback: StatusCallback | None,
    ) -> None:
        if status_callback is None:
            return
        status_callback(thread_id, turn_state, queue_depths)
