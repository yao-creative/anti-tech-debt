from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from anti_tech_debt_app.contracts.models import TurnContext
from anti_tech_debt_app.providers.base import ProviderAdapter, ProviderEvent


class MockProvider(ProviderAdapter):
    async def stream(self, turn_context: TurnContext) -> AsyncIterator[ProviderEvent]:
        prompt = turn_context.user_input.strip()
        yield ProviderEvent("text_delta", {"text": "Analyzing tech debt scope...\n"})
        await asyncio.sleep(0)
        yield ProviderEvent("tool_call", {"tool": "planner", "input": prompt})
        await asyncio.sleep(0)
        if turn_context.allow_delegate:
            yield ProviderEvent("delegate", {"task": f"Audit one hotspot from: {prompt}"})
            await asyncio.sleep(0)
        yield ProviderEvent(
            "final",
            {"text": f"Happy path complete for request: {prompt}"},
        )
