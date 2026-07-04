from __future__ import annotations

from anti_tech_debt_app.runtime.session import SessionRuntime


class SlashCommands:
    """Interpreter for REPL-local slash commands.

    Owns:
        The mapping from slash command strings to session-management actions.

    Mutates:
        Session selection only indirectly through returned values; it does not
        mutate runtime state except by calling SessionManager to create a
        session.

    Observes:
        Command strings and available session ids.

    Functional framing:
        A partial function from command text to UI actions.

    Category-theoretic framing:
        A small command algebra interpreted into session-selection outcomes.
    """

    def __init__(self, manager: SessionRuntime) -> None:
        self.manager = manager

    def handle(self, command: str, current_session_id: str) -> tuple[str, str | None]:
        if command == "/help":
            return ("Commands: /help /new /resume /tools /quit", current_session_id)
        if command == "/new":
            return ("Created new session.", self.manager.create_session("Interactive Session"))
        if command == "/resume":
            sessions = self.manager.list_sessions()
            if sessions:
                return (f"Resumed {sessions[0]}", sessions[0])
            return ("No saved sessions.", current_session_id)
        if command == "/tools":
            return ("Tools: planner", current_session_id)
        if command == "/quit":
            return ("quit", None)
        return ("Unknown command.", current_session_id)
