from __future__ import annotations

from anti_tech_debt_app.bootstrap.container import Container
from anti_tech_debt_app.config import AppConfig
from anti_tech_debt_app.contracts.models import MessageRecord


def test_session_persistence_and_event_replay(tmp_path) -> None:
    config = AppConfig(
        database_path=tmp_path / "state.db",
        event_log_path=tmp_path / "events.jsonl",
    )
    container = Container(config)
    session_id = container.session_manager.create_session("persistent")
    container.store.append_message(MessageRecord(session_id=session_id, role="user", content="hello"))
    assert container.store.get_session(session_id) is not None
    assert container.store.list_messages(session_id)[0].content == "hello"
    assert container.event_log.replay() == []
