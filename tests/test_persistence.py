from __future__ import annotations

import sqlite3

from anti_tech_debt_app.bootstrap.container import Container
from anti_tech_debt_app.config import AppConfig
from anti_tech_debt_app.contracts.models import MessageRecord


def test_thread_persistence_and_event_replay(tmp_path) -> None:
    config = AppConfig(
        database_path=tmp_path / "state.db",
        event_log_path=tmp_path / "events.jsonl",
    )
    container = Container(config)
    thread_id = container.store.create_thread("persistent").thread_id
    container.store.append_message(MessageRecord(thread_id=thread_id, role="user", content="hello"))
    assert container.store.get_thread(thread_id) is not None
    assert container.store.list_messages(thread_id)[0].content == "hello"
    assert container.event_log.replay() == []


def test_store_bootstraps_fresh_thread_schema(tmp_path) -> None:
    database_path = tmp_path / "state.db"
    container = Container(
        AppConfig(
            database_path=database_path,
            event_log_path=tmp_path / "events.jsonl",
        )
    )

    thread_id = container.store.create_thread("fresh").thread_id

    with sqlite3.connect(database_path) as conn:
        tables = {row[0] for row in conn.execute("select name from sqlite_master where type = 'table'")}
        thread_columns = [row[1] for row in conn.execute("pragma table_info(threads)")]
        message_columns = [row[1] for row in conn.execute("pragma table_info(messages)")]

    assert "threads" in tables
    assert "messages" in tables
    assert "sessions" not in tables
    assert thread_columns == ["thread_id", "title", "created_at"]
    assert message_columns == ["thread_id", "role", "content", "created_at"]
    assert container.store.get_thread(thread_id) is not None
