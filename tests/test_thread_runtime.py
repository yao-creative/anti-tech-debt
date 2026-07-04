from __future__ import annotations

from anti_tech_debt_app.bootstrap.container import Container
from anti_tech_debt_app.config import AppConfig


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
