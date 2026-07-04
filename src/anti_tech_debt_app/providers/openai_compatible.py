from __future__ import annotations

from collections.abc import AsyncIterator

from anti_tech_debt_app.contracts.models import TurnContext
from anti_tech_debt_app.providers.base import ProviderAdapter, ProviderEvent


class OpenAICompatibleProvider(ProviderAdapter):
    async def stream(self, turn_context: TurnContext) -> AsyncIterator[ProviderEvent]:
        raise NotImplementedError("Real provider integration is not implemented in this scaffold.")
