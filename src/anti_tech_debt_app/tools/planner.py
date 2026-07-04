from __future__ import annotations

from anti_tech_debt_app.tools.registry import ToolCall, ToolResult


class PlannerTool:
    async def execute(self, call: ToolCall) -> ToolResult:
        prompt = call.arguments["input"]
        return ToolResult(
            name=call.name,
            output=f"Plan: inventory debt, rank risk, apply one thin fix for '{prompt}'.",
        )
