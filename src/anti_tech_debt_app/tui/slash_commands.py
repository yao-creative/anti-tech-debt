from __future__ import annotations

from anti_tech_debt_app.runtime.session_manager import SessionManager


class SlashCommands:
    def __init__(self, manager: SessionManager) -> None:
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
