from __future__ import annotations

from anti_tech_debt_app.bootstrap.container import Container
from anti_tech_debt_app.config import AppConfig
from anti_tech_debt_app.tui.slash_commands import SlashCommands


def test_slash_commands_new_resume_tools(tmp_path) -> None:
    container = Container(
        AppConfig(
            database_path=tmp_path / "state.db",
            event_log_path=tmp_path / "events.jsonl",
        )
    )
    manager = container.session_runtime
    commands = SlashCommands(manager)
    current = manager.create_session("first")
    message, new_session = commands.handle("/new", current)
    assert message == "Created new session."
    assert new_session != current
    message, resumed = commands.handle("/resume", current)
    assert message.startswith("Resumed ")
    assert resumed is not None
    message, same = commands.handle("/tools", resumed)
    assert "planner" in message
    assert same == resumed
