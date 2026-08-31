from __future__ import annotations

from contracts.events import Event
from contracts.ports import ApprovalPolicy, ToolExecutor
from runtime.event_bus import EventBus
from tools.registry import ToolCall, ToolResult


class ToolRouter:
    """Approval-gated dispatcher from tool calls to tool results.

    Owns:
        The composition of approval policy, tool registry, and tool-related
        event publication.

    Mutates:
        The EventBus via tool approval and tool result events.
    Observes:
        ToolCall values, ApprovalRuntime decisions, and ToolRegistry output.

    Functional framing:
        An effectful dispatcher ``ToolCall -> ToolResult``.

    Category-theoretic framing:
        A composition of review and execute arrows with writer-like event
        emission attached.
    """

    def __init__(self, registry: ToolExecutor, approvals: ApprovalPolicy, event_bus: EventBus) -> None:
        self.registry = registry
        self.approvals = approvals
        self.event_bus = event_bus

    async def execute(self, thread_id: str, call: ToolCall) -> ToolResult:
        approved = await self.approvals.review(call)
        await self.event_bus.publish(
            Event(thread_id=thread_id, type="tool.approval", payload={"tool": call.name, "approved": str(approved)})
        )
        if not approved:
            return ToolResult(name=call.name, output="Denied by approval runtime.")
        result = await self.registry.execute(call)
        await self.event_bus.publish(
            Event(thread_id=thread_id, type="tool.result", payload={"tool": result.name, "output": result.output})
        )
        return result
