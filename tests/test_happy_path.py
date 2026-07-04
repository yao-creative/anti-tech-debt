from __future__ import annotations

from anti_tech_debt_app.bootstrap.container import Container
from anti_tech_debt_app.config import AppConfig


async def test_turn_happy_path(tmp_path) -> None:
    config = AppConfig(
        database_path=tmp_path / "state.db",
        event_log_path=tmp_path / "events.jsonl",
    )
    container = Container(config)
    session_id = container.session_runtime.create_session("test")
    queue = container.session_runtime.subscribe()
    await container.session_runtime.start()
    try:
        await container.session_runtime.submit_turn(session_id, "Fix duplicate abstractions")
        events = []
        while True:
            event = await queue.get()
            events.append(event)
            if event.type == "turn.completed":
                break
    finally:
        await container.session_runtime.stop()
    event_types = [event.type for event in events]
    assert "turn.started" in event_types
    assert "assistant.delta" in event_types
    assert "tool.result" in event_types
    assert "subagent.completed" in event_types
    assert "turn.completed" in event_types
    replay = container.event_log.replay()
    assert replay[-1]["type"] == "turn.completed"
    messages = container.store.list_messages(session_id)
    assert messages[-1].role == "assistant"
    assert "Happy path complete" in messages[-1].content
    assert container.event_bus.status is not None
    assert container.event_bus.status.turn_state.value == "completed"
