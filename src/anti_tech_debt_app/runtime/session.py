from __future__ import annotations

import asyncio
from contextlib import suppress

from anti_tech_debt_app.contracts.commands import TurnOp
from anti_tech_debt_app.contracts.events import RuntimeState
from anti_tech_debt_app.contracts.models import SessionState, TurnState
from anti_tech_debt_app.contracts.queues import TypedQueue
from anti_tech_debt_app.persistence.sqlite_store import SQLiteStore
from anti_tech_debt_app.runtime.event_bus import EventBus
from anti_tech_debt_app.runtime.turn_loop import TurnLoop


class SessionRuntime:
    """Runtime-first session/thread controller for the local TUI.

    Owns:
        Session lifecycle entrypoints, the inbound turn queue, and the single
        background loop that drains turn submissions into the canonical
        TurnLoop.

    Mutates:
        Queue progress, background tasks, and published session status.

    Observes:
        TurnOp values from the inbound queue and persisted session rows from
        SQLiteStore.

    Functional framing:
        A small executor that feeds turn operations into a single runtime
        loop.

    Category-theoretic framing:
        A sequencing object that composes user operations with turn-execution
        morphisms.
    """

    def __init__(
        self,
        store: SQLiteStore,
        event_bus: EventBus,
        turn_loop: TurnLoop,
        op_queue: TypedQueue[TurnOp],
    ) -> None:
        self.store = store
        self.event_bus = event_bus
        self.turn_loop = turn_loop
        self.op_queue = op_queue
        self._tasks: list[asyncio.Task[None]] = []

    def create_session(self, title: str = "New Session") -> str:
        return self.store.create_session(title).session_id

    def list_sessions(self) -> list[str]:
        return [record.session_id for record in self.store.list_sessions()]

    def subscribe(self) -> asyncio.Queue:
        return self.event_bus.subscribe()

    async def start(self) -> None:
        self.event_bus.publish_status(
            RuntimeState(
                session_id="runtime",
                session_state=SessionState.ACTIVE,
                turn_state=TurnState.IDLE,
                model=self.turn_loop.model,
                queue_depths=self.queue_depths(),
            )
        )
        self._tasks.append(asyncio.create_task(self._op_loop()))

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with suppress(asyncio.CancelledError):
                await task
        self.event_bus.publish_status(
            RuntimeState(
                session_id="runtime",
                session_state=SessionState.STOPPED,
                turn_state=TurnState.IDLE,
                model=self.turn_loop.model,
                queue_depths=self.queue_depths(),
            )
        )

    async def submit(self, op: TurnOp) -> None:
        await self.op_queue.put(op)

    async def submit_turn(self, session_id: str, user_input: str) -> None:
        await self.submit(TurnOp(session_id=session_id, user_input=user_input))

    def queue_depths(self) -> dict[str, int]:
        return {"turn_input_queue": self.op_queue.qsize()}

    async def _op_loop(self) -> None:
        while True:
            op = await self.op_queue.get()
            try:
                await self.turn_loop.run(op, queue_depths=self.queue_depths())
            except Exception as exc:
                await self.turn_loop.publish_failure(op.session_id, exc, queue_depths=self.queue_depths())
            finally:
                self.op_queue.task_done()
