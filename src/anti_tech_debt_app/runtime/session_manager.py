from __future__ import annotations

import asyncio
from contextlib import suppress

from anti_tech_debt_app.contracts.commands import StartTurn
from anti_tech_debt_app.contracts.events import Event
from anti_tech_debt_app.contracts.queues import TypedQueue
from anti_tech_debt_app.runtime.event_bus import EventBus
from anti_tech_debt_app.runtime.turn_runner import TurnRunner
from anti_tech_debt_app.persistence.sqlite_store import SQLiteStore


class SessionManager:
    def __init__(
        self,
        store: SQLiteStore,
        event_bus: EventBus,
        turn_runner: TurnRunner,
        submission_queue: TypedQueue[StartTurn],
        event_bridge: TypedQueue[Event],
    ) -> None:
        self.store = store
        self.event_bus = event_bus
        self.turn_runner = turn_runner
        self.submission_queue = submission_queue
        self.event_bridge = event_bridge
        self._tasks: list[asyncio.Task[None]] = []

    def create_session(self, title: str = "New Session") -> str:
        return self.store.create_session(title).session_id

    def list_sessions(self) -> list[str]:
        return [record.session_id for record in self.store.list_sessions()]

    async def start(self) -> None:
        self._tasks.append(asyncio.create_task(self._submission_loop()))
        self._tasks.append(asyncio.create_task(self._bridge_loop()))

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with suppress(asyncio.CancelledError):
                await task

    async def submit_turn(self, session_id: str, user_input: str) -> None:
        await self.submission_queue.put(StartTurn(session_id=session_id, user_input=user_input))

    async def _submission_loop(self) -> None:
        while True:
            command = await self.submission_queue.get()
            await self.turn_runner.run(command.session_id, command.user_input)
            self.submission_queue.task_done()

    async def _bridge_loop(self) -> None:
        while True:
            event = await self.event_bridge.get()
            await self.event_bus.publish(event)
            self.event_bridge.task_done()
