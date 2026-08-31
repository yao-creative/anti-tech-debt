from __future__ import annotations

from runtime.thread import ThreadRuntime


class SlashCommands:
    """Interpreter for REPL-local slash commands.

    Owns:
        The mapping from slash command strings to thread-management actions.

    Mutates:
        Runtime-owned active thread only through ThreadRuntime operations.

    Observes:
        Command strings and available thread ids.

    Functional framing:
        A partial function from command text to UI actions.

    Category-theoretic framing:
        A small command algebra interpreted into runtime-owned thread changes.
    """

    def __init__(self, runtime: ThreadRuntime) -> None:
        self.runtime = runtime

    def handle(self, command: str) -> str:
        if command == "/help":
            return "Commands: /help /new /resume /tools /quit"
        if command == "/new":
            thread_id = self.runtime.new_thread("Interactive Thread")
            return f"Created new thread {thread_id}."
        if command == "/resume":
            thread_id = self.runtime.resume_latest_thread()
            return f"Resumed {thread_id}"
        if command == "/tools":
            return "Tools: planner"
        if command == "/quit":
            return "quit"
        return "Unknown command."
