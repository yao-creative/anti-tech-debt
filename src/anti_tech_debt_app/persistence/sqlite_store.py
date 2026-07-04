from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

from anti_tech_debt_app.contracts.models import MessageRecord, ThreadRecord


class SQLiteStore:
    """SQLite-backed repository for threads and messages.

    Owns:
        The database path and the relational storage for ``threads`` and
        ``messages``.

    Mutates:
        Durable rows in the SQLite database.

    Observes:
        ThreadRecord and MessageRecord values handed in by the runtime.

    Functional framing:
        A repository algebra for persisting and loading conversation state.

    Category-theoretic framing:
        An interpreter from domain records into durable relational facts.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            self._migrate_legacy_schema(conn)
            conn.execute(
                "create table if not exists threads (thread_id text primary key, title text, created_at text)"
            )
            conn.execute(
                "create table if not exists messages (thread_id text, role text, content text, created_at text)"
            )

    def _migrate_legacy_schema(self, conn: sqlite3.Connection) -> None:
        tables = {
            row[0]
            for row in conn.execute("select name from sqlite_master where type = 'table'").fetchall()
        }
        if "sessions" not in tables:
            return
        has_legacy_messages = "messages" in tables and self._table_has_column(conn, "messages", "session_id")
        if has_legacy_messages:
            conn.execute("alter table messages rename to messages_legacy")
        conn.execute("alter table sessions rename to sessions_legacy")
        conn.execute(
            "create table if not exists threads (thread_id text primary key, title text, created_at text)"
        )
        conn.execute(
            "create table if not exists messages (thread_id text, role text, content text, created_at text)"
        )
        conn.execute(
            "insert or ignore into threads(thread_id, title, created_at) "
            "select session_id, title, created_at from sessions_legacy"
        )
        if has_legacy_messages:
            conn.execute(
                "insert into messages(thread_id, role, content, created_at) "
                "select session_id, role, content, created_at from messages_legacy"
            )
        conn.execute("drop table sessions_legacy")
        if has_legacy_messages:
            conn.execute("drop table messages_legacy")

    def _table_has_column(self, conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
        columns = conn.execute(f"pragma table_info({table_name})").fetchall()
        return any(row[1] == column_name for row in columns)

    def create_thread(self, title: str = "New Thread") -> ThreadRecord:
        record = ThreadRecord(thread_id=str(uuid.uuid4()), title=title)
        with self._connect() as conn:
            conn.execute(
                "insert into threads(thread_id, title, created_at) values (?, ?, ?)",
                (record.thread_id, record.title, record.created_at),
            )
        return record

    def get_thread(self, thread_id: str) -> ThreadRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "select thread_id, title, created_at from threads where thread_id = ?",
                (thread_id,),
            ).fetchone()
        if row is None:
            return None
        return ThreadRecord(thread_id=row[0], title=row[1], created_at=row[2])

    def list_threads(self) -> list[ThreadRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "select thread_id, title, created_at from threads order by created_at desc"
            ).fetchall()
        return [ThreadRecord(thread_id=row[0], title=row[1], created_at=row[2]) for row in rows]

    def append_message(self, message: MessageRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                "insert into messages(thread_id, role, content, created_at) values (?, ?, ?, ?)",
                (message.thread_id, message.role, message.content, message.created_at),
            )

    def list_messages(self, thread_id: str) -> list[MessageRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "select thread_id, role, content, created_at from messages where thread_id = ? order by rowid asc",
                (thread_id,),
            ).fetchall()
        return [
            MessageRecord(thread_id=row[0], role=row[1], content=row[2], created_at=row[3])
            for row in rows
        ]
