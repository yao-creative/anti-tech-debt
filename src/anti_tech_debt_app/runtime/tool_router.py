from __future__ import annotations

from anti_tech_debt_app.contracts.events import Event
from anti_tech_debt_app.runtime.approval_runtime import ApprovalRuntime
from anti_tech_debt_app.runtime.event_bus import EventBus
from anti_tech_debt_app.tools.registry import ToolCall, ToolRegistry, ToolResult


class ToolRouter:
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
