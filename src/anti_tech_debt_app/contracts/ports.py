from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

from anti_tech_debt_app.contracts.events import Event
from anti_tech_debt_app.contracts.models import MessageRecord, ThreadRecord, TurnContext
from anti_tech_debt_app.tools.registry import ToolCall, ToolResult


@dataclass(slots=True)
class ProviderEvent:
    type: str
    payload: dict[str, str]


class ProviderAdapter(Protocol):
    async def stream(self, turn_context: TurnContext) -> AsyncIterator[ProviderEvent]:
        ...


class ConversationStore(Protocol):
    def create_thread(self, title: str = "New Thread") -> ThreadRecord:
        ...

    def get_thread(self, thread_id: str) -> ThreadRecord | None:
        ...

    def list_threads(self) -> list[ThreadRecord]:
        ...

    def append_message(self, message: MessageRecord) -> None:
        ...

    def list_messages(self, thread_id: str) -> list[MessageRecord]:
        ...


class EventRecorder(Protocol):
    def append(self, event: Event) -> None:
        ...


class ToolExecutor(Protocol):
    def names(self) -> list[str]:
        ...

    async def execute(self, call: ToolCall) -> ToolResult:
        ...


class ApprovalPolicy(Protocol):
    async def review(self, call: ToolCall) -> bool:
        ...


class SubagentExecutor(Protocol):
    async def run(self, thread_id: str, task: str) -> str:
        ...
