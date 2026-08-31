from __future__ import annotations

import asyncio
from contextlib import suppress

from rich.console import Console

from bootstrap.container import Container
from tui.composer import Composer
from tui.formatter import TuiFormatter
from tui.slash_commands import SlashCommands
from tui.status_bar import StatusBar


class ReplApp:
    """Interactive shell over the local runtime.

    Owns:
        The terminal control loop and the composition of composer, formatter,
        slash commands, and status bar.

    Mutates:
        ThreadRuntime task lifecycle.

    Observes:
        Prompt input, slash commands, EventBus runtime state, and subscribed event
        stream values.

    Functional framing:
        An interpreter from terminal interactions into runtime commands and
        rendered outputs.

    Category-theoretic framing:
        A boundary morphism from user interaction space into the internal
        effectful runtime category.
    """

    def __init__(self, container: Container, console: Console | None = None) -> None:
        # poset 
        self.container = container
        self.console = console or Console()
        self.formatter = TuiFormatter(self.console)
        self.composer = Composer()
        self.slash_commands = SlashCommands(self.container.thread_runtime)
        self.status_bar = StatusBar(self.container.event_bus)

    async def run(self) -> None:
        await self.container.thread_runtime.start()
        event_queue = self.container.thread_runtime.subscribe()
        printer = asyncio.create_task(self._print_events(event_queue))
        self.formatter.render_welcome(self.container.thread_runtime.active_thread_id())
        try:
            while True:
                self.formatter.render_status(self.container.event_bus.status)
                text = await self.composer.prompt_async()
                if not text.strip():
                    continue
                if text.startswith("/"):
                    message = self.slash_commands.handle(text.strip())
                    if message == "quit":
                        break
                    self.console.print(message)
                    continue
                await self.container.thread_runtime.submit_turn(text)
        finally:
            printer.cancel()
            with suppress(asyncio.CancelledError):
                await printer
            await self.container.thread_runtime.stop()

    async def _print_events(self, event_queue: asyncio.Queue) -> None:
        while True:
            event = await event_queue.get()
            self.formatter.render_event(event)
