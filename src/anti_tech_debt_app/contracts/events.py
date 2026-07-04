from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import SessionState, TurnState, utc_now


@dataclass(slots=True)
class RuntimeEvent:
    session_id: str
    type: str
    payload: dict[str, Any]
    created_at: str = field(default_factory=utc_now)


Event = RuntimeEvent


@dataclass(slots=True)
class RuntimeState:
    session_id: str
    session_state: SessionState
    turn_state: TurnState
    model: str
    queue_depths: dict[str, int] = field(default_factory=dict)


StatusSnapshot = RuntimeState
