from __future__ import annotations

from collections.abc import AsyncIterator

from anti_tech_debt_app.contracts.commands import TurnOp
from anti_tech_debt_app.contracts.events import Event
from anti_tech_debt_app.contracts.models import MessageRecord, ThreadRecord, TurnContext, TurnState
from anti_tech_debt_app.contracts.ports import ProviderEvent
from anti_tech_debt_app.contracts.queues import TypedQueue
from anti_tech_debt_app.runtime.approval_runtime import ApprovalRuntime
from anti_tech_debt_app.runtime.event_bus import EventBus
from anti_tech_debt_app.runtime.thread import ThreadRuntime
from anti_tech_debt_app.runtime.tool_router import ToolRouter
from anti_tech_debt_app.runtime.turn_loop import TurnLoop
from anti_tech_debt_app.tools.registry import ToolCall, ToolResult


class FakeStore:
    def __init__(self) -> None:
        self.created_threads: list[ThreadRecord] = []
        self.messages: dict[str, list[MessageRecord]] = {}

    def create_thread(self, title: str = "New Thread") -> ThreadRecord:
        thread = ThreadRecord(thread_id=f"thread-{len(self.created_threads) + 1}", title=title)
        self.created_threads.append(thread)
        self.messages.setdefault(thread.thread_id, [])
        return thread

    def get_thread(self, thread_id: str) -> ThreadRecord | None:
        for thread in self.created_threads:
            if thread.thread_id == thread_id:
                return thread
        return None

    def list_threads(self) -> list[ThreadRecord]:
        return list(reversed(self.created_threads))

    def append_message(self, message: MessageRecord) -> None:
        self.messages.setdefault(message.thread_id, []).append(message)

    def list_messages(self, thread_id: str) -> list[MessageRecord]:
        return list(self.messages.get(thread_id, []))


class FakeEventLog:
    def __init__(self) -> None:
        self.events: list[Event] = []

    def append(self, event: Event) -> None:
        self.events.append(event)


class FakeProvider:
    def __init__(self, events: list[ProviderEvent]) -> None:
        self.events = events
        self.contexts: list[TurnContext] = []

    async def stream(self, turn_context: TurnContext) -> AsyncIterator[ProviderEvent]:
        self.contexts.append(turn_context)
        for event in self.events:
            yield event


class FakeSubagent:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def run(self, thread_id: str, task: str) -> str:
        self.calls.append((thread_id, task))
        return f"delegated:{task}"


class FakeToolExecutor:
    def __init__(self, result: ToolResult | None = None) -> None:
        self.calls: list[ToolCall] = []
        self.result = result or ToolResult(name="planner", output="ok")

    def names(self) -> list[str]:
        return [self.result.name]

    async def execute(self, call: ToolCall) -> ToolResult:
        self.calls.append(call)
        return self.result


class FakeApprovalPolicy:
    def __init__(self, approved: bool) -> None:
        self.approved = approved
        self.calls: list[ToolCall] = []

    async def review(self, call: ToolCall) -> bool:
        self.calls.append(call)
        return self.approved


class RaisingProvider:
    async def stream(self, turn_context: TurnContext) -> AsyncIterator[ProviderEvent]:
        raise RuntimeError("boom")
        yield


