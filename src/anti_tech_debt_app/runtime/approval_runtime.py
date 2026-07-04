from __future__ import annotations

from anti_tech_debt_app.tools.registry import ToolCall


class ApprovalRuntime:
    def __init__(self, auto_approve: bool = True) -> None:
        self.auto_approve = auto_approve

    async def review(self, call: ToolCall) -> bool:
        return self.auto_approve or call.name != "shell"
