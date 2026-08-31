from __future__ import annotations

import asyncio

from tools.registry import ToolCall, ToolResult


class ShellEchoTool:
    async def execute(self, call: ToolCall) -> ToolResult:
        process = await asyncio.create_subprocess_exec(
            "printf",
            "%s",
            call.arguments["input"],
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate()
        return ToolResult(name=call.name, output=stdout.decode())
