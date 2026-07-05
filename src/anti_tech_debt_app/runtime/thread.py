from __future__ import annotations

import asyncio
from contextlib import suppress

from anti_tech_debt_app.contracts.commands import TurnOp
from anti_tech_debt_app.contracts.events import RuntimeState
from anti_tech_debt_app.contracts.models import ThreadRecord, ThreadState, TurnState
from anti_tech_debt_app.contracts.queues import TypedQueue
from anti_tech_debt_app.persistence.sqlite_store import SQLiteStore
from anti_tech_debt_app.runtime.event_bus import EventBus
from anti_tech_debt_app.runtime.turn_loop import TurnLoop


class ThreadRuntime:
    """Runtime-first thread controller for the local TUI."""

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
        self._active_thread_id: str | None = None

    def active_thread_id(self) -> str:
        if self._active_thread_id is None:
            raise RuntimeError("Thread runtime has not been started.")
        return self._active_thread_id

    def new_thread(self, title: str = "Interactive Thread") -> str:
        thread = self.store.create_thread(title)
        self._active_thread_id = thread.thread_id
        self._publish_status(TurnState.IDLE)
        return thread.thread_id

    def resume_latest_thread(self) -> str:
        threads = self.store.list_threads()
        if not threads:
            return self.new_thread()
        self._active_thread_id = threads[0].thread_id
        self._publish_status(TurnState.IDLE)
        return self._active_thread_id

    def list_threads(self) -> list[ThreadRecord]:
        return self.store.list_threads()

    def subscribe(self) -> asyncio.Queue:
        return self.event_bus.subscribe()

    async def start(self) -> None:
        if self._tasks:
            return
        self.resume_latest_thread()
        self._tasks.append(asyncio.create_task(self._op_loop()))

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with suppress(asyncio.CancelledError):
                await task
        if self._active_thread_id is not None:
            self.event_bus.publish_status(
                RuntimeState(
                    thread_id=self._active_thread_id,
                    thread_state=ThreadState.STOPPED,
                    turn_state=TurnState.IDLE,
                    model=self.turn_loop.model,
                    queue_depths=self.queue_depths(),
                )
            )
        self._tasks.clear()

    async def submit(self, op: TurnOp) -> None:
        await self.op_queue.put(op)

    async def submit_turn(self, user_input: str) -> None:
        await self.submit(TurnOp(thread_id=self.active_thread_id(), user_input=user_input))

    def queue_depths(self) -> dict[str, int]:
        return {"turn_input_queue": self.op_queue.qsize()}

    def _publish_status(self, turn_state: TurnState) -> None:
        if self._active_thread_id is None:
            return
        self.event_bus.publish_status(
            RuntimeState(
                thread_id=self._active_thread_id,
                thread_state=ThreadState.ACTIVE,
                turn_state=turn_state,
                model=self.turn_loop.model,
                queue_depths=self.queue_depths(),
            )
        )

    async def _op_loop(self) -> None:
        while True:
            op = await self.op_queue.get()
            self._active_thread_id = op.thread_id
            try:
                await self.turn_loop.run(op, queue_depths=self.queue_depths())
            except Exception as exc:
                await self.turn_loop.publish_failure(op.thread_id, exc, queue_depths=self.queue_depths())
            finally:
                self.op_queue.task_done()
