from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

from anti_tech_debt_app.contracts.models import MessageRecord, SessionRecord


class SQLiteStore:
    """SQLite-backed repository for sessions and messages.

    Owns:
        The database path and the relational storage for ``sessions`` and
        ``messages``.

    Mutates:
        Durable rows in the SQLite database.

    Observes:
        SessionRecord and MessageRecord values handed in by the runtime.

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
            conn.execute(
                "create table if not exists sessions (session_id text primary key, title text, created_at text)"
            )
            conn.execute(
                "create table if not exists messages (session_id text, role text, content text, created_at text)"
            )

    def create_session(self, title: str = "New Session") -> SessionRecord:
        record = SessionRecord(session_id=str(uuid.uuid4()), title=title)
        with self._connect() as conn:
            conn.execute(
                "insert into sessions(session_id, title, created_at) values (?, ?, ?)",
                (record.session_id, record.title, record.created_at),
            )
        return record

    def get_session(self, session_id: str) -> SessionRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "select session_id, title, created_at from sessions where session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return SessionRecord(session_id=row[0], title=row[1], created_at=row[2])

    def list_sessions(self) -> list[SessionRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "select session_id, title, created_at from sessions order by created_at desc"
            ).fetchall()
        return [SessionRecord(session_id=row[0], title=row[1], created_at=row[2]) for row in rows]

    def append_message(self, message: MessageRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                "insert into messages(session_id, role, content, created_at) values (?, ?, ?, ?)",
                (message.session_id, message.role, message.content, message.created_at),
            )

    def list_messages(self, session_id: str) -> list[MessageRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "select session_id, role, content, created_at from messages where session_id = ? order by rowid asc",
                (session_id,),
            ).fetchall()
        return [
            MessageRecord(session_id=row[0], role=row[1], content=row[2], created_at=row[3])
            for row in rows
        ]
