from __future__ import annotations

from pathlib import Path

from anti_tech_debt_app.tools.registry import ToolCall, ToolResult


class FilesystemReadTool:
    async def execute(self, call: ToolCall) -> ToolResult:
        path = Path(call.arguments["path"])
        return ToolResult(name=call.name, output=path.read_text()[:500])
