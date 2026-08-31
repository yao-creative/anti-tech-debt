from __future__ import annotations

from rich.console import Console

from contracts.events import Event, RuntimeState


class TuiFormatter:
    """Presentation adapter from runtime state into terminal output.

    Owns:
        Rendering policy for welcome, event, and status lines.

    Mutates:
        Console output only.

    Observes:
        Event and RuntimeState values.

    Functional framing:
        A renderer from domain objects to terminal-visible artifacts.

    Category-theoretic framing:
        A presentation functor that forgets internal structure while
        preserving the visible ordering of outputs.
    """

    def __init__(self, console: Console) -> None:
        self.console = console

    def render_welcome(self, thread_id: str) -> None:
        self.console.print(f"[bold]anti-tech-debt-app[/bold] thread={thread_id}")
        self.console.print("[dim]/help /new /resume /tools /quit[/dim]")

    def render_event(self, event: Event) -> None:
        self.console.print(f"[cyan]{event.type}[/cyan] {event.payload}")

    def render_status(self, status: RuntimeState | None) -> None:
        if status is None:
            return
        self.console.print(
            f"[dim]thread={status.thread_id} thread_state={status.thread_state.value} state={status.turn_state.value} "
            f"model={status.model} queues={status.queue_depths}[/dim]"
        )
