from __future__ import annotations

import asyncio
from contextlib import suppress

from rich.console import Console

from anti_tech_debt_app.bootstrap.container import Container
from anti_tech_debt_app.tui.composer import Composer
from anti_tech_debt_app.tui.formatter import TuiFormatter
from anti_tech_debt_app.tui.slash_commands import SlashCommands
from anti_tech_debt_app.tui.status_bar import StatusBar


class ReplApp:
    def __init__(self, container: Container, console: Console | None = None) -> None:
        self.container = container
        self.console = console or Console()
        self.formatter = TuiFormatter(self.console)
        self.composer = Composer()
        self.slash_commands = SlashCommands(self.container.session_manager)
        self.status_bar = StatusBar(self.container.event_bus)

    async def run(self) -> None:
        session_id = self.container.session_manager.create_session("Interactive Session")
        await self.container.session_manager.start()
        event_queue = self.container.event_bus.subscribe()
        printer = asyncio.create_task(self._print_events(event_queue))
        self.formatter.render_welcome(session_id)
        try:
            while True:
                self.formatter.render_status(self.container.event_bus.status)
                text = await self.composer.prompt_async()
                if not text.strip():
                    continue
                if text.startswith("/"):
                    message, next_session = self.slash_commands.handle(text.strip(), session_id)
                    if message == "quit":
                        break
                    self.console.print(message)
                    if next_session is not None:
                        session_id = next_session
                    continue
                await self.container.session_manager.submit_turn(session_id, text)
        finally:
            printer.cancel()
            with suppress(asyncio.CancelledError):
                await printer
            await self.container.session_manager.stop()

    async def _print_events(self, event_queue: asyncio.Queue) -> None:
        while True:
            event = await event_queue.get()
            self.formatter.render_event(event)
