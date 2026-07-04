from __future__ import annotations

from rich.console import Console

from anti_tech_debt_app.contracts.events import Event, StatusSnapshot


class TuiFormatter:
    def __init__(self, console: Console) -> None:
        self.console = console

    def render_welcome(self, session_id: str) -> None:
        self.console.print(f"[bold]anti-tech-debt-app[/bold] session={session_id}")
        self.console.print("[dim]/help /new /resume /tools /quit[/dim]")

    def render_event(self, event: Event) -> None:
        self.console.print(f"[cyan]{event.type}[/cyan] {event.payload}")

    def render_status(self, status: StatusSnapshot | None) -> None:
        if status is None:
            return
        self.console.print(
            f"[dim]state={status.turn_state.value} model={status.model} queues={status.queue_depths}[/dim]"
        )
