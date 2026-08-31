from __future__ import annotations

from tools.registry import ToolCall, ToolResult


class PlannerTool:
    """Single built-in planner tool for the scaffold.

    Owns:
        The planner transformation from one textual request to one textual
        plan summary.

    Mutates:
        Nothing.

    Observes:
        ToolCall arguments.

    Functional framing:
        A total function from planner input to ToolResult, presented as async
        for interface uniformity.

    Category-theoretic framing:
        A pure morphism in the domain layer lifted into the runtime effect
        boundary.
    """

    async def execute(self, call: ToolCall) -> ToolResult:
        prompt = call.arguments["input"]
        return ToolResult(
            name=call.name,
            output=f"Plan: inventory debt, rank risk, apply one thin fix for '{prompt}'.",
        )
