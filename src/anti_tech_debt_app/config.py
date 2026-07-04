from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    app_name: str = "anti-tech-debt-app"
    default_model: str = "mock-stream"
    database_path: Path = Path(".anti-tech-debt-app/state.db")
    event_log_path: Path = Path(".anti-tech-debt-app/events.jsonl")
    workspace_path: Path = Path(".")
    queue_capacity: int = 32

    @property
    def data_dir(self) -> Path:
        return self.database_path.parent
