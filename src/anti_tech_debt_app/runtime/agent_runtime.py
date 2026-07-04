from __future__ import annotations

from anti_tech_debt_app.contracts.events import Event
from anti_tech_debt_app.contracts.models import TurnContext
from anti_tech_debt_app.contracts.queues import TypedQueue
from anti_tech_debt_app.providers.base import ProviderAdapter
from anti_tech_debt_app.runtime.subagent_runtime import SubagentRuntime
from anti_tech_debt_app.runtime.tool_router import ToolRouter
from anti_tech_debt_app.tools.registry import ToolCall


class AgentRuntime:
    """Provider-driven interpreter for one agent turn.

    Owns:
        The turn-local orchestration logic that connects provider events,
        tool dispatch, delegation, and bridged UI events.

    Mutates:
        ``event_bridge`` by emitting assistant and delegation events.

    Observes:
        ProviderEvent values, ToolRouter effects, and SubagentRuntime
        results.

    Functional framing:
        A reducer over a streamed provider program that accumulates the final
        assistant text while emitting side effects.

    Category-theoretic framing:
        A fold over an event algebra into the runtime effect category.
    """

    def __init__(
        self,
        provider: ProviderAdapter,
        tool_router: ToolRouter,
        subagent_runtime: SubagentRuntime,
        event_bridge: TypedQueue[Event],
    ) -> None:
        self.provider = provider
        self.tool_router = tool_router
        self.subagent_runtime = subagent_runtime
        self.event_bridge = event_bridge

    async def run(self, turn_context: TurnContext) -> str:
        final_text = ""
        async for provider_event in self.provider.stream(turn_context):
            if provider_event.type == "text_delta":
                await self.event_bridge.put(
                    Event(
                        session_id=turn_context.session_id,
                        type="assistant.delta",
                        payload={"text": provider_event.payload["text"]},
                    )
                )
            elif provider_event.type == "tool_call":
                await self.tool_router.execute(
                    turn_context.session_id,
                    ToolCall(name=provider_event.payload["tool"], arguments={"input": provider_event.payload["input"]}),
                )
            elif provider_event.type == "delegate":
                result = await self.subagent_runtime.run(turn_context.session_id, provider_event.payload["task"])
                await self.event_bridge.put(
                    Event(
                        session_id=turn_context.session_id,
                        type="assistant.note",
                        payload={"text": result},
                    )
                )
            elif provider_event.type == "final":
                final_text = provider_event.payload["text"]
        return final_text
