from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

from anti_tech_debt_app.contracts.models import TurnContext


@dataclass(slots=True)
class ProviderEvent:
    type: str
    payload: dict[str, str]


class ProviderAdapter(Protocol):
    async def stream(self, turn_context: TurnContext) -> AsyncIterator[ProviderEvent]:
        ...
