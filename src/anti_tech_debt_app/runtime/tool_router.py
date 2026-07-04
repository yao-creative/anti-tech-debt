from __future__ import annotations

from anti_tech_debt_app.contracts.events import Event
from anti_tech_debt_app.runtime.approval_runtime import ApprovalRuntime
from anti_tech_debt_app.runtime.event_bus import EventBus
from anti_tech_debt_app.tools.registry import ToolCall, ToolRegistry, ToolResult


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

    def __init__(self, registry: ToolRegistry, approvals: ApprovalRuntime, event_bus: EventBus) -> None:
        self.registry = registry
        self.approvals = approvals
        self.event_bus = event_bus

    async def execute(self, session_id: str, call: ToolCall) -> ToolResult:
        approved = await self.approvals.review(call)
        await self.event_bus.publish(
            Event(session_id=session_id, type="tool.approval", payload={"tool": call.name, "approved": str(approved)})
        )
        if not approved:
            return ToolResult(name=call.name, output="Denied by approval runtime.")
        result = await self.registry.execute(call)
        await self.event_bus.publish(
            Event(session_id=session_id, type="tool.result", payload={"tool": result.name, "output": result.output})
        )
        return result
