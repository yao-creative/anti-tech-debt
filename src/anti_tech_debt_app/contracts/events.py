from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import TurnState, utc_now


@dataclass(slots=True)
class Event:
    session_id: str
    type: str
    payload: dict[str, Any]
    created_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class StatusSnapshot:
    session_id: str
    turn_state: TurnState
    model: str
    queue_depths: dict[str, int]
