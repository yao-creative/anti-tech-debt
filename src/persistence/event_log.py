from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from contracts.events import Event


class EventLog:
    """Append-only JSONL sink for replayable runtime events.

    Owns:
        The filesystem path for the event log.

    Mutates:
        The JSONL file contents by appending serialized events.

    Observes:
        Event values emitted by higher runtime layers.

    Functional framing:
        A writer sink for durable event history.

    Category-theoretic framing:
        A Writer-like accumulator externalized into the filesystem.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: Event) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event)) + "\n")

    def replay(self) -> list[dict[str, object]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line]
