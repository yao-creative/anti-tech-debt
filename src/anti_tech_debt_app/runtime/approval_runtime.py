from __future__ import annotations

from anti_tech_debt_app.tools.registry import ToolCall


class ApprovalRuntime:
    """Approval predicate for tool execution.

    Owns:
        The current approval policy configuration.

    Mutates:
        No shared state in the current implementation.

    Observes:
        ToolCall values.

    Functional framing:
        An async predicate over tool calls.

    Category-theoretic framing:
        A morphism from tool-call objects into a two-valued approval object.
    """

    def __init__(self, auto_approve: bool = True) -> None:
        self.auto_approve = auto_approve

    async def review(self, call: ToolCall) -> bool:
        return self.auto_approve or call.name != "shell"
