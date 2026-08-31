from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class ToolCall:
    name: str
    arguments: dict[str, str]


@dataclass(slots=True)
class ToolResult:
    name: str
    output: str


class Tool(Protocol):
    async def execute(self, call: ToolCall) -> ToolResult:
        ...


class ToolRegistry:
    """Name-indexed registry of available tools.

    Owns:
        The mapping from tool names to tool implementations.

    Mutates:
        No runtime state after initialization in the current scaffold.

    Observes:
        ToolCall names and arguments.

    Functional framing:
        A dictionary-backed dispatcher over a small tool algebra.

    Category-theoretic framing:
        An indexed family of executable arrows selected by tool name.
    """

    def __init__(self, tools: dict[str, Tool]) -> None:
        self._tools = tools

    def names(self) -> list[str]:
        return sorted(self._tools)

    async def execute(self, call: ToolCall) -> ToolResult:
        tool = self._tools[call.name]
        return await tool.execute(call)
