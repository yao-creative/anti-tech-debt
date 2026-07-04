from __future__ import annotations

from anti_tech_debt_app.contracts.events import Event
from anti_tech_debt_app.contracts.queues import TypedQueue
from anti_tech_debt_app.runtime.subagent_runtime import SubagentRuntime


async def test_subagent_bridge_emits_started_and_completed() -> None:
    bridge: TypedQueue[Event] = TypedQueue("bridge", maxsize=4)
    runtime = SubagentRuntime(bridge)
    result = await runtime.run("thread-1", "inspect module")
    started = bridge.get_nowait()
    completed = bridge.get_nowait()
    assert started.thread_id == "thread-1"
    assert started.type == "subagent.started"
    assert completed.thread_id == "thread-1"
    assert completed.type == "subagent.completed"
    assert "inspect module" in result
