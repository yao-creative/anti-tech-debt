from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TurnOp:
    thread_id: str
    user_input: str
    kind: str = "user_turn"


StartTurn = TurnOp


@dataclass(slots=True)
class InterruptTurn:
    thread_id: str


@dataclass(slots=True)
class ResumeThread:
    thread_id: str
