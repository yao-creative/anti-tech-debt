from __future__ import annotations

from anti_tech_debt_app.runtime.event_bus import EventBus


class StatusBar:
    """Read-only adapter for the current runtime state.

    Owns:
        The formatting rule for a compact status line.

    Mutates:
        Nothing.

    Observes:
        EventBus.status.

    Functional framing:
        A projection from runtime status into a compact textual summary.

    Category-theoretic framing:
        A forgetful map from richer runtime state to one visible status
        string.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    def current_line(self) -> str:
        status = self.event_bus.status
        if status is None:
            return "state=idle"
        return (
            f"thread={status.thread_id} thread_state={status.thread_state.value} "
            f"state={status.turn_state.value} model={status.model}"
        )