async def test_turn_loop_accepts_fake_ports_and_persists_result() -> None:
    store = FakeStore()
    thread = store.create_thread("test")
    store.append_message(MessageRecord(thread_id=thread.thread_id, role="assistant", content="earlier"))
    event_log = FakeEventLog()
    event_bus = EventBus()
    provider = FakeProvider(
        [
            ProviderEvent("text_delta", {"text": "thinking"}),
            ProviderEvent("tool_call", {"tool": "planner", "input": "reduce blast radius"}),
            ProviderEvent("delegate", {"task": "audit hotspot"}),
            ProviderEvent("final", {"text": "done"}),
        ]
    )
    tool_executor = FakeToolExecutor(ToolResult(name="planner", output="planned"))
    tool_router = ToolRouter(tool_executor, ApprovalRuntime(auto_approve=True), event_bus)
    subagent = FakeSubagent()
    turn_loop = TurnLoop(store, event_log, event_bus, provider, tool_router, subagent, "test-model")
    queue = event_bus.subscribe()
    status_calls: list[tuple[str, TurnState, dict[str, int] | None]] = []

    result = await turn_loop.run(
        TurnOp(thread_id=thread.thread_id, user_input="refactor later"),
        status_callback=lambda thread_id, turn_state, queue_depths: status_calls.append(
            (thread_id, turn_state, queue_depths)
        ),
    )

    assert result == "done"
    assert provider.contexts[0].history[0].content == "earlier"
    assert tool_executor.calls == [ToolCall(name="planner", arguments={"input": "reduce blast radius"})]
    assert subagent.calls == [(thread.thread_id, "audit hotspot")]
    assert [event.type for event in event_log.events] == ["turn.started", "turn.completed"]
    assert store.list_messages(thread.thread_id)[-1].content == "done"
    assert [turn_state for _, turn_state, _ in status_calls] == [
        TurnState.RUNNING,
        TurnState.WAITING_TOOL,
        TurnState.RUNNING,
        TurnState.WAITING_SUBAGENT,
        TurnState.RUNNING,
        TurnState.COMPLETED,
    ]

    seen_types = [queue.get_nowait().type for _ in range(5)]
    assert seen_types == [
        "turn.started",
        "assistant.delta",
        "tool.approval",
        "tool.result",
        "assistant.note",
    ]


async def test_tool_router_accepts_fake_executor_and_policy() -> None:
    event_bus = EventBus()
    queue = event_bus.subscribe()
    tool_executor = FakeToolExecutor(ToolResult(name="planner", output="tool-output"))
    approvals = FakeApprovalPolicy(approved=True)
    router = ToolRouter(tool_executor, approvals, event_bus)

    result = await router.execute("thread-1", ToolCall(name="planner", arguments={"input": "x"}))

    approval_event = queue.get_nowait()
    result_event = queue.get_nowait()
    assert result.output == "tool-output"
    assert approvals.calls == [ToolCall(name="planner", arguments={"input": "x"})]
    assert tool_executor.calls == [ToolCall(name="planner", arguments={"input": "x"})]
    assert approval_event.type == "tool.approval"
    assert result_event.type == "tool.result"


async def test_thread_runtime_uses_store_port_for_thread_lifecycle() -> None:
    store = FakeStore()
    event_bus = EventBus()
    op_queue: TypedQueue[TurnOp] = TypedQueue("turn_input", maxsize=4)
    turn_loop = TurnLoop(
        store,
        FakeEventLog(),
        event_bus,
        FakeProvider([ProviderEvent("final", {"text": "done"})]),
        ToolRouter(FakeToolExecutor(), ApprovalRuntime(auto_approve=True), event_bus),
        FakeSubagent(),
        "test-model",
    )
    runtime = ThreadRuntime(store, event_bus, turn_loop, op_queue)

    await runtime.start()
    try:
        active = runtime.active_thread_id()
        assert store.get_thread(active) is not None
        assert runtime.list_threads()[0].thread_id == active
    finally:
        await runtime.stop()


async def test_turn_loop_publish_failure_reports_failed_status() -> None:
    store = FakeStore()
    thread = store.create_thread("test")
    event_log = FakeEventLog()
    event_bus = EventBus()
    turn_loop = TurnLoop(
        store,
        event_log,
        event_bus,
        RaisingProvider(),
        ToolRouter(FakeToolExecutor(), ApprovalRuntime(auto_approve=True), event_bus),
        FakeSubagent(),
        "test-model",
    )
    status_calls: list[tuple[str, TurnState, dict[str, int] | None]] = []

    await turn_loop.publish_failure(
        thread.thread_id,
        RuntimeError("boom"),
        status_callback=lambda thread_id, turn_state, queue_depths: status_calls.append(
            (thread_id, turn_state, queue_depths)
        ),
    )

    assert [event.type for event in event_log.events] == ["turn.failed"]
    assert status_calls == [(thread.thread_id, TurnState.FAILED, None)]
