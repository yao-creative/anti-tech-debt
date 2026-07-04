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


def test_legacy_session_schema_migrates_to_threads(tmp_path) -> None:
    database_path = tmp_path / "state.db"
    with sqlite3.connect(database_path) as conn:
        conn.execute("create table sessions (session_id text primary key, title text, created_at text)")
        conn.execute("create table messages (session_id text, role text, content text, created_at text)")
        conn.execute(
            "insert into sessions(session_id, title, created_at) values (?, ?, ?)",
            ("legacy-thread", "legacy", "2026-01-01T00:00:00+00:00"),
        )
        conn.execute(
            "insert into messages(session_id, role, content, created_at) values (?, ?, ?, ?)",
            ("legacy-thread", "user", "hello", "2026-01-01T00:00:01+00:00"),
        )

    container = Container(
        AppConfig(
            database_path=database_path,
            event_log_path=tmp_path / "events.jsonl",
        )
    )

    assert container.store.get_thread("legacy-thread") is not None
    assert container.store.list_messages("legacy-thread")[0].content == "hello"
    with sqlite3.connect(database_path) as conn:
        tables = {row[0] for row in conn.execute("select name from sqlite_master where type = 'table'")}
    assert "threads" in tables
    assert "sessions" not in tables


def test_legacy_sessions_without_messages_still_migrate(tmp_path) -> None:
    database_path = tmp_path / "state.db"
    with sqlite3.connect(database_path) as conn:
        conn.execute("create table sessions (session_id text primary key, title text, created_at text)")
        conn.execute(
            "insert into sessions(session_id, title, created_at) values (?, ?, ?)",
            ("legacy-thread", "legacy", "2026-01-01T00:00:00+00:00"),
        )

    container = Container(
        AppConfig(
            database_path=database_path,
            event_log_path=tmp_path / "events.jsonl",
        )
    )

    assert container.store.get_thread("legacy-thread") is not None
    assert container.store.list_messages("legacy-thread") == []
