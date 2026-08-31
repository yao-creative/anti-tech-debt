from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from anti_tech_debt_app.bootstrap.container import Container
from anti_tech_debt_app.config import AppConfig
from anti_tech_debt_app.contracts.commands import TurnOp
from anti_tech_debt_app.contracts.events import Event
from anti_tech_debt_app.contracts.models import TurnContext
from anti_tech_debt_app.contracts.ports import ProviderEvent
from anti_tech_debt_app.contracts.queues import TypedQueue
from anti_tech_debt_app.runtime.approval_runtime import ApprovalRuntime
from anti_tech_debt_app.runtime.event_bus import EventBus
from anti_tech_debt_app.runtime.subagent_runtime import SubagentRuntime
from anti_tech_debt_app.runtime.thread import ThreadRuntime
from anti_tech_debt_app.runtime.tool_router import ToolRouter
from anti_tech_debt_app.runtime.turn_loop import TurnLoop
from anti_tech_debt_app.tools.registry import ToolResult


class BlockingProvider:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def stream(self, turn_context: TurnContext) -> AsyncIterator[ProviderEvent]:
        self.started.set()
        yield ProviderEvent("text_delta", {"text": "waiting"})
        await self.release.wait()
        yield ProviderEvent("final", {"text": "done"})


async def test_thread_runtime_start_creates_active_thread(tmp_path) -> None:
    container = Container(
        AppConfig(
            database_path=tmp_path / "state.db",
            event_log_path=tmp_path / "events.jsonl",
        )
    )

    await container.thread_runtime.start()
    try:
        active = container.thread_runtime.active_thread_id()
        assert container.store.get_thread(active) is not None
        assert container.event_bus.status is not None
        assert container.event_bus.status.thread_id == active
        assert container.event_bus.status.thread_state.value == "active"
        assert container.event_bus.status.turn_state.value == "idle"
    finally:
        await container.thread_runtime.stop()


async def test_thread_runtime_start_resumes_latest_thread(tmp_path) -> None:
    container = Container(
        AppConfig(
            database_path=tmp_path / "state.db",
            event_log_path=tmp_path / "events.jsonl",
        )
    )
    first = container.store.create_thread("first").thread_id
    latest = container.store.create_thread("latest").thread_id

    await container.thread_runtime.start()
    try:
        assert container.thread_runtime.active_thread_id() == latest
    finally:
        await container.thread_runtime.stop()

    assert first != latest


async def test_thread_runtime_start_is_idempotent(tmp_path) -> None:
    container = Container(
        AppConfig(
            database_path=tmp_path / "state.db",
            event_log_path=tmp_path / "events.jsonl",
        )
    )

    await container.thread_runtime.start()
    first_task_count = len(container.thread_runtime._tasks)
    await container.thread_runtime.start()
    try:
        assert len(container.thread_runtime._tasks) == first_task_count == 1
    finally:
        await container.thread_runtime.stop()


async def test_thread_runtime_stop_preserves_completed_turn_state(tmp_path) -> None:
    container = Container(
        AppConfig(
            database_path=tmp_path / "state.db",
            event_log_path=tmp_path / "events.jsonl",
        )
    )

    await container.thread_runtime.start()
    try:
        await container.thread_runtime.submit_turn("Finish the task")
        queue = container.thread_runtime.subscribe()
        while True:
            event = await queue.get()
            if event.type == "turn.completed":
                break
    finally:
        await container.thread_runtime.stop()

    assert container.event_bus.status is not None
    assert container.event_bus.status.thread_state.value == "stopped"
    assert container.event_bus.status.turn_state.value == "completed"


async def test_thread_runtime_stop_marks_in_flight_turn_cancelled(tmp_path) -> None:
    container = Container(
        AppConfig(
            database_path=tmp_path / "state.db",
            event_log_path=tmp_path / "events.jsonl",
        )
    )
    blocking_provider = BlockingProvider()
    container.turn_loop.provider = blocking_provider

    await container.thread_runtime.start()
    await container.thread_runtime.submit_turn("Block on provider")
    await blocking_provider.started.wait()
    await container.thread_runtime.stop()

    assert container.event_bus.status is not None
    assert container.event_bus.status.thread_state.value == "stopped"
    assert container.event_bus.status.turn_state.value == "cancelled"
