from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TurnOp:
    session_id: str
    user_input: str
    kind: str = "user_turn"


StartTurn = TurnOp


@dataclass(slots=True)
class InterruptTurn:
    session_id: str


@dataclass(slots=True)
class ResumeSession:
    session_id: str
