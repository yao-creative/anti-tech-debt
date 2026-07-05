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
    runtime = container.thread_runtime
    commands = SlashCommands(runtime)
    first = runtime.new_thread("first")
    message = commands.handle("/new")
    assert message.startswith("Created new thread ")
    assert runtime.active_thread_id() != first
    message = commands.handle("/resume")
    assert message.startswith("Resumed ")
    assert runtime.active_thread_id() in message
    message = commands.handle("/tools")
    assert "planner" in message
