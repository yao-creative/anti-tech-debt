from __future__ import annotations

import asyncio
from contextlib import suppress

from anti_tech_debt_app.contracts.commands import TurnOp
from anti_tech_debt_app.contracts.events import RuntimeState
from anti_tech_debt_app.contracts.models import ThreadRecord, ThreadState, TurnState
from anti_tech_debt_app.contracts.ports import ConversationStore
from anti_tech_debt_app.contracts.queues import TypedQueue
from anti_tech_debt_app.runtime.event_bus import EventBus
from anti_tech_debt_app.runtime.turn_loop import TurnLoop


class ThreadRuntime:
    """Runtime-first thread controller for the local TUI."""

    _TERMINAL_TURN_STATES = frozenset({TurnState.COMPLETED, TurnState.FAILED, TurnState.CANCELLED})
    _IN_FLIGHT_TURN_STATES = frozenset({TurnState.RUNNING, TurnState.WAITING_TOOL, TurnState.WAITING_SUBAGENT})

    def __init__(
        self,
        store: ConversationStore,
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
        self._publish_status(thread_id=thread.thread_id, thread_state=ThreadState.ACTIVE, turn_state=TurnState.IDLE)
        return thread.thread_id

    def resume_latest_thread(self) -> str:
        threads = self.store.list_threads()
        if not threads:
            return self.new_thread()
        self._active_thread_id = threads[0].thread_id
        self._publish_status(thread_id=self._active_thread_id, thread_state=ThreadState.ACTIVE, turn_state=TurnState.IDLE)
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
            turn_state = self._stopped_turn_state()
            self._publish_status(
                thread_id=self._active_thread_id,
                thread_state=ThreadState.STOPPED,
                turn_state=turn_state,
                queue_depths=self.queue_depths(),
            )
        self._tasks.clear()

    async def submit(self, op: TurnOp) -> None:
        await self.op_queue.put(op)

    async def submit_turn(self, user_input: str) -> None:
        await self.submit(TurnOp(thread_id=self.active_thread_id(), user_input=user_input))

    def queue_depths(self) -> dict[str, int]:
        return {"turn_input_queue": self.op_queue.qsize()}

    def _publish_status(
        self,
        thread_id: str | None = None,
        *,
        thread_state: ThreadState | None = None,
        turn_state: TurnState | None = None,
        queue_depths: dict[str, int] | None = None,
    ) -> None:
        effective_thread_id = thread_id or self._active_thread_id
        if effective_thread_id is None:
            return
        previous = self.event_bus.status if self.event_bus.status and self.event_bus.status.thread_id == effective_thread_id else None
        self.event_bus.publish_status(
            RuntimeState(
                thread_id=effective_thread_id,
                thread_state=thread_state or (previous.thread_state if previous is not None else ThreadState.ACTIVE),
                turn_state=turn_state or (previous.turn_state if previous is not None else TurnState.IDLE),
                model=self.turn_loop.model,
                queue_depths=queue_depths or self.queue_depths(),
            )
        )

    def _stopped_turn_state(self) -> TurnState:
        status = self.event_bus.status
        if status is None or status.thread_id != self.active_thread_id():
            return TurnState.IDLE
        if status.turn_state in self._TERMINAL_TURN_STATES:
            return status.turn_state
        if status.turn_state in self._IN_FLIGHT_TURN_STATES:
            return TurnState.CANCELLED
        return TurnState.IDLE

    async def _op_loop(self) -> None:
        while True:
            op = await self.op_queue.get()
            self._active_thread_id = op.thread_id
            try:
                await self.turn_loop.run(op, queue_depths=self.queue_depths(), status_callback=self._publish_turn_status)
            except Exception as exc:
                await self.turn_loop.publish_failure(
                    op.thread_id,
                    exc,
                    queue_depths=self.queue_depths(),
                    status_callback=self._publish_turn_status,
                )
            finally:
                self.op_queue.task_done()

    def _publish_turn_status(self, thread_id: str, turn_state: TurnState, queue_depths: dict[str, int] | None) -> None:
        self._publish_status(
            thread_id=thread_id,
            thread_state=ThreadState.ACTIVE,
            turn_state=turn_state,
            queue_depths=queue_depths,
        )
