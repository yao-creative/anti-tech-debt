from __future__ import annotations

from anti_tech_debt_app.runtime.event_bus import EventBus


class StatusBar:
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    def current_line(self) -> str:
        status = self.event_bus.status
        if status is None:
            return "state=idle"
        return f"state={status.turn_state.value} model={status.model}"
