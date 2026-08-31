from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class TurnState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING_TOOL = "waiting_tool"
    WAITING_SUBAGENT = "waiting_subagent"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ThreadState(str, Enum):
    IDLE = "idle"
    ACTIVE = "active"
    STOPPED = "stopped"


@dataclass(slots=True)
class ThreadRecord:
    thread_id: str
    title: str
    created_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class MessageRecord:
    thread_id: str
    role: str
    content: str
    created_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class TurnContext:
    thread_id: str
    user_input: str
    history: list[MessageRecord]
    allow_delegate: bool = True
